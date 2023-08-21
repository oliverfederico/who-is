# *Who is using this library?*

This tool is designed to study third-party library usage in the C/C++ GitHub ecosystem.

The tool consists of three main components each with a python script: \
[*dependency_discovery*](#fetcher): Use to discovery the third-party library dependencies of C/C++ repositories on GitHub.\
[*library_usage*](#builder): Use to collect client usage data for a given library, uses **find_call.cpp** \
[*analyse_usage*](#builder): Use to process usage data for library usage and API analysis

## Requirements

* Python (3.6+) with virtual environments and pip.
  - See "requirements.txt" for python dependencies

To build **find_call.cpp** 
* [Nholmann Json](https://github.com/nlohmann/json)
* [LLVM](https://github.com/llvm/llvm-project)
  - Instructions on installing LLVM and setting up build infrastructure can be found [here](https://clang.llvm.org/docs/LibASTMatchersTutorial.html): 
  - Place "find_call/" inside the 'clang-tools-extra' directory inside LLVM project, build and provide path to binary when running **analyse_usage.py** 

## Usage

Example usage using CCScanner Dataset:
```
python find_usage.py repo2deps.json xxhash xxhash\.h

python analyse_usage.py ../example_results
```

### Dependency Discovery
This can be skipped if using the CCScanner Dataset

run commands:
```
python dependency_discovery.py
```
This takes ~12 hours to run and outputs the dependencies of each scanned library as a json file.

#### GitHub

This module scans GH repositories tagged as C and C++ software and sorts
them according to the number of stars.

To avoid running into [rate limit issues](https://developer.github.com/v3/search/), please provide your [personal access token](https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/) as an enviroment variable.

```
export GITHUB_TOKEN=<your_github_token>
```

### Library Usage Discovery

```
python find_usage.py <path-to-dependencies> <library-name> <header-regex>
```
This will download and scan each potential client repository for usage and output the usage data for each client repository.

NB: if using the CCScanner dataset then pass **repo2dep.json** as path to dependencies. \
NB: library name should match name used in dependency dataset.

### Usage Analysis and Visualisation

```
python analyse_usage.py <path-to-usage-data> 
```
This will analyse the usage data and provide tables and plots of a libraries usage.

## Datasets

This project uses the dependency dataset provided by [CCScanner](https://github.com/lkpsg/ccscanner) which can be used in replacement of the dependency discovery module.
CCScanner Dataset is available [here](https://figshare.com/s/9e2fd7a1389af8266bfe?file=36678075), simply put **repos2deps.json** in the **find_usage/** directory 

June 2023 run of dependency discovery module can be found in **dependency_discovery/results**/
Example Usage data for several libraries can be found in **example_results/**
