from __future__ import annotations

from collections.abc import Callable
import copy
import enum
import os
import os.path
from pathlib import Path, PurePosixPath
import re
import shutil

from typing import Any, cast
try:
    # make pylance happy
    from typing import TypeAlias as TypeAlias2
except ImportError:
    TypeAlias2 = Any
TypeAlias = TypeAlias2

class ConvertAction(enum.Enum):
    MODULES = 'modules'
    HEADERS = 'headers'

    def __str__(self) -> str:
        return self.value

AlwaysIncludeNames: TypeAlias = set[str]
always_include_names = [
    'cassert',
    'assert.h',
]

COMPAT_MACRO_DEFAULT: str = "CXX_COMPAT_HEADER"
STAR_MODULE_EXPORT: str = '*'

class ContentType(enum.Enum):
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
        self.root_dir_module_name: str = ''
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
        assert(ext != '.')
        self.content_type_to_ext[type] = ext

class FileOptions:
    def __init__(self):
        self.convert_as_compat: bool = False

def filename_to_module_name(filename: PurePosixPath) -> str:
    parts = os.path.splitext(filename)
    result = parts[0].replace('/', '.').replace('\\', '.')
    return result

class FileEntryType(enum.Enum):
    FILE = 1
    DIR = 2

FilesMapDict: TypeAlias = dict[str, "FilesMapDict | FileEntryType"]

class FilesMap:
    def __init__(self):
        self.value: FilesMapDict = {}

    def find(self, path: PurePosixPath) -> FilesMapDict | FileEntryType | None:
        value: FilesMapDict = self.value
        for part in path.parts:
            if not value:
                break
            nextValue = value.get(part, None)
            if type(nextValue) is not dict:
                return nextValue
            value = nextValue
        return value

    def add_filesystem_directory(self, path: Path):
        for (root, dirs, files) in os.walk(path):
            relative_root = Path(os.path.relpath(root, path))
            if relative_root == Path(''):
                root_node: FilesMapDict = self.value
            else:
                parent_node = self.find(PurePosixPath(relative_root.parent))
                assert(type(parent_node) is dict)
                root_node = parent_node[relative_root.name] = {}

            for name in dirs:
                root_node[name] = {}
            for name in files:
                root_node[name] = FileEntryType.FILE
    
    def add_files_map_dict(self, other: FilesMapDict):
        self.value.update(other)

ActionExtTypes: TypeAlias = dict[ConvertAction, ExtTypes]

class FilesResolver:
    def __init__(self, options: Options):
        self.options: Options = options
        self.files_map = FilesMap()
        self.source_ext_types: ActionExtTypes = {
            ConvertAction.MODULES: self.options.modules_ext_types,
            ConvertAction.HEADERS: self.options.headers_ext_types,
        }
        self.destination_ext_types: ActionExtTypes = {
            ConvertAction.HEADERS: self.options.modules_ext_types,
            ConvertAction.MODULES: self.options.headers_ext_types,
        }
    
    def resolve_in_search_path(self, current_dir: Path, current_filename: str|Path, include_filename: str, is_quote: bool) -> PurePosixPath | None:
        include_path = PurePosixPath(include_filename)
        # search relative to root
        if self.files_map.find(include_path):
            return include_path
        # search relative to current_dir
        full_path = PurePosixPath(current_dir.joinpath(include_path))
        if is_quote and self.files_map.find(full_path):
            return full_path
        # search in search_path
        for search_path_item in self.options.search_path:
            path = PurePosixPath(search_path_item).joinpath(include_path)
            if self.files_map.find(path):
                return path
        if is_quote:
            print(f'warning: file not found: "{include_filename}" referenced from "{current_filename}"')
            return include_path
        return None

    def convert_filename_to_module_name(self, filename: PurePosixPath) -> str:
        full_name = filename
        if self.options.root_dir_module_name and self.files_map.find(filename):
            full_name = PurePosixPath(self.options.root_dir_module_name).joinpath(filename)
        module_name = filename_to_module_name(full_name)
        return module_name

    def get_source_content_type(self, action: ConvertAction, filename: Path) -> ContentType:
        parts = os.path.splitext(filename)
        extension = parts[-1]
        action_ext_types = self.source_ext_types[action]
        return action_ext_types.get(extension, ContentType.OTHER)

    def convert_filename_to_content_type(self, filename: Path, content_type: ContentType) -> str:
        parts = os.path.splitext(filename)
        new_extension = self.options.content_type_to_ext[content_type]
        new_filename = parts[0] + new_extension
        return new_filename

class ModuleFilesResolver:
    def __init__(self, parent_resolver: FilesResolver, options: Options):
        self.parent_resolver: FilesResolver = parent_resolver
        self.options: Options = options
        self.module_filename: Path = Path()
        self.module_dir: Path = Path()

    def set_filename(self, filename: Path):
        self.module_filename = filename
        self.module_dir = self.module_filename.parent

    def resolve_include(self, include_filename: str, is_quote: bool) -> PurePosixPath | None:
        result = self.parent_resolver.resolve_in_search_path(self.module_dir, self.module_filename, include_filename, is_quote)
        return result

    def resolve_include_to_module_name(self, include_filename: str, is_quote: bool) -> str | None:
        resolved_include_filename = self.parent_resolver.resolve_in_search_path(self.module_dir, self.module_filename, include_filename, is_quote)
        if resolved_include_filename is None:
            return None
        result = self.parent_resolver.convert_filename_to_module_name(resolved_include_filename)
        return result

ContentTypeToName: TypeAlias = dict[ContentType, str]
content_type_to_name: ContentTypeToName = {
    ContentType.HEADER: 'header',
    ContentType.CXX: 'source',
    ContentType.MODULE_INTERFACE: 'module interface unit',
    ContentType.MODULE_IMPL: 'module implementation unit',
}

ContentTypeToConverted: TypeAlias = dict[ContentType, ContentType]
content_type_to_converted: ContentTypeToConverted = {
    ContentType.HEADER: ContentType.MODULE_INTERFACE,
    ContentType.CXX: ContentType.MODULE_IMPL,
    ContentType.MODULE_INTERFACE: ContentType.HEADER,
    ContentType.MODULE_IMPL: ContentType.CXX,
}

interface_content_types: set[ContentType] = {ContentType.MODULE_INTERFACE, ContentType.HEADER}

def get_converted_content_type(content_type: ContentType) -> ContentType:
    return content_type_to_converted[content_type]

class FileContent:
    def __init__(self, filename: str|Path, content_type: ContentType, content: str):
        self.filename: Path = Path(filename)
        self.content_type: ContentType = content_type
        self.content: str = content

    def __repr__(self):
        return str(self.__dict__)

    def __eq__(self, other: object):
        return self.__dict__ == other.__dict__

FileContentList: TypeAlias = list[FileContent]

StrList: TypeAlias = list[str]
new_line = '\n'

class LineCompatibility(enum.Enum):
    GLOBAL_MODULE_FRAGMENT = 1
    MODULE_CONTENT = 2
    ANY = 3

# regex: spaces only
spaces_rx = re.compile(r'''^\s*$''')
# regex: #include <brackets_header.h>
preprocessor_include_brackets_rx = re.compile(r'''^(\s*)#(\s*)include\s*<(.+)>(.*)$''')
# regex: #include "quote_header.h"
preprocessor_include_quote_rx = re.compile(r'''^(\s*)#(\s*)include\s*"(.+)"(.*)$''')
# regex: line comment
preprocessor_line_comment_rx = re.compile(r'''^\s*//.*$''')
# regex: block comment start
preprocessor_block_comment_rx = re.compile(r'''^\s*/\*.*$''')
# regex: block comment end
preprocessor_block_comment_rx = re.compile(r'''^\s*\*/.*$''')
# regex: #if
preprocessor_if_rx = re.compile(r'''^\s*#\s*if.*''')
# regex: #endif
preprocessor_endif_rx = re.compile(r'''^\s*#\s*endif.*$''')
# regex: #define
preprocessor_define_rx = re.compile(r'''^\s*#\s*define.*''')
# regex: #error
# regex: #elif
# regex: #else
# regex: #pragma
# regex: #warning
preprocessor_other_rx = re.compile(r'''^\s*#\s*(error|elif|else|pragma|warning).*''')
# regex: #pragma once
preprocessor_pragma_once_rx = re.compile(r'''^\s*#\s*pragma\s+once.*$''')

class FileBaseBuilder:
    content_type: ContentType = ContentType.OTHER

    def __init__(self, options: Options, parent_resolver: FilesResolver):
        self.options: Options = options
        self.parent_resolver: FilesResolver = parent_resolver
        self.source_filename: Path = Path('')

    def set_source_filename(self, source_filename: Path):
        self.source_filename = source_filename

    def converted_filename(self) -> str:
        return self.parent_resolver.convert_filename_to_content_type(self.source_filename, self.content_type)

    def build_result(self) -> str:
        raise NotImplementedError('build_result')

    def build_file_content(self) -> FileContent:
        content = self.build_result()
        return FileContent(self.converted_filename(), self.content_type, content)

class ModuleBaseBuilder(FileBaseBuilder):
    module_purview_start_prefix: str = ''   # 'module' or 'export module' - overriden in implementation classes
    content_type: ContentType = ContentType.OTHER

    def __init__(self, options: Options, parent_resolver: FilesResolver, file_options: FileOptions):
        super().__init__(options, parent_resolver)
        self.file_options: FileOptions = file_options
        self.resolver: ModuleFilesResolver = ModuleFilesResolver(self.parent_resolver, self.options)
        self.module_name: str = ''                   # name of the module
        self.file_copyright: StrList = []            # // File copyright
        self.global_module_fragment_start: StrList = []  # module;
        self.global_module_fragment_compat_includes: StrList = []    # compat header includes
        self.global_module_fragment_compat_end: StrList = []    # compat header includes endif
        self.global_module_fragment: StrList = []    # header includes
        self.module_purview_start: StrList = []      # export module <name>; // Start of module purview.
        # self.module_imports: StrList = []
        # self.module_purview_special_headers: StrList = [] # // Configuration, export, etc.
        self.module_content: StrList = []
        self.main_module_content_index: int|None = None

        self.module_staging: StrList = [] # staging area for next module entry
        self.flushed_module_preprocessor_nesting_count: int = 0 # count of opened preprocessor #if statements flushed to module content
        self.global_module_fragment_staging: StrList = [] # staging area for next global_module_fragment entry
        self.preprocessor_nesting_count: int = 0 # count of opened preprocessor #if statements
        self.global_module_fragment_includes_count: int = 0 # count of #include <> statements
        self.flushed_global_module_fragment_includes_count: int = 0 # count of #include <> statements flushed to global module content
        self.module_staging_last_unnested_index: int = 0 # last index in module staging without opened preprocessor #if statements

    def set_source_filename(self, source_filename: Path):
        super().set_source_filename(source_filename)
        self.resolver.set_filename(source_filename)
        self.set_module_name(self.parent_resolver.convert_filename_to_module_name(PurePosixPath(source_filename)))

    def set_module_name(self, name: str):
        assert(not self.module_name)
        self.module_name = name

    def set_is_actually_module(self) -> None:
        if self.global_module_fragment:
            self.set_global_module_fragment_start()

    def get_is_actually_module(self) -> bool:
        raise NotImplementedError('get_is_actually_module')

    def get_module_interface_builder(self) -> ModuleInterfaceUnitBuilder | None:
        raise NotImplementedError('get_module_interface_builder')

    def set_global_module_fragment_start(self):
        if self.global_module_fragment_start:
            return
        if not self.get_is_actually_module():
            return
        if self.convert_as_compat_header():
            self.global_module_fragment_start = [
                f'''#ifndef {self.options.compat_macro}''',
                f'''module;''',
                f'''#else''',
                f'''#pragma once''',
            ]
            self.global_module_fragment_compat_end = [
                f'''#endif''',
            ]
        else:
            self.global_module_fragment_start = [
                'module;'
            ]

    def set_module_purview_start(self):
        if self.module_purview_start:
            return
        if not self.get_is_actually_module():
            return
        assert(self.module_purview_start_prefix)
        assert(self.module_name)
        module_purview_start = f'''{self.module_purview_start_prefix} {self.module_name};'''
        self.module_purview_start = self.wrap_in_compat_macro_if_compat_header([
            module_purview_start
        ])

    def add_file_copyright(self, line: str):
        self.file_copyright.append(line)

    def _flush_global_module_fragment(self):
        self.flushed_global_module_fragment_includes_count = 0
        if self.preprocessor_nesting_count != 0:
            return
        if self.global_module_fragment_includes_count == 0 and not self.convert_as_compat_header():
            return
        self.set_global_module_fragment_start()
        for line in self.global_module_fragment_staging:
            self.global_module_fragment.append(line)
        self.global_module_fragment_staging = []
        self.flushed_global_module_fragment_includes_count = self.global_module_fragment_includes_count
        self.global_module_fragment_includes_count = 0
        self._flush_module_staging()

    def add_global_module_fragment(self, line: str):
        self.global_module_fragment_includes_count += 1
        self._add_global_module_fragment_staging(line, 0)
        self._flush_global_module_fragment()

    def handle_preprocessor(self, line: str, nesting_advance: int):
        self.add_staging(line, nesting_advance)

    def add_staging(self, line: str, nesting_advance: int):
        self.preprocessor_nesting_count += nesting_advance
        self._add_module_staging(line, nesting_advance)
        self._add_global_module_fragment_staging(line, nesting_advance)

    def _add_global_module_fragment_staging(self, line: str, nesting_advance: int):
        self.global_module_fragment_staging.append(line)
        self._flush_global_module_fragment()

    def add_module_purview_special_headers(self, line: str):
        self.set_module_purview_start()
        # self.module_purview_special_headers.append(line)

    def handle_main_content(self, line: str):
        self._flush_module_staging(self._set_main_module_content_start)
        self.add_module_content(line)

    def _set_main_module_content_start(self):
        if self.main_module_content_index is None:
            self.main_module_content_index = len(self.module_content)

    def _mark_module_interface_unit_export(self):
        if self.main_module_content_index is None:
            return
        module_start = []
        module_end = []
        if self.file_options.convert_as_compat:
            # wrap module content in extern "C++" {}
            module_start = [
                '''extern "C++" {'''
                ]
            module_end = [
                '''} // extern "C++"'''
                ]
        if self.content_type == ContentType.MODULE_INTERFACE:
            # wrap module interface unit in export {}
            module_start = [
                '''export {'''
            ] + module_start
            module_end = module_end + [
                '''} // export'''
            ]
        if self.file_options.convert_as_compat:
            # wrap in #ifdef CXX_COMPAT_HEADER/#endif
            module_start = self.wrap_in_compat_macro_if_compat_header(module_start)
            module_end = self.wrap_in_compat_macro_if_compat_header(module_end)
        for line in reversed(module_start):
            self.module_content.insert(self.main_module_content_index, line)
        self.module_content = self.module_content + module_end

    def add_module_content(self, line: str):
        self._flush_module_staging()
        self.set_module_purview_start()
        self.module_content.append(line)

    def _add_module_staging(self, line: str, nesting_advance: int):
        if (self.preprocessor_nesting_count == 0 and nesting_advance == 0
            or self.preprocessor_nesting_count == 1 and nesting_advance == 1):
            self.module_staging_last_unnested_index = len(self.module_staging)
        self.module_staging.append(line)
        if (self.preprocessor_nesting_count == 0 and nesting_advance == -1):
            self.module_staging_last_unnested_index = len(self.module_staging)

    def _flush_module_staging(self, last_unnested_inserter: Callable[[], None] | None = None):
        self.set_module_purview_start()
        if self.flushed_global_module_fragment_includes_count == 0 or self.flushed_module_preprocessor_nesting_count != 0:
            for i in range(len(self.module_staging)):
                if last_unnested_inserter and i == self.module_staging_last_unnested_index:
                    last_unnested_inserter()
                line = self.module_staging[i]
                self.module_content.append(line)
            if last_unnested_inserter and self.module_staging_last_unnested_index == len(self.module_staging):
                last_unnested_inserter()
        self.module_staging = []
        self.flushed_module_preprocessor_nesting_count = self.preprocessor_nesting_count
        self.flushed_global_module_fragment_includes_count = 0
        self.module_staging_last_unnested_index = 0

    def convert_as_compat_header(self):
        return self.file_options.convert_as_compat and self.content_type == ContentType.MODULE_INTERFACE

    def wrap_in_compat_macro_if_compat_header(self, lines: StrList):
        if self.convert_as_compat_header():
            return [
                f'''#ifndef {self.options.compat_macro}''',
            ] + lines + [
                f'''#endif''', # end compat_macro
            ]
        else:
            return lines

    def handle_include_brackets(self, line: str, match: re.Match[str] | None = None):
        if self.convert_as_compat_header():
            self.add_compat_include(line)
        self.add_module_import_from_include(line, match, False)
        # self.add_global_module_fragment(line)

    def handle_include_quote(self, line: str, match: re.Match[str] | None = None):
        if self.convert_as_compat_header():
            self.add_compat_include(line)
        self.add_module_import_from_include(line, match, True)

    def handle_pragma_once(self, line: str):
        self._add_module_staging(f'''// {line}''', 0)

    def add_module_import_from_include(self, line: str, match: re.Match[str] | None = None, is_quote: bool = False):
        self.set_module_purview_start()
        if not match:
            match = preprocessor_include_quote_rx.match(line)
        if not match:
            print('warning: preprocessor_include_local_rx not matched')
            self.add_module_content(line)
            return

        line_space1 = match[1]
        line_space2 = match[1]
        line_include_filename = match[3]
        line_tail = match[4]

        resolved_include_filename = self.resolver.resolve_include(line_include_filename, is_quote)
        if resolved_include_filename is None:
            self.add_global_module_fragment(line)
            return
        if any_pattern_maches(self.options.always_include_names, resolved_include_filename):
            self.add_global_module_fragment(line)
            return
        
        line_module_name = self.resolver.resolve_include_to_module_name(line_include_filename, is_quote)
        if line_module_name is None:
            self.add_global_module_fragment(line)
            return
        if line_module_name == self.module_name:
            self.set_is_actually_module()
            self.set_module_purview_start()
            return

        export_opt = '''export ''' if self._needs_export_for_import(line_module_name) else ''

        import_line = f'''{line_space1}{line_space2}{export_opt}import {line_module_name};{line_tail}'''
        import_lines = self.wrap_in_compat_macro_if_compat_header([import_line])
        for import_line in import_lines:
            self.add_module_content(import_line)
    
    def _needs_export_for_import(self, import_module_name: str) -> bool:
        if self.content_type != ContentType.MODULE_INTERFACE:
            return False
        owner_exports = self.options.export.get(self.module_name)
        if owner_exports and (import_module_name in owner_exports or STAR_MODULE_EXPORT in owner_exports):
            return True
        star_owner_exports = self.options.export.get(STAR_MODULE_EXPORT)
        if star_owner_exports and (import_module_name in star_owner_exports or STAR_MODULE_EXPORT in star_owner_exports):
            return True
        for suffix in self.options.export_suffixes:
            if self.module_name + suffix == import_module_name:
                return True
        return False

    def add_compat_include(self, line: str):
        self.set_global_module_fragment_start()
        self.global_module_fragment_compat_includes.append(line)

    def build_result(self):
        if self.global_module_fragment or self.global_module_fragment_compat_includes:
            assert(bool(self.global_module_fragment_start) == self.get_is_actually_module())
        module_interface_builder = self.get_module_interface_builder()
        if (self.content_type == ContentType.MODULE_IMPL and self.get_is_actually_module()
            and module_interface_builder and module_interface_builder.global_module_fragment):
            # include interface GMF at the start of impl GMF
            self.set_global_module_fragment_start()
            self.global_module_fragment = module_interface_builder.global_module_fragment + self.global_module_fragment
        self._flush_module_staging()
        self._mark_module_interface_unit_export()
        parts = [
            new_line.join(self.file_copyright),
            new_line.join(self.global_module_fragment_start),
            new_line.join(self.global_module_fragment_compat_includes),
            new_line.join(self.global_module_fragment_compat_end),
            new_line.join(self.global_module_fragment),
            new_line.join(self.module_purview_start),
            # new_line.join(self.module_imports),
            # new_line.join(self.module_purview_special_headers),
            new_line.join(self.module_content),
            ]
        parts = filter(None, parts) # remove empty parts
        return new_line.join(parts) + new_line

class ModuleInterfaceUnitBuilder(ModuleBaseBuilder):
    content_type = ContentType.MODULE_INTERFACE
    '''
// Module interface unit.

// File copyright

module;                    // Start of global module fragment.

<header includes>

export module <name>;      // Start of module purview.

<module imports>

<special header includes>  // Configuration, export, etc.

<module interface>

<inline/template includes>
    '''
    module_purview_start_prefix: str = 'export module'

    def set_is_actually_module(self) -> None:
        pass

    def get_is_actually_module(self) -> bool:
        '''module interface unit is always actually module'''
        return True

    def get_module_interface_builder(self) -> ModuleInterfaceUnitBuilder | None:
        return None

class ModuleImplUnitBuilder(ModuleBaseBuilder):
    content_type = ContentType.MODULE_IMPL
    '''
// Module implementation unit.

// File copyright

module;                    // Start of global module fragment.

<header includes>

module <name>;             // Start of module purview.

<extra module imports>     // Only additional to interface.

<module implementation>
    '''
    module_purview_start_prefix: str = 'module'

    def __init__(self, options: Options, parent_resolver: FilesResolver, file_options: FileOptions):
        super().__init__(options, parent_resolver, file_options)
        self._is_actually_module = False
        self.module_interface_builder: ModuleInterfaceUnitBuilder | None = None

    def set_is_actually_module(self) -> None:
        self._is_actually_module = True
        super().set_is_actually_module()

    def get_is_actually_module(self) -> bool:
        return self._is_actually_module

    def get_module_interface_builder(self) -> ModuleInterfaceUnitBuilder | None:
        return self.module_interface_builder

    def set_module_interface_builder(self, module_interface_builder: ModuleInterfaceUnitBuilder | None):
        self.module_interface_builder = module_interface_builder

class CompatHeaderBuilder(FileBaseBuilder):
    content_type = ContentType.HEADER
    def __init__(self, options: Options, module_builder: ModuleBaseBuilder):
        super().__init__(options, module_builder.parent_resolver)
        self.module_builder: ModuleBaseBuilder = module_builder
        assert(module_builder.content_type == ContentType.MODULE_INTERFACE)
        module_interface_unit_filename: str = module_builder.converted_filename()
        assert(module_interface_unit_filename)
        self.relative_module_interface_unit_filename: str = os.path.basename(module_interface_unit_filename)

    def build_result(self) -> str:
        compat_macro = self.options.compat_macro
        assert(compat_macro)
        relative_module_interface_unit_filename = self.relative_module_interface_unit_filename
        parts = [
            f'''#pragma once''',
            f'''#ifndef {compat_macro}''',
            f'''#define {compat_macro}''',
            f'''#include "{relative_module_interface_unit_filename}"''',
            f'''#undef {compat_macro}''',
            f'''#else''',
            f'''#include "{relative_module_interface_unit_filename}"''',
            f'''#endif''',
        ]
        return new_line.join(parts) + new_line

class HeaderScanState(enum.Enum):
    START = enum.auto()
    FILE_COMMENT = enum.auto()
    MAIN = enum.auto()

class Matcher:
    def __init__(self):
        self.rx: re.Pattern[str] | None = None
        self.matched: re.Match[str] | None = None
    def match(self, rx: re.Pattern[str], s: str) -> re.Match[str] | None:
        self.rx = rx
        self.matched = self.rx.match(s)
        return self.matched

class Converter:

    def __init__(self, action: ConvertAction):
        self.action = action
        self.options = Options()
        self.resolver = FilesResolver(self.options)
        self.all_files = 0
        self.convertable_files = 0
        self.converted_files = 0
        self.copied_files = 0
        self.module_interface_builders: dict[str, ModuleInterfaceUnitBuilder] = {}
    
    def convert_file_content_to_module(self, content: str, filename: Path, content_type: ContentType, file_options: FileOptions) -> FileContentList:
        if content_type in {ContentType.MODULE_INTERFACE, ContentType.MODULE_IMPL}:
            return [FileContent(filename, content_type, content)]
        content_lines = content.splitlines()

        builder = self.make_builder_to_module(filename, content_type, file_options)

        is_comment = lambda: (not line
            or line2 == '//'
            or line2 == '/*'
            or line3 == '\ufeff//'
            or line3 == '\ufeff/*')

        scanState = HeaderScanState.START
        i = 0
        while i < len(content_lines):
            line = content_lines[i]
            while line and line[-1] == '\\' and i+1 < len(content_lines):
                # handle backslash \ as last character on line -- line continues on next line
                i += 1
                line += new_line + content_lines[i]
            line2 = line[0:2]
            line3 = line[0:3]
            if scanState == HeaderScanState.START:
                    if is_comment():
                        scanState = HeaderScanState.FILE_COMMENT
                        continue
                    else:
                        scanState = HeaderScanState.MAIN
                        continue
            elif scanState == HeaderScanState.FILE_COMMENT:
                    line2 = line.strip()[0:2] 
                    if (is_comment()
                        or line2[0] == '*'
                        ):
                        builder.add_file_copyright(line)
                    else:
                        scanState = HeaderScanState.MAIN
                        continue
            elif scanState == HeaderScanState.MAIN:
                    m = Matcher()
                    if m.match(preprocessor_include_brackets_rx, line):
                        builder.handle_include_brackets(line, m.matched)
                    elif m.match(preprocessor_include_quote_rx, line):
                        builder.handle_include_quote(line, m.matched)
                    elif m.match(preprocessor_pragma_once_rx, line):
                        builder.handle_pragma_once(line)
                    elif (m.match(preprocessor_line_comment_rx, line)
                          or m.match(preprocessor_other_rx, line)
                          or m.match(spaces_rx, line)):
                        builder.handle_preprocessor(line, 0)
                    elif (m.match(preprocessor_define_rx, line)):
                        builder.handle_preprocessor(line, 0)
                    elif m.match(preprocessor_if_rx, line):
                        builder.handle_preprocessor(line, 1)
                    elif m.match(preprocessor_endif_rx, line):
                        builder.handle_preprocessor(line, -1)
                    else:
                        builder.handle_main_content(line)
            i += 1

        result: FileContentList = []
        result.append(builder.build_file_content())

        if file_options.convert_as_compat and builder.content_type == ContentType.MODULE_INTERFACE:
            compat_header_builder = CompatHeaderBuilder(self.options, builder)
            compat_header_builder.set_source_filename(Path(filename))
            result.append(compat_header_builder.build_file_content())

        return result
    
    def make_builder_to_module(self, filename: str|Path, content_type: ContentType, file_options: FileOptions|None = None) -> ModuleBaseBuilder:
        filename = Path(filename)
        if not file_options:
            file_options = FileOptions()
        if content_type == ContentType.HEADER:
            builder = ModuleInterfaceUnitBuilder(self.options, self.resolver, file_options)
        elif content_type == ContentType.CXX:
            builder = ModuleImplUnitBuilder(self.options, self.resolver, file_options)
        else:
                raise RuntimeError(f'Unknown content type {content_type}')
        
        builder.set_source_filename(filename)

        if content_type == ContentType.HEADER:
            self.module_interface_builders[builder.module_name] = cast(ModuleInterfaceUnitBuilder, builder)
        elif content_type == ContentType.CXX:
            cast(ModuleImplUnitBuilder, builder).set_module_interface_builder(self.module_interface_builders.get(builder.module_name, None))
        return builder

    def convert_file_content_to_headers(self, content: str, filename: Path, content_type: ContentType, file_options: FileOptions) -> FileContentList:
        if content_type in {ContentType.HEADER, ContentType.CXX}:
            return [FileContent(filename, content_type, content)]
        return [FileContent(filename, content_type, content)]

    def convert_file_content(self, content: str, filename: str|Path, file_options: FileOptions|None = None) -> FileContentList:
        filename = Path(filename)
        if file_options is None:
            file_options = FileOptions()
        action = self.action
        content_type = self.resolver.get_source_content_type(action, filename)
        if action == ConvertAction.MODULES:
            return self.convert_file_content_to_module(content, filename, content_type, file_options)
        elif action == ConvertAction.HEADERS:
            return self.convert_file_content_to_headers(content, filename, content_type, file_options)
        else:
            raise RuntimeError(f'Unknown action: "{action}"')

    def convert_file(self, source_directory: Path, destination_directory: Path, filename: Path, file_options: FileOptions) -> FileContentList:
        self.convertable_files += 1
        with open(source_directory.joinpath(filename)) as source_file:
            source_content = source_file.read()
        converted_files = self.convert_file_content(source_content, filename, file_options)
        for converted_file in converted_files:
            converted_content = converted_file.content
            converted_filename = converted_file.filename
            self._create_or_update_file_content_if_diff(destination_directory.joinpath(converted_filename), converted_content)
        return converted_files
    
    def _create_or_update_file_content_if_diff(self, file_path: Path, content: str):
        if file_path.exists():
            with open(file_path, 'r') as existing_destination_file:
                existing_file_content = existing_destination_file.read()
                if existing_file_content == content:
                    return
        with open(file_path, 'w') as destination_file:
            destination_file.write(content)
        self.converted_files += 1

    def convert_or_copy_file(self, source_directory: Path, destination_directory: Path, filename: Path, file_options: FileOptions):
        self.all_files += 1
        content_type = self.resolver.get_source_content_type(self.action, filename)
        if content_type == ContentType.OTHER or any_pattern_maches(self.options.always_include_names, PurePosixPath(filename)):
            self._copy_file_content_if_diff(source_directory.joinpath(filename), destination_directory.joinpath(filename))
        else:
            print('converting', filename)
            converted_files = self.convert_file(source_directory, destination_directory, filename, file_options)
            for converted_file in converted_files:
                print('converted ', converted_file.filename, '\t', converted_file.content_type)

    def _copy_file_content_if_diff(self, source_file_path: Path, destination_file_path: Path):
        with open(source_file_path, 'rb') as source_file:
            source_file_content = source_file.read()
        if destination_file_path.exists():
            with open(destination_file_path, 'rb') as existing_destination_file:
                existing_file_content = existing_destination_file.read()
                if existing_file_content == source_file_content:
                    return
        shutil.copy2(source_file_path, destination_file_path)
        self.copied_files += 1

    def convert_directory(self, source_directory: Path, destination_directory: Path):
        if self.options.root_dir and self.options.root_dir != Path() and source_directory != self.options.root_dir:
            self.add_filesystem_directory(self.options.root_dir)
            self.convert_directory_impl(self.options.root_dir, destination_directory, source_directory.relative_to(self.options.root_dir), FileOptions())
        else:
            self.add_filesystem_directory(source_directory)
            self.convert_directory_impl(source_directory, destination_directory, Path(), FileOptions())

    def add_filesystem_directory(self, directory: Path):
        print('adding filesystem directory', directory)
        self.resolver.files_map.add_filesystem_directory(directory)

    def convert_directory_impl(self, source_directory: Path, destination_directory: Path, subdir: Path, file_options: FileOptions):
        source_directory_w_subdir = source_directory.joinpath(subdir or '')
        destination_directory_w_subdir = destination_directory.joinpath(subdir or '')
        destination_directory_w_subdir.mkdir(parents=True, exist_ok=True)
        for filepath in sorted(source_directory_w_subdir.iterdir(),
                               key = lambda filepath: self.interface_then_impl_key(filepath)):
            filename = filepath.relative_to(source_directory)
            if any_pattern_maches(self.options.skip_patterns, PurePosixPath(filename)):
                print(f'skipping "{filename}"')
                continue
            next_file_options = self.make_next_file_options(file_options, filename)
            if filepath.is_file():
                self.convert_or_copy_file(source_directory, destination_directory, filename, next_file_options)
            if filepath.is_dir():
                self.convert_directory_impl(source_directory, destination_directory, filename, next_file_options)

    def interface_then_impl_key(self, file_path: Path):
        content_type = self.resolver.get_source_content_type(self.action, file_path)
        if content_type in interface_content_types:
            return 0
        return 1


    def make_next_file_options(self, file_options: FileOptions, filename: Path):
        next_file_options = copy.copy(file_options)
        if not file_options.convert_as_compat:
            convert_as_compat = any_pattern_maches(self.options.compat_patterns, PurePosixPath(filename))
            if convert_as_compat:
                next_file_options.convert_as_compat = convert_as_compat
        return next_file_options

def any_pattern_maches(patterns: list[str], filename: PurePosixPath) -> bool:
    for skip_pattern in patterns:
        if filename.match(skip_pattern):
            return True
    return False

def convert_file_content(action: ConvertAction, content: str, filename: str) -> str:
    converter = Converter(action)
    file_content_list: FileContentList = converter.convert_file_content(content, filename, FileOptions())
    return file_content_list[0].content

def convert_directory(action: ConvertAction, source_directory: Path, destination_directory: Path, subdir: str | None = None):
    converter = Converter(action)
    return converter.convert_directory(source_directory, destination_directory)
