# cxx_modules_converter

`cxx_modules_converter.py` is a Python script to convert C++ sources and headers to C++20 modules.

## License

cxx_modules_converter is licensed under the [MIT](LICENSE) license.

## Usage
Script can be used as following:
> cxx_modules_converter.py [-h] [-s DIRECTORY] [-d DESTINATION] [-a {modules,headers}] [-r ROOT] [-p] [-I INCLUDE] [-n NAME] [-k SKIP] [-c COMPAT] [-m COMPAT_MACRO] [-e HEADER] [--export EXPORT] [--exportsuffix EXPORTSUFFIX] [-v]

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
* -k SKIP, --skip SKIP  skip patterns - files and directories matching any pattern will not be converted or copied
* -c COMPAT, --compat COMPAT
                        compat patterns - files and directories matching any pattern will be converted in compatibility mode allowing to use as either module or header
* -m COMPAT_MACRO, --compat-macro COMPAT_MACRO
                        compatibility macro name used in compat modules and headers
* -e HEADER, --header HEADER
                        always include headers with matching names and copy them as is
* --export EXPORT       A=B means module A exports module B, i.e. `--export A=B` means module A will have `export import B;`. use `--export "A=*"` to export all imports. use `--export "*=B"` to export B from all modules. use `--export "*=*"` to
                        export all from all modules.
* --exportsuffix EXPORTSUFFIX
                        export module suffix for which `export import` is used instead of simple `import`
* -v, --version         show version

## Assumptions
The converter has several assumptions which are not configurable (at the moment):
* following source files extensions are used:
  * `.h` - header file
  * `.cpp` - c++ source file
  * `.cpp` - module implementation unit
  * `.cppm` - module interface unit
* header file path is used to determine module name by joining path parts with dots (`.`); same for c++ source files
* system header includes using `#include <>` are moved to global module fragment

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
