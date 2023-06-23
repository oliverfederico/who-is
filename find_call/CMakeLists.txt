set(LLVM_LINK_COMPONENTS support)

# CMakeLists.txt
find_package(nlohmann_json 3.2.0 REQUIRED)

add_clang_executable(find-call
  find_call.cpp
  )
target_link_libraries(find-call
  PRIVATE
  clangAST
  clangASTMatchers
  clangBasic
  clangFrontend
  clangSerialization
  clangTooling
  nlohmann_json::nlohmann_json
  )
