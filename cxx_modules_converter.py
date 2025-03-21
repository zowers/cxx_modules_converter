#!/usr/bin/env python3
#
# Convert C++20 modules to headers and headers to modules
#
from __future__ import annotations

import argparse
import importlib.metadata
from pathlib import Path
import sys

from cxx_modules_converter_lib import (
    Converter, 
    ConvertAction,
    COMPAT_MACRO_DEFAULT,
    always_include_names,
    ContentType,
    Options,
)

def get_version() -> str | None:
    try:
        metadata_version = importlib.metadata.version('cxx_modules_converter')
        if metadata_version:
            return metadata_version
    except importlib.metadata.PackageNotFoundError:
        return 'not-installed'

def parse_args(argv: list[str] | None = None):
    version = get_version()
    parser = argparse.ArgumentParser(
                    prog='cxx_modules_converter',
                    description=f'Convert C++20 modules to headers and headers to modules, version: {version}',
                    epilog='')
    directory = '.'
    options = Options()
    parser.add_argument('-s','--directory', default=directory, help='the directory with files')
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
    parser.add_argument('-c', '--compat', action='append', default=[],
                        help='compat patterns - files and directories matching any pattern'
                        + ' will be converted in compatibility mode allowing to use as either module or header')
    parser.add_argument('-m', '--compat-macro', default=COMPAT_MACRO_DEFAULT, help='compatibility macro name used in compat modules and headers')
    parser.add_argument('-e', '--header', action='append', default=always_include_names, help='always include headers with matching names and copy them as is')
    parser.add_argument('--export', action='append', default=[], 
                        help='A=B means module A exports module B, i.e. `--export A=B` means module A will have `export import B;`.'
                        + ' use `--export "A=*"` to export all imports.'
                        + ' use `--export "*=B"` to export B from all modules.'
                        + ' use `--export "*=*"` to export all from all modules.'
                        )
    parser.add_argument('--exportsuffix', action='append', default=[], help='export module suffix for which `export import` is used instead of simple `import`')
    parser.add_argument('--inextheader', action='append', default=[], help='input header file extensions, .h by default. first use replaces the default, subsequent uses append.')
    parser.add_argument('--inextcxx', action='append', default=[], help='input C++ source file extensions, .cpp by default. first use replaces the default, subsequent uses append.')
    parser.add_argument('--outextmod', help=f'output module interface unit file extensions. default: {options.content_type_to_ext[ContentType.MODULE_INTERFACE]}')
    parser.add_argument('--outextmodimpl', help=f'output module implementation unit file extensions. default: {options.content_type_to_ext[ContentType.MODULE_IMPL]}')
    parser.add_argument('-v', '--version', default=False, action='store_true', help='show version')
    parsed_args = parser.parse_args(argv)
    return parsed_args

def log(message: str):
    print('cxx_modules_converter:', message)

def main():
    parsed_args = parse_args()
    if parsed_args.version:
        version = get_version()
        log(f'{version}')
        return
    if not parsed_args.directory:
        log('--directory argument is required')
        return 1
    log_messages: list[str] = []
    log_messages.append(f'converting files of directory "{parsed_args.directory}" to {parsed_args.action} {"inplace" if parsed_args.inplace else " into " + parsed_args.destination}')
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
        log_messages.append(f'include search path: "{include}"')
        converter.options.search_path.append(include)
    for skip_pattern in parsed_args.skip:
        log_messages.append(f'skip pattern: "{skip_pattern}"')
        converter.options.skip_patterns.append(skip_pattern)
    for compat_pattern in parsed_args.compat:
        log_messages.append(f'compat pattern: "{compat_pattern}"')
        converter.options.compat_patterns.append(compat_pattern)
    if parsed_args.compat_macro:
        converter.options.compat_macro = parsed_args.compat_macro
    for header in parsed_args.header:
        log_messages.append(f'header: "{header}"')
        converter.options.always_include_names.append(header)
    for export_pair in parsed_args.export:
        owner, export = export_pair.split('=')
        log_messages.append(f'export: "{owner}" exports "{export}"')
        converter.options.add_export_module(owner, export)
    for export_suffix in parsed_args.exportsuffix:
        log_messages.append(f'export suffix: "{export_suffix}"')
        converter.options.export_suffixes.append(export_suffix)
    for ext in parsed_args.inextheader:
        log_messages.append(f'input header extension: "{ext}"')
        converter.options.add_module_action_ext_type(ext, ContentType.HEADER)
    for ext in parsed_args.inextcxx:
        log_messages.append(f'input C++ source extension: "{ext}"')
        converter.options.add_module_action_ext_type(ext, ContentType.CXX)
    if parsed_args.outextmod:
        ext = parsed_args.outextmod
        log_messages.append(f'output module interface unit extension: "{ext}"')
        converter.options.set_output_content_type_to_ext(ContentType.MODULE_INTERFACE, ext)
    if parsed_args.outextmodimpl:
        ext = parsed_args.outextmodimpl
        log_messages.append(f'output module implementation unit extension: "{ext}"')
        converter.options.set_output_content_type_to_ext(ContentType.MODULE_IMPL, ext)
    log_text = '\n'.join(log_messages)
    log(log_text)
    converter.convert_directory(directory, Path(destination))
    log(log_text)
    log(f'done, all: {converter.all_files}, convertable: {converter.convertable_files}, converted: {converter.converted_files}, copied: {converter.copied_files} ')

if __name__ == '__main__':
    sys.exit(main())
