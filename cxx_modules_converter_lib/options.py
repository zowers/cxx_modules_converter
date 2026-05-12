from __future__ import annotations

import copy
import enum
import logging
from pathlib import Path, PurePosixPath
from typing import TypeAlias

# Re-exported from exceptions module
from .exceptions import ValidationError


class ConvertAction(enum.Enum):
    MODULES = 'modules'
    HEADERS = 'headers'

    def __str__(self) -> str:
        return self.value


AlwaysIncludeNames: TypeAlias = list[str]
always_include_names: AlwaysIncludeNames = [
    'cassert',
    'assert.h',
]

COMPAT_MACRO_DEFAULT: str = "CXX_COMPAT_HEADER"
STAR_MODULE_EXPORT: str = '*'

STD_MODULE = 'std'
STD_COMPAT_MODULE = 'std.compat'

# Standard library headers, list of files from libstdc++-14-dev
STD_MODULE_PATHS = [
    'algorithm',
    'any',
    'array',
    'atomic',
    'barrier',
    'bit',
    'bitset',
    # 'cassert',
    'ccomplex',
    'cctype',
    'cerrno',
    'cfenv',
    'cfloat',
    'charconv',
    'chrono',
    'cinttypes',
    'ciso646',
    'climits',
    'clocale',
    'cmath',
    'codecvt',
    'compare',
    'complex',
    'concepts',
    'condition_variable',
    'coroutine',
    'csetjmp',
    'csignal',
    'cstdalign',
    'cstdarg',
    'cstdbool',
    'cstddef',
    'cstdint',
    'cstdio',
    'cstdlib',
    'cstring',
    'ctgmath',
    'ctime',
    'cuchar',
    'cwchar',
    'cwctype',
    'deque',
    'exception',
    'execution',
    'expected',
    'filesystem',
    'format',
    'forward_list',
    'fstream',
    'functional',
    'future',
    'generator',
    'initializer_list',
    'iomanip',
    'ios',
    'iosfwd',
    'iostream',
    'istream',
    'iterator',
    'latch',
    'limits',
    'list',
    'locale',
    'map',
    'memory',
    'memory_resource',
    'mutex',
    'new',
    'numbers',
    'numeric',
    'optional',
    'ostream',
    'print',
    'queue',
    'random',
    'ranges',
    'ratio',
    'regex',
    'scoped_allocator',
    'semaphore',
    'set',
    'shared_mutex',
    'source_location',
    'span',
    'spanstream',
    'sstream',
    'stack',
    'stacktrace',
    'stdexcept',
    'stdfloat',
    'stop_token',
    'streambuf',
    'string',
    'string_view',
    'syncstream',
    'system_error',
    'text_encoding',
    'thread',
    'tuple',
    'typeindex',
    'typeinfo',
    'type_traits',
    'unordered_map',
    'unordered_set',
    'utility',
    'valarray',
    'variant',
    'vector',
    # 'version',
]


class ContentType(enum.IntEnum):
    HEADER = 1
    CXX = 2
    MODULE_INTERFACE = 3
    MODULE_IMPL = 4
    OTHER = 5


ExtTypes: TypeAlias = dict[str, ContentType]
ContentTypeToExt: TypeAlias = dict[ContentType, str]


class Options:
    """Configuration options for the conversion process.

    This class holds all user-configurable settings: file extensions,
    skip/compat patterns, include search paths, module naming,
    join configurations, etc.

    Attributes:
        always_include_names (list[str]): Header names that are always
            treated as system headers. Default: ['cassert', 'assert.h'].
        root_dir (Path): Root directory for module name resolution.
            Default: current directory (Path()).
        search_path (list[str]): Include search paths. Default: empty list.
        skip_patterns (list[str]): Patterns for files/directories to skip.
            Default: empty list.
        compat_patterns (list[str]): Patterns for compatibility-mode files.
            Default: empty list.
        compat_macro (str): Macro name used in compatibility headers.
            Default: 'CXX_COMPAT_HEADER'.
        export (dict[str, set[str]]): Export mapping (module → set of
            exported modules). Default: empty dict.
            Configure with `add_export_module`.
        export_suffixes (list[str]): Suffixes that trigger export import.
            Default: empty list.
        modules_ext_types (dict[str, ContentType]): Mapping from file
            extension to content type.
            Default: {'.h': ContentType.HEADER, '.cpp': ContentType.CXX}.
            Modify with `add_module_action_ext_type`.
        headers_ext_types (dict[str, ContentType]): Mapping from header
            extension to content type.
            Default: {'.cppm': ContentType.MODULE_INTERFACE,
                      '.cpp': ContentType.MODULE_IMPL}.
            Modify with `add_header_action_ext_type`.
        content_type_to_ext (dict[ContentType, str]): Output extension for
            each content type.
            Default: {HEADER: '.h', CXX: '.cpp',
                      MODULE_INTERFACE: '.cppm', MODULE_IMPL: '.cpp'}.
            Set via `set_output_content_type_to_ext`.
        path_to_module_prefix_map (dict[PurePosixPath, str]): Mapping from
            path to module prefix. Default: empty dict.
            Add mappings with `add_modules_path`.
        join_configurations (dict[str, str]): Join module partitions file
            patterns (pattern → target module). Default: empty dict.
            Add with `add_join_configuration`. Each pattern maps to the
            primary module that will contain the matching files as module
            partitions.
    """

    def __init__(self):
        """Initialize Options with default values."""
        self.always_include_names = copy.copy(always_include_names)
        self.root_dir: Path = Path()
        # self.root_dir_module_name: str = ''
        self.search_path: list[str] = []
        self.skip_patterns: list[str] = []
        self.compat_patterns: list[str] = []
        self.compat_macro: str = COMPAT_MACRO_DEFAULT
        self.export: dict[str, set[str]] = {}
        self.export_suffixes: list[str] = []
        self.modules_ext_types: ExtTypes = {
            '.h': ContentType.HEADER,
            '.cpp': ContentType.CXX,
        }
        self._modules_ext_types_is_default = set(self.modules_ext_types.values())
        self.headers_ext_types: ExtTypes = {
            '.cppm': ContentType.MODULE_INTERFACE,
            '.cpp': ContentType.MODULE_IMPL,
        }
        self._headers_ext_types_is_default = set(self.headers_ext_types.values())
        self.content_type_to_ext: ContentTypeToExt = {
            ContentType.HEADER: '.h',
            ContentType.CXX: '.cpp',
            ContentType.MODULE_INTERFACE: '.cppm',
            ContentType.MODULE_IMPL: '.cpp',
        }
        self.path_to_module_prefix_map: dict[PurePosixPath, str] = {}
        self.join_configurations: dict[str, str] = {}  # pattern -> target_module

    def add_export_module(self, owner: str, export: str):
        """Add an export mapping: module `owner` will export module `export`.

        This method corresponds to the CLI option `--export A=B`. It defines that
        module `owner` will have `export import {export};` in its interface.
        Wildcards are supported:
        - `export="*"` means "export all imports".
        - `owner="*"` means "all modules export the given module".
        - `"*"` for both means "export all from all modules".

        Args:
            owner: Name of the module that exports another module,
                or `"*"` for all modules.
            export: Name of the module to be exported,
                or `"*"` to export all imports.
        """
        owner_exports = self.export.setdefault(owner, set())
        owner_exports.add(export)

    def add_module_action_ext_type(self, ext: str, type: ContentType):
        """Add a file extension mapping for module conversion (headers → modules).

        This method corresponds to the CLI options `--inextheader` (type=HEADER)
        and `--inextcxx` (type=CXX). The first call for a given `type` replaces
        the default mapping; subsequent calls add alternative extensions.

        Args:
            ext: File extension, with or without leading dot (e.g., '.h' or 'h').
            type: Content type (ContentType.HEADER or ContentType.CXX).
        """
        if not ext.startswith('.'):
            ext = '.' + ext
        if type in self._modules_ext_types_is_default:
            # first add replaces the default
            self._modules_ext_types_is_default.remove(type)
            for e in self.modules_ext_types:
                if self.modules_ext_types[e] == type:
                    del self.modules_ext_types[e]
                    break
        self.modules_ext_types[ext] = type

    def add_header_action_ext_type(self, ext: str, type: ContentType):
        """Add a file extension mapping for header conversion (modules → headers).

        This method is used when converting modules back to headers
        (ConvertAction.HEADERS). It maps file extensions to content types
        for module interface units (.cppm) and module implementation units
        (.cpp). The first call for a given `type` replaces the default
        mapping; subsequent calls add alternative extensions.

        Args:
            ext: File extension, with or without leading dot
                (e.g., '.cppm' or 'cppm').
            type: Content type (ContentType.MODULE_INTERFACE
                or ContentType.MODULE_IMPL).
        """
        if not ext.startswith('.'):
            ext = '.' + ext
        if type in self._headers_ext_types_is_default:
            # first add replaces the default
            self._headers_ext_types_is_default.remove(type)
            for e in self.headers_ext_types:
                if self.headers_ext_types[e] == type:
                    del self.headers_ext_types[e]
                    break
        self.headers_ext_types[ext] = type

    def set_output_content_type_to_ext(self, type: ContentType, ext: str):
        """Set the output file extension for a given content type.

        This method is used by the CLI options `--outextmod` (type=MODULE_INTERFACE)
        and `--outextmodimpl` (type=MODULE_IMPL). It can also be used programmatically
        to change the output extension for any content type (HEADER, CXX, etc.).

        Args:
            type: Content type (e.g., ContentType.MODULE_INTERFACE).
            ext: File extension, with or without leading dot (e.g., '.cppm' or 'cppm').
                Cannot be empty or just a dot.

        Raises:
            ValidationError: If `ext` is empty or just a dot.
        """
        if not ext.startswith('.'):
            ext = '.' + ext
        if ext == '.':
            raise ValidationError("Extension cannot be empty or just a dot")
        self.content_type_to_ext[type] = ext

    def add_modules_path(self, module_prefix: str, pathStr: str):
        """Start a module tree `module_prefix` at the given filesystem path.

        This method corresponds to the CLI option `--modules M=P`. It defines that
        files under `pathStr` (relative to the root directory) belong to the module
        namespace `module_prefix`. Directory separators in the path are converted
        to dots (`.`) when constructing module names.

        If the same path is added multiple times, a warning is logged and the
        duplicate mapping is ignored.

        Args:
            module_prefix: Module prefix (e.g., "mymodule").
            pathStr: Filesystem path (relative to root directory). Use empty string
                for the root directory itself.
        """
        path = PurePosixPath(pathStr)
        if path in self.path_to_module_prefix_map:
            logging.warning(
                f'path {path} already mapped to module prefix {self.path_to_module_prefix_map[path]}'  # noqa: E501
            )
            return
        self.path_to_module_prefix_map[path] = module_prefix

    def root_dir_module_name(self) -> str:
        """Return the module prefix assigned to the root directory.

        Returns:
            The module prefix for the root directory (empty string if not set).
        """
        return self.path_to_module_prefix_map.get(PurePosixPath(), '')

    def set_root_dir_module_name(self, prefix: str):
        """Set the module prefix for the root directory.

        This method corresponds to the CLI option `--name`. It defines the top-level
        module name for files located directly under the root directory.

        Args:
            prefix: Module prefix (e.g., "mymodule").
        """
        self.add_modules_path(prefix, '')

    def add_std_module(self):
        """Map standard C++ library headers to the `std` module.

        This method corresponds to the CLI option `--modulestd`. It adds mappings
        for all standard header paths (e.g., `<iostream>`, `<vector>`) to the
        module name `std`. After calling this, `#include <iostream>` will be
        converted to `import std;`.
        """
        for path in STD_MODULE_PATHS:
            self.add_modules_path(STD_MODULE, path)

    def add_std_compat_module(self):
        """Map standard C++ library headers to the `std.compat` module.

        This method corresponds to the CLI option `--modulestdcompat`.
        It adds mappings for all standard header paths to the module name
        `std.compat`. This is used when compatibility headers are desired
        (e.g., `import std.compat;`).
        """
        for path in STD_MODULE_PATHS:
            self.add_modules_path(STD_COMPAT_MODULE, path)

    def add_join_configuration(self, target_module: str, pattern: str):
        """Create module `target_module` with partition modules for files
        matching `pattern`.

        This method corresponds to the CLI option `--join A=B`.
        It defines that files matching the glob `pattern` should become
        partition modules of the primary module `target_module`.
        The pattern is matched against file paths relative to the root
        directory.

        If the same pattern is added multiple times, a warning is logged
        and the duplicate configuration is ignored.

        Args:
            target_module: Name of the primary module (e.g., "A").
            pattern: Glob pattern (e.g., "A/*").
        """
        if pattern in self.join_configurations:
            logging.warning(
                f'pattern "{pattern}" already mapped to target module "{self.join_configurations[pattern]}"'  # noqa: E501
            )
            return
        self.join_configurations[pattern] = target_module


class FileOptions:
    """Per-file configuration derived from global Options.

    Instances of this class are created by the resolver for each file and contain
    file-specific settings that affect conversion.

    Attributes:
        convert_as_compat (bool): Whether the file should be converted
            in compatibility mode.
            Default: False.
    """

    def __init__(self):
        """Initialize FileOptions with default values."""
        self.convert_as_compat: bool = False


class FileEntryType(enum.IntEnum):
    FILE = 1
    DIR = 2


FilesMapDict: TypeAlias = dict[str, "FilesMapDict | FileEntryType"]
