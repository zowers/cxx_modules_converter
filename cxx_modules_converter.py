#!/usr/bin/env python3
#
# Convert C++20 modules to headers and headers to modules
#

import argparse
from pathlib import Path
import sys

from cxx_modules_converter_lib import Converter, ConvertAction

def parse_args(argv: list[str] = None):
    parser = argparse.ArgumentParser(
                    prog='cxx_modules_converter',
                    description='Convert C++20 modules to headers and headers to modules',
                    epilog='')
    directory = '.'
    parser.add_argument('-s','--directory', default=directory, required=True, help='the directory with files')
    parser.add_argument('-i', '--inplace', default=False, action='store_true', help='convert files in the same directory or put conversion result to destination')
    parser.add_argument('-d', '--destination', default=directory, help='destination directory where to put conversion result, ignored when --inplace is provided')
    parser.add_argument('-a', '--action', default=ConvertAction.MODULES, 
                        choices=[ConvertAction.MODULES, ConvertAction.HEADERS],
                        help='action to perform - convert to modules or headers')
    parser.add_argument('-r', '--root', default=directory, help='resolve module names starting from this root directory, ignored when --parent')
    parser.add_argument('-p', '--parent', action='store_true', default=False, help='resolve module names starting from parent of source directory')
    parser.add_argument('-I', '--include', action='append', default=[], help='include search path, starting from root or parent directory')
    parser.add_argument('-n', '--name', default='', help='module name for modules in [root] directory which prefixes all modules')
    parser.add_argument('-k', '--skip', action='append', default=[], help='skip patterns - files and directories matching any pattern will not be converted or copied')
    parsed_args = parser.parse_args(argv)
    return parsed_args

def log(message):
    print('cxx_modules_converter:', message)

def main(parsed_args):
    log(f'converting files of directory "{parsed_args.directory}" to {parsed_args.action} {'inplace' if parsed_args.inplace else ' into ' + parsed_args.destination}')
    if parsed_args.inplace:
        destination = parsed_args.directory
    else:
        destination = parsed_args.destination
        assert(destination != parsed_args.directory)
    directory = Path(parsed_args.directory)
    converter = Converter(parsed_args.action)
    if parsed_args.parent:
        parsed_args.root = directory.parent
    if parsed_args.root:
        root_dir = Path(parsed_args.root)
        converter.options.root_dir = root_dir
    else:
        converter.options.root_dir = directory
    converter.options.root_dir_module_name = parsed_args.name
    for include in parsed_args.include:
        log(f'include search path: "{include}"')
        converter.options.search_path.append(include)
    for skip_pattern in parsed_args.skip:
        log(f'skip pattern: "{skip_pattern}"')
        converter.options.skip_patterns.append(skip_pattern)
    converter.convert_directory(directory, Path(destination))
    log('done')

if __name__ == '__main__':
    parsed_args = parse_args()
    sys.exit(main(parsed_args))
