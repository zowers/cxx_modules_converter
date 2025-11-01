# cxx_modules_converter

`cxx_modules_converter.py` is a Python script to convert C++ sources and headers to C++20 modules.

## License

cxx_modules_converter is licensed under the [MIT](LICENSE) license.

## Requirements
Python 3.10 or later is required.

## Usage
Script can be used as following:
> cxx_modules_converter.py [-h] [-s DIRECTORY] [-i] [-d DESTINATION] [-a {modules,headers}] [-r ROOT] [-p] [-I INCLUDE] [-n NAME] [-k SKIP] [-c COMPAT] [-m COMPAT_MACRO] [-e HEADER] [--export EXPORT] [--exportsuffix EXPORTSUFFIX] [--inextheader INEXTHEADER] [--inextcxx INEXTCXX] [--outextmod OUTEXTMOD] [--outextmodimpl OUTEXTMODIMPL] [--modules MODULES] [--modulestd] [--modulestdcompat] [--join JOIN] [-v]

### Options:
* -h, --help            show this help message and exit
* -s DIRECTORY, --directory DIRECTORY
                        the directory with files
* -i, --inplace         convert files in the same directory or put conversion result to destination (unsupported)
* -d DESTINATION, --destination DESTINATION
                        destination directory where to put conversion result, ignored when --inplace is provided
* -a {modules,headers}, --action {modules,headers}
                        action to perform - convert to modules or headers
* -r ROOT, --root ROOT  resolve module names starting from this root directory, ignored when --parent
* -p, --parent          resolve module names starting from parent of source directory
* -I INCLUDE, --include INCLUDE
                        include search path, starting from root or parent directory
* -n NAME, --name NAME  module name for modules in [root] directory which prefixes all modules
* -k SKIP, --skip SKIP  skip patterns - files and directories matching any pattern will not be converted or copied (fmatch is used)
* -c COMPAT, --compat COMPAT
                        compat patterns - files and directories matching any pattern will be converted in compatibility mode allowing to use as either module or header  (fmatch is used)
* -m COMPAT_MACRO, --compat-macro COMPAT_MACRO
                        compatibility macro name used in compat modules and headers
* -e HEADER, --header HEADER
                        always include headers with matching names and copy them as is (fmatch is used)
* --export EXPORT       A=B means module A exports module B, i.e. `--export A=B` means module A will have `export import B;`. use `--export "A=*"` to export all imports. use `--export "*=B"` to export B from all modules. use `--export "*=*"` to
                        export all from all modules.
* --exportsuffix EXPORTSUFFIX
                        export module suffix for which `export import` is used instead of simple `import`
* --inextheader INEXTHEADER input header file extensions, .h by default. first use replaces the default, subsequent uses append.
* --inextcxx INEXTCXX   input C++ source file extensions, .cpp by default. first use replaces the default, subsequent uses append.
* --outextmod OUTEXTMOD output module interface unit file extensions. default: .cppm
  *  e.g. `--outextmod=.ixx` to skip the need to change `/interface /TP` options in msvc (https://learn.microsoft.com/en-us/cpp/build/reference/interface?view=msvc-170)
* --outextmodimpl OUTEXTMODIMPL  output module implementation unit file extensions. default: .cpp
* --modules MODULES     `M=P`: start modules tree `M` at path `P`, directory separator is converted to `.` (dot). Default: use directory name and file name as module name.
* --modulestd MODULESTD
                        Enable `std` module, i.e. define `--modules vector=std` to replace `vector` and other standard headers to `import std;`.
* --modulestdcompat MODULESTDCOMPAT
                        Enable `std.compat` module, i.e. define `--modules vector=std.compat` to replace `vector` and other standard headers to `import std.compat;`.
* --join JOIN          A=B means create module A with partition modules for files matching pattern B. Example: --join A=A/* creates module A with partitions for all files in A/ directory.
* -v, --version         show version

## Assumptions
The converter has several configurable assumptions:
* following source files extensions are used by default but can be changed:
  * `.h` - header file (input), configurable with `--inextheader`
  * `.cpp` - c++ source file (input), configurable with `--inextcxx`
  * `.cpp` - module implementation unit (output), configurable with `--outextmodimpl`
  * `.cppm` - module interface unit (output), configurable with `--outextmod`
* header file path is used to determine module name by joining path parts with dots (`.`); same for c++ source files, but can be customized using `--join` option to combine multiple files into module partitions
* system header includes using `#include <>` are moved to global module fragment, but standard library headers can be replaced with `import std;` using `--modulestd` or `import std.compat;` using `--modulestdcompat`

## Tests
[`pytest`](https://pytest.org/) is used to run tests.
The `venv` can be used to create python3 virtual environment, assuming Linux and bash is used:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
Install pytest requirements using
```bash
pip install -r requirements-test.txt
```

## Development

For development, you need to install Poetry:

```bash
pip install poetry
```

To bump the version, use:

```bash
poetry version patch  # for patch version
poetry version minor  # for minor version
poetry version major  # for major version
```
