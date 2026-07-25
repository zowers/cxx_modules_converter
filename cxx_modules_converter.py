#!/usr/bin/env python3
#
# Convert C++20 modules to headers and headers to modules
#

import argparse
import importlib.metadata
import logging
import sys
from pathlib import Path

from cxx_modules_converter_lib import (
    COMPAT_MACRO_DEFAULT,
    ContentType,
    ConvertAction,
    Converter,
    Options,
    always_include_names,
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
        description=f'Convert C++20 modules to headers and headers to modules, version: {version}',  # noqa: E501
        epilog='',
    )
    directory = '.'
    options = Options()
    parser.add_argument(
        '-s', '--directory', default=directory, help='the directory with files'
    )
    parser.add_argument(
        '-i',
        '--inplace',
        default=False,
        action='store_true',
        help='convert files in the same directory or put conversion result to destination',  # noqa: E501
    )
    parser.add_argument(
        '-d',
        '--destination',
        default=directory,
        help='destination directory where to put conversion result, ignored when --inplace is provided',  # noqa: E501
    )
    parser.add_argument(
        '-a',
        '--action',
        type=ConvertAction,
        default=ConvertAction.MODULES,
        choices=list(ConvertAction),
        help='action to perform - convert to modules or headers',
    )
    parser.add_argument(
        '-r',
        '--root',
        default=directory,
        help='resolve module names starting from this root directory, ignored when --parent',  # noqa: E501
    )
    parser.add_argument(
        '-p',
        '--parent',
        action='store_true',
        default=False,
        help='resolve module names starting from parent of source directory',
    )
    parser.add_argument(
        '-I',
        '--include',
        action='append',
        default=[],
        help='include search path, starting from root or parent directory',
    )
    parser.add_argument(
        '-n',
        '--name',
        default='',
        help='module name for modules in [root] directory which prefixes all modules',
    )
    parser.add_argument(
        '-k',
        '--skip',
        action='append',
        default=[],
        help='skip patterns - files and directories matching any pattern will not be converted or copied (fmatch is used)',  # noqa: E501
    )
    parser.add_argument(
        '-c',
        '--compat',
        action='append',
        default=[],
        help='compat patterns - files and directories matching any pattern'
        + ' will be converted in compatibility mode allowing to use as either module or header (fmatch is used)',  # noqa: E501
    )
    parser.add_argument(
        '-m',
        '--compat-macro',
        default=COMPAT_MACRO_DEFAULT,
        help='compatibility macro name used in compat modules and headers',
    )
    parser.add_argument(
        '-e',
        '--header',
        action='append',
        default=always_include_names,
        help='always include headers with matching names and copy them as is (fmatch is used)',  # noqa: E501
    )
    parser.add_argument(
        '--export',
        action='append',
        default=[],
        help='A=B means module A exports module B, i.e. `--export A=B` means module A will have `export import B;`.'  # noqa: E501
        + ' use `--export "A=*"` to export all imports.'
        + ' use `--export "*=B"` to export B from all modules.'
        + ' use `--export "*=*"` to export all from all modules.',
    )
    parser.add_argument(
        '--exportsuffix',
        action='append',
        default=[],
        help='export module suffix for which `export import` is used instead of simple `import`',  # noqa: E501
    )
    parser.add_argument(
        '--inextheader',
        action='append',
        default=[],
        help='input header file extensions, .h by default. first use replaces the default, subsequent uses append.',  # noqa: E501
    )
    parser.add_argument(
        '--inextcxx',
        action='append',
        default=[],
        help='input C++ source file extensions, .cpp by default. first use replaces the default, subsequent uses append.',  # noqa: E501
    )
    parser.add_argument(
        '--inextmod',
        action='append',
        default=[],
        help='input module interface extensions for headers action, .cppm by default. first use replaces the default, subsequent uses append.',  # noqa: E501
    )
    parser.add_argument(
        '--inextmodimpl',
        action='append',
        default=[],
        help='input module implementation extensions for headers action, .cpp by default. first use replaces the default, subsequent uses append.',  # noqa: E501
    )
    parser.add_argument(
        '--outextmod',
        help=f'output module interface unit file extensions. default: {options.content_type_to_ext[ContentType.MODULE_INTERFACE]}',  # noqa: E501
    )
    parser.add_argument(
        '--outextmodimpl',
        help=f'output module implementation unit file extensions. default: {options.content_type_to_ext[ContentType.MODULE_IMPL]}',  # noqa: E501
    )
    parser.add_argument(
        '--outextheader',
        help=f'output header extension. default: {options.content_type_to_ext[ContentType.HEADER]}',  # noqa: E501
    )
    parser.add_argument(
        '--outextcxx',
        help=f'output C++ source extension. default: {options.content_type_to_ext[ContentType.CXX]}',  # noqa: E501
    )
    parser.add_argument(
        '--modules',
        action='append',
        default=[],
        help='`M=P`: start modules tree `M` at path `P`, directory separator is converted to `.` (dot). Default: use directory name and file name as module name.',  # noqa: E501
    )
    parser.add_argument(
        '--modulestd',
        default=False,
        action='store_true',
        help='Enable `std` module, i.e. define `--modules vector=std` to replace `vector` and other standard headers to `import std;`.',  # noqa: E501
    )
    parser.add_argument(
        '--modulestdcompat',
        default=False,
        action='store_true',
        help='Enable `std.compat` module, i.e. define `--modules vector=std.compat` to replace `vector` and other standard headers to `import std.compat;`.',  # noqa: E501
    )
    parser.add_argument(
        '--join',
        action='append',
        default=[],
        help='A=B means create module A with partition modules for files matching pattern B. '  # noqa: E501
        'Example: --join A=A/* creates module A with partitions for all files in A/ directory.',  # noqa: E501
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Set logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO',
    )
    parser.add_argument(
        '-v', '--version', default=False, action='store_true', help='show version'
    )
    parsed_args = parser.parse_args(argv)
    return parsed_args


def main():
    parsed_args = parse_args()
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, parsed_args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    logger = logging.getLogger(__name__)

    if parsed_args.version:
        version = get_version()
        logger.info(f'{version}')
        return
    if not parsed_args.directory:
        logger.error('--directory argument is required')
        return 1
    try:
        log_messages: list[str] = []
        log_messages.append(
            f'converting files of directory "{parsed_args.directory}" to {parsed_args.action} {"inplace" if parsed_args.inplace else " into " + parsed_args.destination}'  # noqa: E501
        )
        if parsed_args.inplace:
            destination = parsed_args.directory
        else:
            destination = parsed_args.destination
            if destination == parsed_args.directory:
                raise ValueError(
                    "Destination directory must be different from source directory when not using --inplace"  # noqa: E501
                )
        path = Path(parsed_args.directory)
        converter = Converter(parsed_args.action)
        if parsed_args.parent:
            parsed_args.root = path.parent
        if parsed_args.root:
            root_dir = Path(parsed_args.root)
            converter.options.root_dir = root_dir
        else:
            converter.options.root_dir = path
        converter.options.set_root_dir_module_name(parsed_args.name)
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
        for ext in parsed_args.inextmod:
            log_messages.append(f'input module interface extension: "{ext}"')
            converter.options.add_header_action_ext_type(
                ext, ContentType.MODULE_INTERFACE
            )
        for ext in parsed_args.inextmodimpl:
            log_messages.append(f'input module implementation extension: "{ext}"')
            converter.options.add_header_action_ext_type(ext, ContentType.MODULE_IMPL)
        if parsed_args.outextmod:
            ext = parsed_args.outextmod
            log_messages.append(f'output module interface unit extension: "{ext}"')
            converter.options.set_output_content_type_to_ext(
                ContentType.MODULE_INTERFACE, ext
            )
        if parsed_args.outextmodimpl:
            ext = parsed_args.outextmodimpl
            log_messages.append(f'output module implementation unit extension: "{ext}"')
            converter.options.set_output_content_type_to_ext(
                ContentType.MODULE_IMPL, ext
            )
        if parsed_args.outextheader:
            ext = parsed_args.outextheader
            log_messages.append(f'output header extension: "{ext}"')
            converter.options.set_output_content_type_to_ext(ContentType.HEADER, ext)
        if parsed_args.outextcxx:
            ext = parsed_args.outextcxx
            log_messages.append(f'output C++ source extension: "{ext}"')
            converter.options.set_output_content_type_to_ext(ContentType.CXX, ext)
        for modules_pair in parsed_args.modules:
            module_prefix, path = modules_pair.split('=')
            log_messages.append(f'module prefix: "{module_prefix}" in path "{path}"')
            converter.options.add_modules_path(module_prefix, path)
        if parsed_args.modulestd:
            if parsed_args.modulestdcompat:
                raise ValueError("Cannot use both --modulestd and --modulestdcompat")
            log_messages.append(f'module std: "std"')
            converter.options.add_std_module()
        if parsed_args.modulestdcompat:
            if parsed_args.modulestd:
                raise ValueError("Cannot use both --modulestd and --modulestdcompat")
            log_messages.append(f'module std.compat: "std.compat"')
            converter.options.add_std_compat_module()
        for join_pair in parsed_args.join:
            target_module, pattern = join_pair.split('=', 1)
            log_messages.append(f'join: "{target_module}" from pattern "{pattern}"')
            converter.options.add_join_configuration(target_module, pattern)
        log_text = '\n'.join(log_messages)
        logger.info(log_text)
        converter.convert_directory(path, Path(destination))
        logger.info(
            f'done, all: {converter.all_files}, convertable: {converter.convertable_files}, converted: {converter.converted_files}, copied: {converter.copied_files}'  # noqa: E501
        )
    except Exception as e:
        logger.error(f'Error: {e}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
