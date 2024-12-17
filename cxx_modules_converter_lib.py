import enum
import os
import os.path
from pathlib import Path, PurePosixPath
import re
import shutil
from typing import TypeAlias

class ConvertAction(enum.StrEnum):
    MODULES = 'modules'
    HEADERS = 'headers'

AlwaysIncludeNames: TypeAlias = set[str]
always_include_names = {
    'cassert',
    'assert.h',
}

class Options:
    def __init__(self):
        self.always_include_names = always_include_names
        self.root_dir: Path = ''
        self.search_path = []

def filename_to_module_name(filename: str) -> str:
    parts = os.path.splitext(filename)
    result = parts[0].replace('/', '.').replace('\\', '.')
    return result

class FileEntryType(enum.IntEnum):
    FILE = 1
    DIR = 2

FilesMapDict: TypeAlias = dict[str, dict]

class FilesMap:
    def __init__(self):
        self.value: FilesMapDict = {}

    def find(self, path: Path) -> FilesMapDict | FileEntryType | None:
        value = self.value
        for part in path.parts:
            if not value:
                break
            value = value.get(part, None)
        return value

    def add_filesystem_directory(self, path: Path):
        for (root, dirs, files) in path.walk():
            relative_root = root.relative_to(path)
            if relative_root == Path(''):
                root_node = self.value
            else:
                parent_node = self.find(relative_root.parent)
                parent_node[relative_root.name] = {}
                root_node = parent_node[relative_root.name]

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
    
    def resolve_in_search_path(self, current_dir: Path, current_filename: Path, include_filename: str) -> PurePosixPath:
        include_path = PurePosixPath(include_filename)
        # search relative to root
        if self.files_map.find(include_path):
            return include_path
        # search relative to current_dir
        full_path = current_dir.joinpath(include_path)
        if self.files_map.find(full_path):
            return full_path
        # search in search_path
        for search_path_item in self.options.search_path:
            path = PurePosixPath(search_path_item).joinpath(include_path)
            if self.files_map.find(path):
                return path
        print(f'warning: file not found: "{include_filename}" referenced from "{current_filename}"')
        return include_path

class ModuleFilesResolver:
    def __init__(self, parent_resolver: FilesResolver, options: Options):
        self.parent_resolver: FilesResolver = parent_resolver
        self.options: Options = options
        self.module_filename: Path = Path()
        self.module_dir: Path = Path()

    def set_filename(self, filename: Path):
        self.module_filename = filename
        self.module_dir = self.module_filename.parent

    def resolve_include(self, include_filename: str) -> str:
        result = self.parent_resolver.resolve_in_search_path(self.module_dir, self.module_filename, include_filename)
        return result

    def resolve_include_to_module_name(self, include_filename: str) -> str:
        resolved_include_filename = self.parent_resolver.resolve_in_search_path(self.module_dir, self.module_filename, include_filename)
        result = self.convert_filename_to_module_name(resolved_include_filename)
        return result

    def convert_filename_to_module_name(self, filename: str) -> str:

        module_name = filename_to_module_name(filename)
        return module_name

class ContentType(enum.IntEnum):
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

def get_source_content_type(action: ConvertAction, filename: str) -> ContentType:
    parts = os.path.splitext(filename)
    extension = parts[-1]
    action_ext_types = source_ext_types[action]
    return action_ext_types.get(extension, ContentType.OTHER)

def get_converted_content_type(content_type: ContentType) -> ContentType:
    return content_type_to_converted[content_type]

def convert_filename_to_content_type(filename: str, content_type: ContentType):
    parts = os.path.splitext(filename)
    new_extension = content_type_to_ext[content_type]
    new_filename = parts[0] + new_extension
    return new_filename

StrList: TypeAlias = list[str]
new_line = '\n'

class LineCompatibility(enum.IntEnum):
    GLOBAL_MODULE_FRAGMENT = 1
    MODULE_CONTENT = 2
    ANY = 3

class Line:
    def __init__(self, text: str, line_compatibility: LineCompatibility):
        self.text: str = text
        self.line_compatibility: str = line_compatibility

LineList: TypeAlias = list[Line]

# regex: spaces only
spaces_rx = re.compile(r'''^\s*$''')
# regex: #include <system_header>
preprocessor_include_system_rx = re.compile(r'''^(\s*)#(\s*)include\s*<(.+)>(.*)$''')
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

class ModuleBaseBuilder:
    module_purview_start_prefix: str = ''   # 'module' or 'export module' - overriden in implementation classes

    def __init__(self, options: Options, parent_resolver: FilesResolver):
        self.options: Options = options
        self.parent_resolver: FilesResolver = parent_resolver
        self.resolver: ModuleFilesResolver = ModuleFilesResolver(self.parent_resolver, self.options)
        self.module_name: str = ''                   # name of the module
        self.file_copyright: StrList = []            # // File copyright
        self.global_module_fragment_start: str = ''  # module;
        self.global_module_fragment: StrList = []    # header includes
        self.module_purview_start: str = ''          # export module <name>; // Start of module purview.
        # self.module_imports: StrList = []
        # self.module_purview_special_headers: StrList = [] # // Configuration, export, etc.
        self.module_content: StrList = []

        self.module_staging: StrList = [] # staging area for next module entry
        self.flushed_module_preprocessor_nesting_count: int = 0 # count of opened preprocessor #if statements flushed to module content
        self.global_module_fragment_staging: StrList = [] # staging area for next global_module_fragment entry
        self.preprocessor_nesting_count: int = 0 # count of opened preprocessor #if statements
        self.global_module_fragment_includes_count: int = 0 # count of #include <> statements
        self.flushed_global_module_fragment_includes_count: int = 0 # count of #include <> statements flushed to global module content

    def set_filename(self, filename: Path):
        self.resolver.set_filename(filename)
        self.set_module_name(self.resolver.convert_filename_to_module_name(filename))

    def set_module_name(self, name):
        assert(not self.module_name)
        self.module_name = name

    def set_global_module_fragment_start(self):
        assert(not self.global_module_fragment_start)
        self.global_module_fragment_start = 'module;'

    def set_module_purview_start(self):
        assert(not self.module_purview_start)
        assert(self.module_purview_start_prefix)
        assert(self.module_name)
        self.module_purview_start = f'{self.module_purview_start_prefix} {self.module_name};'

    def add_file_copyright(self, line):
        self.file_copyright.append(line)

    def _flush_global_module_fragment(self):
        self.flushed_global_module_fragment_includes_count = 0
        if self.preprocessor_nesting_count != 0:
            return
        if self.global_module_fragment_includes_count == 0:
            return
        if not self.global_module_fragment_start:
            self.set_global_module_fragment_start()
        for line in self.global_module_fragment_staging:
            self.global_module_fragment.append(line)
        self.global_module_fragment_staging = []
        self.flushed_global_module_fragment_includes_count = self.global_module_fragment_includes_count
        self.global_module_fragment_includes_count = 0
        self._flush_module_staging()

    def add_global_module_fragment(self, line):
        self.global_module_fragment_includes_count += 1
        self._add_global_module_fragment_staging(line, 0)
        self._flush_global_module_fragment()

    def add_staging(self, line: str, nesting_advance: int):
        self.preprocessor_nesting_count += nesting_advance
        self._add_module_staging(line, nesting_advance)
        self._add_global_module_fragment_staging(line, nesting_advance)

    def _add_global_module_fragment_staging(self, line: str, nesting_advance: int):
        self.global_module_fragment_staging.append(line)
        self._flush_global_module_fragment()

    def add_module_purview_special_headers(self, line):
        if not self.module_purview_start:
            self.set_module_purview_start()
        self.module_purview_special_headers.append(line)

    def add_module_content(self, line):
        self._flush_module_staging()
        if not self.module_purview_start:
            self.set_module_purview_start()
        self.module_content.append(line)

    def _add_module_staging(self, line: str, nesting_advance: int):
        self.module_staging.append(line)

    def _flush_module_staging(self):
        if not self.module_purview_start:
            self.set_module_purview_start()
        if self.flushed_global_module_fragment_includes_count == 0 or self.flushed_module_preprocessor_nesting_count != 0:
            for line in self.module_staging:
                self.module_content.append(line)
        self.module_staging = []
        self.flushed_module_preprocessor_nesting_count = self.preprocessor_nesting_count
        self.flushed_global_module_fragment_includes_count = 0

    def add_module_import_from_include(self, line: str, match: re.Match = None):
        if not self.module_purview_start:
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

        if line_include_filename in self.options.always_include_names:
            self.add_module_content(line)
            return
        
        line_module_name = self.resolver.resolve_include_to_module_name(line_include_filename)
        if line_module_name == self.module_name:
            return None
        import_line = f'{line_space1}{line_space2}import {line_module_name};{line_tail}'
        self.add_module_content(import_line)
    
    def build_result(self):
        assert(bool(self.global_module_fragment_start) == bool(self.global_module_fragment))
        if self.flushed_module_preprocessor_nesting_count != 0:
            self._flush_module_staging()
        if not self.module_purview_start:
            self.set_module_purview_start()
        parts = [
            new_line.join(self.file_copyright),
            self.global_module_fragment_start,
            new_line.join(self.global_module_fragment),
            self.module_purview_start,
            # new_line.join(self.module_imports),
            # new_line.join(self.module_purview_special_headers),
            new_line.join(self.module_content),
            ]
        parts = filter(None, parts) # remove empty parts
        return new_line.join(parts) + new_line

class ModuleInterfaceUnitBuilder(ModuleBaseBuilder):
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

class ModuleImplUnitBuilder(ModuleBaseBuilder):
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

class HeaderScanState(enum.IntEnum):
    START = enum.auto()
    FILE_COMMENT = enum.auto()
    MAIN = enum.auto()

class Matcher:
    def __init__(self):
        self.rx: re.Pattern = None
        self.matched: re.Match = None
    def match(self, rx: re.Pattern, s) -> re.Match:
        self.rx = rx
        self.matched = self.rx.match(s)
        return self.matched

class Converter:

    def __init__(self, action: ConvertAction):
        self.action = action
        self.options = Options()
        self.resolver = FilesResolver(self.options)
    
    def convert_file_content_to_module(self, content: str, filename: str, content_type: ContentType) -> str:
        if content_type in {ContentType.MODULE_INTERFACE, ContentType.MODULE_IMPL}:
            return content
        content_lines = content.splitlines()

        builder = self.make_builder_to_module(filename, content_type)

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
            match scanState:
                case HeaderScanState.START:
                    if is_comment():
                        scanState = HeaderScanState.FILE_COMMENT
                        continue
                    else:
                        scanState = HeaderScanState.MAIN
                        continue
                case HeaderScanState.FILE_COMMENT:
                    line2 = line.strip()[0:2] 
                    if (is_comment()
                        or line2[0] == '*'
                        ):
                        builder.add_file_copyright(line)
                    else:
                        scanState = HeaderScanState.MAIN
                        continue
                case HeaderScanState.MAIN:
                    m = Matcher()
                    if m.match(preprocessor_include_system_rx, line):
                        builder.add_global_module_fragment(line)
                    elif m.match(preprocessor_include_local_rx, line):
                        builder.add_module_import_from_include(line, m.matched)
                    elif (m.match(preprocessor_line_comment_rx, line)
                          or m.match(preprocessor_other_rx, line)
                          or m.match(spaces_rx, line)):
                        builder.add_staging(line, 0)
                    elif (m.match(preprocessor_define_rx, line)):
                        builder.add_staging(line, 0)
                    elif m.match(preprocessor_if_rx, line):
                        builder.add_staging(line, 1)
                    elif m.match(preprocessor_endif_rx, line):
                        builder.add_staging(line, -1)
                    else:
                        builder.add_module_content(line)
            i += 1

        result_content = builder.build_result()
        
        return result_content
    
    def make_builder_to_module(self, filename: str, content_type: ContentType) -> ModuleBaseBuilder:
        match content_type:
            case ContentType.HEADER:
                builder = ModuleInterfaceUnitBuilder(self.options, self.resolver)
            case ContentType.CXX:
                builder = ModuleImplUnitBuilder(self.options, self.resolver)
            case _:
                raise RuntimeError(f'Unknown content type {content_type}')
        
        builder.set_filename(PurePosixPath(filename))
        return builder

    def convert_file_content_to_headers(self, content: str, filename: str, content_type: ContentType) -> str:
        if content_type in {ContentType.HEADER, ContentType.CXX}:
            return content
        return content

    def convert_file_content(self, content: str, filename: str) -> str:
        action = self.action
        content_type = get_source_content_type(action, filename)
        match action:
            case ConvertAction.MODULES:
                return self.convert_file_content_to_module(content, filename, content_type)
            case ConvertAction.HEADERS:
                return self.convert_file_content_to_headers(content, filename, content_type)
            case _:
                raise RuntimeError(f'Unknown action: "{action}"')

    def convert_file(self, source_directory: Path, destination_directory: Path, filename: str) -> tuple[str, ContentType]:
        with open(source_directory.joinpath(filename)) as source_file:
            source_content = source_file.read()
        converted_content = self.convert_file_content(source_content, filename)
        content_type = get_source_content_type(self.action, filename)
        converted_content_type = get_converted_content_type(content_type)
        converted_filename = convert_filename_to_content_type(filename, converted_content_type)
        with open(destination_directory.joinpath(converted_filename), 'w') as destination_file:
            destination_file.write(converted_content)
        return (converted_filename, converted_content_type)

    def convert_or_copy_file(self, source_directory: Path, destination_directory: Path, filename: str):
        content_type = get_source_content_type(self.action, filename)
        if content_type == ContentType.OTHER:
            shutil.copy2(source_directory.joinpath(filename), destination_directory.joinpath(filename))
        else:
            print('converting', filename)
            (converted_filename, content_type) = self.convert_file(source_directory, destination_directory, filename)
            print('converted ', converted_filename, '\t', content_type_to_name[content_type])

    def convert_directory(self, source_directory: Path, destination_directory: Path):
        if self.options.root_dir and source_directory != self.options.root_dir:
            self.add_filesystem_directory(self.options.root_dir)
            self.convert_directory_impl(self.options.root_dir, destination_directory, source_directory.relative_to(self.options.root_dir))
        else:
            self.add_filesystem_directory(source_directory)
            self.convert_directory_impl(source_directory, destination_directory)

    def add_filesystem_directory(self, directory: Path):
        print('adding filesystem directory', directory)
        self.resolver.files_map.add_filesystem_directory(directory)

    def convert_directory_impl(self, source_directory: Path, destination_directory: Path, subdir: str = None):
        source_directory_w_subdir = source_directory.joinpath(subdir or '')
        destination_directory_w_subdir = destination_directory.joinpath(subdir or '')
        destination_directory_w_subdir.mkdir(parents=True, exist_ok=True)
        for filepath in source_directory_w_subdir.iterdir():
            filename = filepath.relative_to(source_directory)
            if filepath.is_file():
                self.convert_or_copy_file(source_directory, destination_directory, filename)
            if filepath.is_dir():
                self.convert_directory_impl(source_directory, destination_directory, filename)

def convert_file_content(action: ConvertAction, content: str, filename: str) -> str:
    converter = Converter(action)
    return converter.convert_file_content(content, filename)

def convert_directory(action: ConvertAction, source_directory: Path, destination_directory: Path, subdir: str = None):
    converter = Converter(action)
    return converter.convert_directory(source_directory, destination_directory)
