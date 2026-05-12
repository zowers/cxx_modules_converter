from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from .options import ContentType, Options
from .resolvers import FilesResolver
from .file_processing import FileContent, StrList

if TYPE_CHECKING:
    from .module_base_builder import ModuleBaseBuilder


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


class FileProcessingState:
    def __init__(self):
        self.module_staging: StrList = [] # staging area for next module entry
        self.flushed_module_preprocessor_nesting_count: int = 0 # count of opened preprocessor #if statements flushed to module content
        self.global_module_fragment_staging: StrList = [] # staging area for next global_module_fragment entry
        self.preprocessor_nesting_count: int = 0 # count of opened preprocessor #if statements
        self.global_module_fragment_includes_count: int = 0 # count of #include <> statements
        self.flushed_global_module_fragment_includes_count: int = 0 # count of #include <> statements flushed to global module content
        self.module_staging_last_unnested_index: int = 0 # last index in module staging without opened preprocessor #if statements

    def add_module_staging(self, line: str, nesting_advance: int):
        if (self.preprocessor_nesting_count == 0 and nesting_advance == 0
            or self.preprocessor_nesting_count == 1 and nesting_advance == 1):
            self.module_staging_last_unnested_index = len(self.module_staging)
        self.module_staging.append(line)
        if (self.preprocessor_nesting_count == 0 and nesting_advance == -1):
            self.module_staging_last_unnested_index = len(self.module_staging)

    def add_global_module_fragment_staging(self, builder: 'ModuleBaseBuilder', line: str, nesting_advance: int):
        self.global_module_fragment_staging.append(line)
        self.flush_global_module_fragment(builder)

    def flush_module_staging(self, builder: 'ModuleBaseBuilder', last_unnested_inserter: Callable[[], None] | None = None):
        builder.set_module_purview_start()
        if self.flushed_global_module_fragment_includes_count == 0 or self.flushed_module_preprocessor_nesting_count != 0:
            for i in range(len(self.module_staging)):
                if last_unnested_inserter and i == self.module_staging_last_unnested_index:
                    last_unnested_inserter()
                line = self.module_staging[i]
                builder.module_content.append(line)
            if last_unnested_inserter and self.module_staging_last_unnested_index == len(self.module_staging):
                last_unnested_inserter()
        self.module_staging = []
        self.flushed_module_preprocessor_nesting_count = self.preprocessor_nesting_count
        self.flushed_global_module_fragment_includes_count = 0
        self.module_staging_last_unnested_index = 0

    def flush_global_module_fragment(self, builder: 'ModuleBaseBuilder'):
        self.flushed_global_module_fragment_includes_count = 0
        if self.preprocessor_nesting_count != 0:
            return
        if self.global_module_fragment_includes_count == 0 and not builder.convert_as_compat_header():
            return
        builder.set_global_module_fragment_start()
        for line in self.global_module_fragment_staging:
            builder.global_module_fragment.append(line)
        self.global_module_fragment_staging = []
        self.flushed_global_module_fragment_includes_count = self.global_module_fragment_includes_count
        self.global_module_fragment_includes_count = 0
        self.flush_module_staging(builder)

    def add_staging(self, builder: 'ModuleBaseBuilder', line: str, nesting_advance: int):
        self.preprocessor_nesting_count += nesting_advance
        self.add_module_staging(line, nesting_advance)
        self.add_global_module_fragment_staging(builder, line, nesting_advance)
