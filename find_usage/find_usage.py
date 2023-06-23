import json
import sys
import os
from git import Repo
import subprocess
import logging
from pathlib import Path

# Create a custom logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create handlers
f_handler = logging.FileHandler('file.log', mode='w')
f_handler.setLevel(logging.INFO)

# Create formatters and add it to handlers
f_format = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s')
f_handler.setFormatter(f_format)

# Add handlers to the logger
logger.addHandler(f_handler)


class Config:
    EXCLUDE_PATHS = []
    LIBRARY_NAME = ''
    IGNORE_LIST = []
    HEADER_PATTERN = ''
    TOOL_PATH = ''
    WORKING_DIR = Path(os.getcwd())


def run_command(command, directory=Config.WORKING_DIR):
    try:
        result = subprocess.run(command, capture_output=True, text=True, shell=True, cwd=directory)
        logger.info(result.stdout)

        if result.returncode != 0:
            logger.error(f'Error: {result.stderr}')
            return False

        return True
    except Exception as e:
        logger.error(f"Error: {e}")
        return False


def is_not_excluded_path(file_path):
    file_path = file_path.lower()
    return not any(path in file_path for path in Config.EXCLUDE_PATHS)


def parse_compile_commands(repo_path):
    # Locate compile_commands
    commands_path = repo_path / 'compile_commands.json'
    if not commands_path.exists():
        commands_path = repo_path / 'build' / 'compile_commands.json'
    if not commands_path.exists():
        commands_path = repo_path / 'src' / 'compile_commands.json'
    if not commands_path.exists():
        commands_path = repo_path / 'src' / 'build' / 'compile_commands.json'

    if commands_path.exists():
        with commands_path.open() as f:
            data = json.load(f)

        file_list = [
            item["file"]
            for item in data
            if os.path.exists(item["file"]) and (
                    item["file"].endswith('.c') or item["file"].endswith('.cc') or item["file"].endswith('.cpp'))
               and len(item["file"].rsplit('.', 2)) < 3 and is_not_excluded_path(
                item["file"]) and Config.LIBRARY_NAME in item["command"].lower()
        ]
        return file_list

    return []


def generate_compile_commands(repo_path):
    ccjson_path = repo_path / 'compile_commands.json'
    if ccjson_path.exists():
        logger.info(f"found compile_commands.json for: {repo_path}")
        return repo_path
    else:
        build_ccjson_path = repo_path / 'build' / 'compile_commands.json'
        if build_ccjson_path.exists():
            logger.info(f"moving compile_commands.json from /build to source for: {repo_path}")
            run_command("ln build/compile_commands.json", repo_path)
            return build_ccjson_path
        else:
            cmake_lists_path = repo_path / 'CMakeLists.txt'
            if cmake_lists_path.exists():
                if not (repo_path / "build").exists():
                    (repo_path / "build").mkdir(parents=True, exist_ok=True)
                    run_command(
                        "cmake -B build -Wno-dev -DCMAKE_EXPORT_COMPILE_COMMANDS=1 -DCMAKE_BUILD_TYPE=Release .",
                        repo_path)
                    run_command("ln build/compile_commands.json", repo_path)
                else:
                    run_command("cmake -Wno-dev -DCMAKE_EXPORT_COMPILE_COMMANDS=1 -DCMAKE_BUILD_TYPE=Release .",
                                repo_path)
                return cmake_lists_path
            else:
                src_path = repo_path / "src"
                if src_path.exists():
                    logger.info(f"checking for commands file in src for: {repo_path}")
                    return generate_compile_commands(src_path)

    return None


def run_clang_tool(repo_path, cmake_failed, ran_on_tool):
    files = parse_compile_commands(repo_path)
    if not files:
        logger.error("Failed to locate compile_commands.json")
        cmake_failed.append(repo_path)
        return False, cmake_failed, ran_on_tool
    ran_on_tool.append(repo_path)
    logger.info("\nrunning tool on repo!\n")
    if not run_command("find-call " + " ".join(
            files) + " " + "--extra-arg=-Wno-everything" + " " + f'--header-regex="{Config.HEADER_PATTERN}"',
                       Config.TOOL_PATH):
        return False, cmake_failed, ran_on_tool
    return True, cmake_failed, ran_on_tool


def process_repositories(repos):
    failed = []
    non_cmake = []
    cmake_failed = []
    ran_on_tool = []

    dir_path = Config.WORKING_DIR

    logger.info(f"Scanning Repositories in: {dir_path}")
    for repo in repos:
        repo_path = dir_path / repo
        if repo in Config.IGNORE_LIST:
            continue

        logger.info(f"Downloading repository: {repo}")

        try:
            download_repo(repo)
        except Exception as e:
            logger.error(f"Error downloading repository: {e}")
            failed.append(repo)
            continue
        logger.info(f"Processing repository: {repo}")
        comp_path = generate_compile_commands(repo_path)
        if not comp_path:
            non_cmake.append(repo)
            continue
        try:
            success, cmake_failed, ran_on_tool = run_clang_tool(repo_path, cmake_failed, ran_on_tool)
            if not success:
                logger.error(f"Failed to run Clang tool on repository: {repo}")
            else:
                logger.error(f"Ran Clang tool on repository: {repo}")
        except Exception as e:
            logger.error(f"Failed to generate compile commands for repository: {repo}")
            logger.error(f"Error: {e}")
        if not run_command(f"rm -fr {repo}"):
            logger.error(f"failed to remove repo:{repo}")
    return failed, non_cmake, cmake_failed, ran_on_tool


def download_repo(repo):
    owner, name = repo.split("@@")
    r_url = f"https://github.com/{owner}/{name}.git"
    logger.info(f"Cloning {repo} from {r_url}")
    r = None
    if not os.path.isdir(repo):
        try:
            r = Repo.clone_from(r_url, repo,
                                multi_options=["--recurse-submodules", "-j6", " --depth 1", "--shallow-submodules"])
        except Exception as e:
            logger.error(f"Failed to clone repo: {e}")
    return r


def find_client_repos(json_obj):
    result = []
    for key, value in json_obj.items():
        if isinstance(value, dict) and value:
            if Config.LIBRARY_NAME in value:
                result.append(key)
    return result

# Find potential client repos that use cmake or submodule to manage dependency
def find_client_repos_opt(json_obj):
    result = []
    for key, value in json_obj.items():
        if isinstance(value, dict) and value:
            if Config.LIBRARY_NAME in value:
                for evi in value[Config.LIBRARY_NAME]:
                    if evi["extractor_type"] == "cmake" or evi["extractor_type"] == "submod":
                        result.append(key)
                        break
    return result


def find_all_libs(json_obj):
    result = set()
    for key, value in json_obj.items():
        if isinstance(value, dict):
            result.update(value.keys())
    return result


def find_popular_libs(json_obj):
    result = {}
    for key, value in json_obj.items():
        if value and isinstance(value, dict):
            for lib in value.keys():
                if lib not in result:
                    result[lib] = 1
                else:
                    result[lib] = result[lib] + 1
    result = dict(sorted(result.items(), key=lambda item: item[1]))
    return result


def find_popular_libs_cmake_submod(data):
    library_counts = {}
    for project, dependencies in data.items():
        for dependency, occurrences in dependencies.items():
            for occurrence in occurrences:
                if occurrence['extractor_type'] in ['cmake', 'submod']:
                    library_counts[dependency] = library_counts.get(dependency, 0) + 1
                    break

    library_counts = dict(sorted(library_counts.items(), key=lambda item: item[1]))
    return library_counts


def main():
    # Check if file path was passed as command-line argument
    if len(sys.argv) < 3:
        print("Usage: python script.py <file_path> <library_name> <header_regex> <exclude_path>")
        return

    # Setup
    Config.EXCLUDE_PATHS = ["/libs/", "/common/", "/third-party/", "/thirdparty/", "/third_party/", "/external/"]
    Config.EXCLUDE_PATHS.extend(sys.argv[3:])
    Config.LIBRARY_NAME = sys.argv[2]
    Config.TOOL_PATH = sys.argv[1]
    Config.HEADER_PATTERN = sys.argv[3]

    working_path = Config.WORKING_DIR / "repo2dep.json"

    # Try to open the dependencies file
    try:
        with open(working_path, 'r') as file:
            # Find potential client repositories
            json_str = file.read()
            json_obj = json.loads(json_str)
            repos = find_client_repos_opt(json_obj)

            # Process client repositories for dependencies
            download_failed, non_cmake, cmake_failed, ran_on_tool = process_repositories(repos=["Vita3K@@Vita3K"])

            # Log run summary
            logger.info(f"all repos ({len(repos)}): {repos}")
            logger.info(f"failed to download ({len(download_failed)}): {download_failed}")
            logger.info(f"non cmake repos ({len(non_cmake)}): {non_cmake}")
            logger.info(f"cmake failed repos ({len(cmake_failed)}): {cmake_failed}")
            logger.info(f"ran on tool repos ({len(ran_on_tool)}):{ran_on_tool}")
    except FileNotFoundError:
        logger.error(f"No such file or directory: '{working_path}'")
    except IOError as e:
        logger.error(f"Error occurred while trying to read file: '{working_path}: {e}'")


if __name__ == "__main__":
    main()
