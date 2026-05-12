from __future__ import annotations

import fnmatch
import logging
import os
import re
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from .options import (
    Options,
    FileOptions,
    ContentType,
    STAR_MODULE_EXPORT,
    always_include_names,
)
from .resolvers import FilesResolver, ModuleFilesResolver
from .file_base_builder import FileBaseBuilder, FileProcessingState
from .file_processing import (
    StrList,
    new_line,
    preprocessor_include_quote_rx,
    preprocessor_include_brackets_rx,
    preprocessor_pragma_once_rx,
    preprocessor_line_comment_rx,
    preprocessor_other_rx,
    preprocessor_define_rx,
    preprocessor_if_rx,
    preprocessor_endif_rx,
    spaces_rx,
)
from .exceptions import ConversionError

if TYPE_CHECKING:
    from .module_interface_builder import ModuleInterfaceUnitBuilder


def any_pattern_maches(patterns: list[str], filename: PurePosixPath) -> bool:
    for skip_pattern in patterns:
        if fnmatch.fnmatchcase(filename.as_posix(), skip_pattern):
            return True
    return False


class ModuleBaseBuilder(FileBaseBuilder):
    module_purview_start_prefix: str = ''   # 'module' or 'export module' - overriden in implementation classes
    content_type: ContentType = ContentType.OTHER

    def __init__(self, options: Options, parent_resolver: FilesResolver, file_options: FileOptions):
        super().__init__(options, parent_resolver)
        self.file_options: FileOptions = file_options
        self.resolver: ModuleFilesResolver = ModuleFilesResolver(self.parent_resolver, self.options)
        self.module_name: str = ''                   # name of the module
        self.file_copyright: StrList = []            # // File copyright
        self.module_dependencies: set[str] = set()   # dependencies for the module
        self.global_module_fragment_start: StrList = []  # module;
        self.global_module_fragment_compat_includes: StrList = []    # compat header includes
        self.global_module_fragment_compat_end: StrList = []    # compat header includes endif
        self.global_module_fragment: StrList = []    # header includes
        self.module_purview_start: StrList = []      # export module <name>; // Start of module purview.
        # self.module_imports: StrList = []
        # self.module_purview_special_headers: StrList = [] # // Configuration, export, etc.
        self.module_content: StrList = []
        self.main_module_content_index: int|None = None

        self.processing_state: FileProcessingState = FileProcessingState()

    def set_source_filename(self, source_filename: Path):
        super().set_source_filename(source_filename)
        self.resolver.set_filename(source_filename)
        pure_source_filename = PurePosixPath(source_filename)
        module_name = self.parent_resolver.make_defined_module_for_path(pure_source_filename)
        if not module_name:
            module_name = self.parent_resolver.convert_filename_to_module_name(pure_source_filename)
        if not module_name:
            raise ConversionError(f"Failed to determine module name for file {pure_source_filename}")
        self.set_module_name(module_name)

    def set_module_name(self, name: str):
        self.module_name = name
        self.resolver.set_module_name(name)

    def set_is_actually_module(self) -> None:
        if self.global_module_fragment:
            self.set_global_module_fragment_start()

    def get_is_actually_module(self) -> bool:
        raise NotImplementedError('get_is_actually_module')

    def get_module_interface_builder(self) -> 'ModuleInterfaceUnitBuilder | None':
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
        if not self.module_purview_start_prefix:
            raise ConversionError("module_purview_start_prefix is not set")
        if not self.module_name:
            raise ConversionError("module_name is not set")
        module_purview_start = f'''{self.module_purview_start_prefix} {self.module_name};'''
        self.module_purview_start = self.wrap_in_compat_macro_if_compat_header([
            module_purview_start
        ])

    def add_file_copyright(self, line: str):
        self.file_copyright.append(line)

    def get_module_dependencies(self) -> set[str]:
        return self.module_dependencies

    def add_global_module_fragment(self, line: str):
        self.processing_state.global_module_fragment_includes_count += 1
        self.processing_state.add_global_module_fragment_staging(self, line, 0)
        self.processing_state.flush_global_module_fragment(self)

    def handle_preprocessor(self, line: str, nesting_advance: int):
        self.processing_state.add_staging(self, line, nesting_advance)

    def add_module_purview_special_headers(self, line: str):
        self.set_module_purview_start()
        # self.module_purview_special_headers.append(line)

    def handle_main_content(self, line: str):
        self.processing_state.flush_module_staging(self, self._set_main_module_content_start)
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
        self.processing_state.flush_module_staging(self)
        self.set_module_purview_start()
        self.module_content.append(line)

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
        self.processing_state.add_module_staging(f'''// {line}''', 0)

    def add_module_import_from_include(self, line: str, match: re.Match[str] | None = None, is_quote: bool = False):
        self.set_module_purview_start()
        if not match:
            match = preprocessor_include_quote_rx.match(line)
        if not match:
            logging.warning('preprocessor_include_local_rx not matched')
            self.add_module_content(line)
            return

        line_space1 = match[1]
        line_space2 = match[1]
        line_include_filename = match[3]
        line_tail = match[4]

        resolved_include_filename = self.resolver.resolve_include(line_include_filename, is_quote)
        if resolved_include_filename is None and is_quote:
            self.add_global_module_fragment(line)
            return
        if any_pattern_maches(self.options.always_include_names, resolved_include_filename or PurePosixPath(line_include_filename)):
            self.add_global_module_fragment(line)
            return
        
        line_module_name = self.resolver.resolve_include_to_module_name(line_include_filename, is_quote, False)
        if line_module_name is None:
            self.add_global_module_fragment(line)
            return
        full_line_module_name = self.resolver.resolve_include_to_module_name(line_include_filename, is_quote, True)
        if full_line_module_name is not None:
            self.module_dependencies.add(full_line_module_name)
        if full_line_module_name == self.module_name:
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
        self.processing_state.flush_module_staging(self)
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
