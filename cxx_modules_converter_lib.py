from __future__ import annotations

import copy
import enum
import os
import os.path
from pathlib import Path, PurePosixPath
import re
import shutil

from typing import Any
try:
    # make pylance happy
    from typing import TypeAlias as TypeAlias2
except ImportError:
    TypeAlias2 = Any
TypeAlias = TypeAlias2
class ConvertAction(enum.Enum):
    MODULES = 'modules'
    HEADERS = 'headers'

AlwaysIncludeNames: TypeAlias = set[str]
always_include_names = [
    'cassert',
    'assert.h',
]

COMPAT_MACRO_DEFAULT: str = "CXX_COMPAT_HEADER"

class Options:
    def __init__(self):
        self.always_include_names = copy.copy(always_include_names)
        self.root_dir: Path = Path()
        self.root_dir_module_name: str = ''
        self.search_path: list[str] = []
        self.skip_patterns: list[str] = []
        self.compat_patterns: list[str] = []
        self.compat_macro: str = COMPAT_MACRO_DEFAULT

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

class FilesResolver:
    def __init__(self, options: Options):
        self.options: Options = options
        self.files_map = FilesMap()
    
    def resolve_in_search_path(self, current_dir: Path, current_filename: str|Path, include_filename: str) -> PurePosixPath:
        include_path = PurePosixPath(include_filename)
        # search relative to root
        if self.files_map.find(include_path):
            return include_path
        # search relative to current_dir
        full_path = PurePosixPath(current_dir.joinpath(include_path))
        if self.files_map.find(full_path):
            return full_path
        # search in search_path
        for search_path_item in self.options.search_path:
            path = PurePosixPath(search_path_item).joinpath(include_path)
            if self.files_map.find(path):
                return path
        print(f'warning: file not found: "{include_filename}" referenced from "{current_filename}"')
        return include_path

    def convert_filename_to_module_name(self, filename: PurePosixPath) -> str:
        full_name = filename
        if self.options.root_dir_module_name and self.files_map.find(filename):
            full_name = PurePosixPath(self.options.root_dir_module_name).joinpath(filename)
        module_name = filename_to_module_name(full_name)
        return module_name

class ModuleFilesResolver:
    def __init__(self, parent_resolver: FilesResolver, options: Options):
        self.parent_resolver: FilesResolver = parent_resolver
        self.options: Options = options
        self.module_filename: Path = Path()
        self.module_dir: Path = Path()

    def set_filename(self, filename: Path):
        self.module_filename = filename
        self.module_dir = self.module_filename.parent

    def resolve_include(self, include_filename: str) -> PurePosixPath:
        result = self.parent_resolver.resolve_in_search_path(self.module_dir, self.module_filename, include_filename)
        return result

    def resolve_include_to_module_name(self, include_filename: str) -> str:
        resolved_include_filename = self.parent_resolver.resolve_in_search_path(self.module_dir, self.module_filename, include_filename)
        result = self.parent_resolver.convert_filename_to_module_name(resolved_include_filename)
        return result

class ContentType(enum.Enum):
    HEADER = 1
    CXX = 2
    MODULE_INTERFACE = 3
    MODULE_IMPL = 4
    OTHER = 5

ContentTypeToExt: TypeAlias = dict[ContentType, str]
content_type_to_ext: ContentTypeToExt = {
    ContentType.HEADER: '.h',
    ContentType.CXX: '.cpp',
    ContentType.MODULE_INTERFACE: '.cppm',
    ContentType.MODULE_IMPL: '.cpp',
}

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

ExtTypes: TypeAlias = dict[str, ContentType]
modules_ext_types: ExtTypes = {
    '.h': ContentType.HEADER,
    '.cpp': ContentType.CXX,
}
headers_ext_types: ExtTypes = {
    '.cppm': ContentType.MODULE_INTERFACE,
    '.cpp': ContentType.MODULE_IMPL,
}

ActionExtTypes: TypeAlias = dict[ConvertAction, ExtTypes]
source_ext_types: ActionExtTypes = {
    ConvertAction.MODULES: modules_ext_types,
    ConvertAction.HEADERS: headers_ext_types,
}
destination_ext_types: ActionExtTypes = {
    ConvertAction.HEADERS: modules_ext_types,
    ConvertAction.MODULES: headers_ext_types,
}

def get_source_content_type(action: ConvertAction, filename: Path) -> ContentType:
    parts = os.path.splitext(filename)
    extension = parts[-1]
    action_ext_types = source_ext_types[action]
    return action_ext_types.get(extension, ContentType.OTHER)

def get_converted_content_type(content_type: ContentType) -> ContentType:
    return content_type_to_converted[content_type]

def convert_filename_to_content_type(filename: Path, content_type: ContentType):
    parts = os.path.splitext(filename)
    new_extension = content_type_to_ext[content_type]
    new_filename = parts[0] + new_extension
    return new_filename

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
# regex: #include <system_header>
preprocessor_include_system_rx = re.compile(r'''^(\s*)#(\s*)(include|import)\s*<(.+)>(.*)$''')
# regex: #include "local_header.h"
preprocessor_include_local_rx = re.compile(r'''^(\s*)#(\s*)include\s*"(.+)"(.*)$''')
# regex: line comment
preprocessor_line_comment_rx = re.compile(r'''^\s*//.*$''')
# regex: block comment start
preprocessor_block_comment_rx = re.compile(r'''^\s*/\*.*$''')
# regex: block comment end
preprocessor_block_comment_rx = re.compile(r'''^\s*\*/.*$''')
# regex: #if
preprocessor_if_rx = re.compile(r'''^\s*#\s*if.*$''')
# regex: #endif
preprocessor_endif_rx = re.compile(r'''^\s*#\s*endif.*$''')
# regex: #define
preprocessor_define_rx = re.compile(r'''^\s*#\s*define.*$''')
# regex: #error
# regex: #elif
# regex: #else
# regex: #pragma
# regex: #warning
preprocessor_other_rx = re.compile(r'''^\s*#\s*(error|elif|else|pragma|warning).*$''')

class FileBaseBuilder:
    content_type: ContentType = ContentType.OTHER

    def __init__(self, options: Options):
        self.options: Options = options
        self.source_filename: Path = Path('')

    def set_source_filename(self, source_filename: Path):
        self.source_filename = source_filename

    def converted_filename(self) -> str:
        return convert_filename_to_content_type(self.source_filename, self.content_type)

    def build_result(self) -> str:
        raise NotImplementedError('build_result')

    def build_file_content(self) -> FileContent:
        content = self.build_result()
        return FileContent(self.converted_filename(), self.content_type, content)

class ModuleBaseBuilder(FileBaseBuilder):
    module_purview_start_prefix: str = ''   # 'module' or 'export module' - overriden in implementation classes
    content_type: ContentType = ContentType.OTHER

    def __init__(self, options: Options, parent_resolver: FilesResolver, file_options: FileOptions):
        super().__init__(options)
        self.parent_resolver: FilesResolver = parent_resolver
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

    def set_source_filename(self, source_filename: Path):
        super().set_source_filename(source_filename)
        self.resolver.set_filename(source_filename)
        self.set_module_name(self.parent_resolver.convert_filename_to_module_name(PurePosixPath(source_filename)))

    def set_module_name(self, name: str):
        assert(not self.module_name)
        self.module_name = name

    def set_is_actually_module(self) -> None:
        raise NotImplementedError('set_is_actually_module')

    def get_is_actually_module(self) -> bool:
        raise NotImplementedError('get_is_actually_module')

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
        if self.global_module_fragment_includes_count == 0:
            return
        self.set_global_module_fragment_start()
        for line in self.global_module_fragment_staging:
            self.global_module_fragment.append(line)
        self.global_module_fragment_staging = []
        self.flushed_global_module_fragment_includes_count = self.global_module_fragment_includes_count
        self.global_module_fragment_includes_count = 0
        self._flush_module_staging()

    def handle_system_include(self, line: str):
        self.add_global_module_fragment(line)

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
        self._flush_module_staging()
        self._set_main_module_content_start()
        self.add_module_content(line)

    def _set_main_module_content_start(self):
        if self.main_module_content_index is None:
            self.main_module_content_index = len(self.module_content)

    def _mark_module_interface_unit_export(self):
        if self.main_module_content_index is None:
            return
        module_start = []
        module_end = []
        if self.content_type == ContentType.MODULE_INTERFACE:
            # wrap module interface unit in export {}
            module_start = [
                '''export {'''
            ]
            module_end = [
                '''} // export'''
            ]
        if self.file_options.convert_as_compat:
            # wrap module content in extern "C++" {}
            module_start = [
                '''extern "C++" {'''
                ] + module_start
            module_end = module_end + [
                '''} // extern "C++"'''
                ]
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
        self.module_staging.append(line)

    def _flush_module_staging(self):
        self.set_module_purview_start()
        if self.flushed_global_module_fragment_includes_count == 0 or self.flushed_module_preprocessor_nesting_count != 0:
            for line in self.module_staging:
                self.module_content.append(line)
        self.module_staging = []
        self.flushed_module_preprocessor_nesting_count = self.preprocessor_nesting_count
        self.flushed_global_module_fragment_includes_count = 0

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

    def handle_local_include(self, line: str, match: re.Match[str] | None = None):
        if self.convert_as_compat_header():
            self.add_compat_include(line)
        self.add_module_import_from_include(line, match)

    def add_module_import_from_include(self, line: str, match: re.Match[str] | None = None):
        self.set_module_purview_start()
        if not match:
            match = preprocessor_include_local_rx.match(line)
        if not match:
            print('warning: preprocessor_include_local_rx not matched')
            self.add_module_content(line)
            return

        line_space1 = match[1]
        line_space2 = match[1]
        line_include_filename = match[3]
        line_tail = match[4]

        if any_pattern_maches(self.options.always_include_names, PurePosixPath(line_include_filename)):
            self.add_module_content(line)
            return
        
        line_module_name = self.resolver.resolve_include_to_module_name(line_include_filename)
        if line_module_name == self.module_name:
            self.set_is_actually_module()
            self.set_module_purview_start()
            return
        import_line = f'{line_space1}{line_space2}import {line_module_name};{line_tail}'
        import_lines = self.wrap_in_compat_macro_if_compat_header([import_line])
        for import_line in import_lines:
            self.add_module_content(import_line)

    def add_compat_include(self, line: str):
        self.set_global_module_fragment_start()
        self.global_module_fragment_compat_includes.append(line)

    def build_result(self):
        if self.global_module_fragment or self.global_module_fragment_compat_includes:
            assert(bool(self.global_module_fragment_start) == self.get_is_actually_module())
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

    def set_is_actually_module(self) -> None:
        self._is_actually_module = True

    def get_is_actually_module(self) -> bool:
        return self._is_actually_module


class CompatHeaderBuilder(FileBaseBuilder):
    content_type = ContentType.HEADER
    def __init__(self, options: Options, module_builder: ModuleBaseBuilder):
        super().__init__(options)
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
            f'''#endif''',
            f'''#include "{relative_module_interface_unit_filename}"''',
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
                    if m.match(preprocessor_include_system_rx, line):
                        builder.handle_system_include(line)
                    elif m.match(preprocessor_include_local_rx, line):
                        builder.handle_local_include(line, m.matched)
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
        content_type = get_source_content_type(action, filename)
        if action == ConvertAction.MODULES:
            return self.convert_file_content_to_module(content, filename, content_type, file_options)
        elif action == ConvertAction.HEADERS:
            return self.convert_file_content_to_headers(content, filename, content_type, file_options)
        else:
            raise RuntimeError(f'Unknown action: "{action}"')

    def convert_file(self, source_directory: Path, destination_directory: Path, filename: Path, file_options: FileOptions) -> FileContentList:
        with open(source_directory.joinpath(filename)) as source_file:
            source_content = source_file.read()
        converted_files = self.convert_file_content(source_content, filename, file_options)
        for converted_file in converted_files:
            converted_content = converted_file.content
            converted_filename = converted_file.filename
            with open(destination_directory.joinpath(converted_filename), 'w') as destination_file:
                destination_file.write(converted_content)
        return converted_files

    def convert_or_copy_file(self, source_directory: Path, destination_directory: Path, filename: Path, file_options: FileOptions):
        content_type = get_source_content_type(self.action, filename)
        if content_type == ContentType.OTHER or any_pattern_maches(self.options.always_include_names, PurePosixPath(filename)):
            shutil.copy2(source_directory.joinpath(filename), destination_directory.joinpath(filename))
        else:
            print('converting', filename)
            converted_files = self.convert_file(source_directory, destination_directory, filename, file_options)
            for converted_file in converted_files:
                print('converted ', converted_file.filename, '\t', converted_file.content_type)

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
        for filepath in source_directory_w_subdir.iterdir():
            filename = filepath.relative_to(source_directory)
            if any_pattern_maches(self.options.skip_patterns, PurePosixPath(filename)):
                print(f'skipping "{filename}"')
                continue
            next_file_options = self.make_next_file_options(file_options, filename)
            if filepath.is_file():
                self.convert_or_copy_file(source_directory, destination_directory, filename, next_file_options)
            if filepath.is_dir():
                self.convert_directory_impl(source_directory, destination_directory, filename, next_file_options)

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
            print(f'skipping "f{filename}"')
            return True
    return False

def convert_file_content(action: ConvertAction, content: str, filename: str) -> str:
    converter = Converter(action)
    file_content_list: FileContentList = converter.convert_file_content(content, filename, FileOptions())
    return file_content_list[0].content

def convert_directory(action: ConvertAction, source_directory: Path, destination_directory: Path, subdir: str | None = None):
    converter = Converter(action)
    return converter.convert_directory(source_directory, destination_directory)
