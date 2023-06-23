#include "clang/Tooling/CommonOptionsParser.h"
#include "clang/Tooling/Tooling.h"
#include "llvm/Support/CommandLine.h"
#include "clang/ASTMatchers/ASTMatchers.h"
#include "clang/ASTMatchers/ASTMatchFinder.h"
#include "clang/AST/AST.h"
#include "clang/AST/Expr.h"
#include "clang/Basic/SourceManager.h"
#include <string>
#include <fstream>
#include <iostream>
#include <nlohmann/json.hpp>

using namespace clang;
using namespace clang::ast_matchers;
using json = nlohmann::json;

class FunctionCallPrinter : public MatchFinder::MatchCallback {

  int count = 0;
  json j;

  void handleCallExpr(const CallExpr *CE, const FunctionDecl *FD,
                                           const MatchFinder::MatchResult &Result) {
    SourceManager &SM = Result.Context->getSourceManager();
    SourceLocation Loc = FD->getLocation();
    SourceLocation Cloc = CE->getBeginLoc();
    if (Loc.isValid() and Cloc.isValid()) {
      PresumedLoc PL = SM.getPresumedLoc(Loc);
      PresumedLoc CPL = SM.getPresumedLoc(Cloc);
      if (PL.isValid() and CPL.isValid() and PL.getFilename() != CPL.getFilename()) {
        json f;

        f["function"]["location"]["file"] = CPL.getFilename();
        f["function"]["location"]["line"] = CPL.getLine();
        f["function"]["location"]["offset"] = CPL.getColumn();
        f["function"]["definition"]["file"] = PL.getFilename();
        f["function"]["definition"]["line"] = PL.getLine();
        f["function"]["definition"]["offset"] = PL.getColumn();

        handleFunctionProperties(FD, f);

        if (const clang::CXXMethodDecl *MD = llvm::dyn_cast<clang::CXXMethodDecl>(FD)) {
          f["function"]["isCXXMethodDecl"] = true;
          f["function"]["isVirtualCXXMethodDecl"] = MD->isVirtual();
        } else {
          f["function"]["isCXXMethodDecl"] = false;
        }

        f["function"]["args"] = {};

        for (uint i = 0; i < CE->getNumArgs(); i++) {
          auto arg = CE->getArg(i);
          handleArg(i, arg, f);
        }

        j.emplace_back(f);
        count++;
      }
    }
  }

  void handleArg(uint i, const Expr *arg, json &f) {
    f["function"]["args"][std::to_string(i)]["type"] = arg->getType().getAsString();
    if (const clang::IntegerLiteral *IL = llvm::dyn_cast<clang::IntegerLiteral>(arg)) {
      llvm::SmallString<64> StrVal;
      IL->getValue().toString(StrVal, 10, true);
      f["function"]["args"][std::to_string(i)]["value"] = StrVal.str().str();
    } else if (const clang::FloatingLiteral *FL = llvm::dyn_cast<clang::FloatingLiteral>(arg)) {
      f["function"]["args"][std::to_string(i)]["value"] = FL->getValue().convertToDouble();
    } else if (const clang::CharacterLiteral *CL = llvm::dyn_cast<clang::CharacterLiteral>(
                   arg)) {
      f["function"]["args"][std::to_string(i)]["value"] = static_cast<char>(CL->getValue());
    } else if (const clang::StringLiteral *SL = llvm::dyn_cast<clang::StringLiteral>(arg)) {
      std::string strValue = SL->getString().str();
      f["function"]["args"][std::to_string(i)]["value"] = strValue;
    } else if (const clang::CXXBoolLiteralExpr *BLE = llvm::dyn_cast<clang::CXXBoolLiteralExpr>(
                   arg)) {
      f["function"]["args"][std::to_string(i)]["value"] = (BLE->getValue() ? "true"
                                                                           : "false");
    } else if (const clang::CXXNullPtrLiteralExpr *NullPtr = llvm::dyn_cast<clang::CXXNullPtrLiteralExpr>(
                   arg)) {
      f["function"]["args"][std::to_string(i)]["value"] = "nullptr";
    } else if (const clang::FixedPointLiteral *FPL = llvm::dyn_cast<clang::FixedPointLiteral>(
                   arg)) {
      f["function"]["args"][std::to_string(i)]["value"] = FPL->getValueAsString(10);
    }
  }

  void handleFunctionProperties(const FunctionDecl *FD, json &f) {
    f["function"]["name"] = FD->getNameAsString();
    f["function"]["functionDeclReturn"] = FD->getReturnType().getAsString();
    f["function"]["isVariadic"] = FD->isVariadic();
    f["function"]["isVirtualAsWritten"] = FD->isVirtualAsWritten();
    f["function"]["isPure"] = FD->isPure();
    f["function"]["hasBody"] = FD->hasBody();
    f["function"]["isDefaulted"] = FD->isDefaulted();
    f["function"]["isUserProvided"] = FD->isUserProvided();
    f["function"]["isStatic"] = FD->isStatic();
    f["function"]["isInlineSpecified"] = FD->isInlineSpecified();
    f["function"]["isInlined"] = FD->isInlined();
    f["function"]["isFunctionTemplateSpecialization"] = FD->isFunctionTemplateSpecialization();
    f["function"]["isImplicitlyInstantiable "] = FD->isImplicitlyInstantiable();
    f["function"]["isTemplateInstantiation"] = FD->isTemplateInstantiation();
    f["function"]["isOverloaded"] = FD->isOverloadedOperator();
  }

public:
  // Matcher callback handler
  void run(const MatchFinder::MatchResult &Result) override {
    if (const CallExpr *CE = Result.Nodes.getNodeAs<CallExpr>("callExpr")) {
      const FunctionDecl *FD = CE->getDirectCallee();
      if (FD) {
        handleCallExpr(CE, FD, Result);
      }
    } else {
      llvm::outs() << "Call Expr without FD found!" << "\n";
    }
  }

  json getJson() {
    return j;
  }
};

static llvm::cl::OptionCategory FindCallCategory("find-call options");
static llvm::cl::opt <std::string> Header("header-regex",
                                         llvm::cl::desc("library header files/paths - 'json/json.h|etc'"),
                                         llvm::cl::cat(FindCallCategory));

void writeJsonToFile(json j, std::string path) {
  std::string json_str = j.dump(4);

  // check if JSON string is "null" or "{}"
  if (json_str != "null") {
    // open a file stream
    std::string delimiter = "/";
    std::string target = "@@";
    std::stringstream ss(path);
    std::string token;
    while (std::getline(ss, token, delimiter[0])) {
      if (token.find(target) != std::string::npos) {
        std::ofstream file("results/" + token + ".json");
        // check if the file stream has been successfully opened
        if (!file) {
          std::cerr << "Failed to open the file." << std::endl;
        }

        // write JSON string to the file
        file << json_str;

        // check if there were any problems writing to the file
        if (!file) {
          std::cerr << "Failed to write to the file." << std::endl;
        }

        // close the file stream
        file.close();
        break;
      }
    }
  } else {
    std::cout << "No calls found. \n";
  }
}

int main(int argc, const char **argv) {
  // Check if the desired argument is provided
  if (argc < 3) {
    llvm::errs() << "Missing required arguments: filenames or library header file/path\n";
    return 1;
  }

  auto ExpectedParser = clang::tooling::CommonOptionsParser::create(argc, argv, FindCallCategory);
  if (!ExpectedParser) {
    // Fail gracefully for unsupported options.
    llvm::errs() << ExpectedParser.takeError();
    return 1;
  }

  clang::tooling::CommonOptionsParser &OptionsParser = ExpectedParser.get();
  auto paths = OptionsParser.getSourcePathList();
  clang::tooling::ClangTool Tool(OptionsParser.getCompilations(), paths);

  FunctionCallPrinter Printer;

  MatchFinder Finder;
  Finder.addMatcher(traverse(TK_IgnoreUnlessSpelledInSource, callExpr(
                                                                 allOf(isExpansionInMainFile(), callee(functionDecl(isExpansionInFileMatching(Header))))).bind("callExpr")),
                    &Printer);

  auto tool = Tool.run(clang::tooling::newFrontendActionFactory(&Finder).get());

  // dump JSON object to string
  writeJsonToFile(Printer.getJson(), paths[0]);

  return tool;
}