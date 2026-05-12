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
    def __init__(self):
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
        self.join_configurations: dict[str, str] = {} # pattern -> target_module

    def add_export_module(self, owner: str, export: str):
        owner_exports = self.export.setdefault(owner, set())
        owner_exports.add(export)

    def add_module_action_ext_type(self, ext: str, type: ContentType):
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
        if not ext.startswith('.'):
            ext = '.' + ext
        if ext == '.':
            raise ValidationError("Extension cannot be empty or just a dot")
        self.content_type_to_ext[type] = ext

    def add_modules_path(self, module_prefix: str, pathStr: str):
        path = PurePosixPath(pathStr)
        if path in self.path_to_module_prefix_map:
            logging.warning(f'path {path} already mapped to module prefix {self.path_to_module_prefix_map[path]}')
            return
        self.path_to_module_prefix_map[path] = module_prefix

    def root_dir_module_name(self) -> str:
        return self.path_to_module_prefix_map.get(PurePosixPath(), '')

    def set_root_dir_module_name(self, prefix: str):
        self.add_modules_path(prefix, '')

    def add_std_module(self):
        for path in STD_MODULE_PATHS:
            self.add_modules_path(STD_MODULE, path)

    def add_std_compat_module(self):
        for path in STD_MODULE_PATHS:
            self.add_modules_path(STD_COMPAT_MODULE, path)
    
    def add_join_configuration(self, target_module: str, pattern: str):
        if pattern in self.join_configurations:
            logging.warning(f'pattern "{pattern}" already mapped to target module "{self.join_configurations[pattern]}"')
            return
        self.join_configurations[pattern] = target_module

class FileOptions:
    def __init__(self):
        self.convert_as_compat: bool = False

class FileEntryType(enum.IntEnum):
    FILE = 1
    DIR = 2

FilesMapDict: TypeAlias = dict[str, "FilesMapDict | FileEntryType"]