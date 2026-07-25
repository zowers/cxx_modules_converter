from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from .exceptions import ConversionError
from .file_base_builder import FileBaseBuilder
from .file_processing import (
    ModuleLine,
    ModuleLineKind,
    ParsedModuleFile,
    get_converted_content_type,
)
from .options import ContentType, Options
from .resolvers import FilesResolver


class HeaderBuilder(FileBaseBuilder):
    """Build a traditional header or source from a parsed module file."""

    def __init__(
        self,
        options: Options,
        parent_resolver: FilesResolver,
        source_content_type: ContentType,
        parsed_file: ParsedModuleFile,
        header_filenames_by_module: Mapping[str, Path],
    ):
        super().__init__(options, parent_resolver)
        if source_content_type not in {
            ContentType.MODULE_INTERFACE,
            ContentType.MODULE_IMPL,
        }:
            raise ConversionError(f'HeaderBuilder cannot convert {source_content_type}')
        self.source_content_type = source_content_type
        self.content_type = get_converted_content_type(source_content_type)
        self.parsed_file = parsed_file
        self.header_filenames_by_module = header_filenames_by_module

    def build_result(self) -> str:
        converted_filename = Path(self.converted_filename())
        converted_lines: list[str] = []
        for line in self.parsed_file.lines:
            match line.kind:
                case ModuleLineKind.CONTENT:
                    converted_lines.append(line.text + line.line_ending)
                case ModuleLineKind.GLOBAL_MODULE_FRAGMENT:
                    self._append_removed_declaration_comment(converted_lines, line)
                case ModuleLineKind.MODULE_DECLARATION:
                    if self.source_content_type == ContentType.MODULE_IMPL:
                        converted_lines.append(
                            self._make_module_include(line, converted_filename)
                        )
                    else:
                        self._append_removed_declaration_comment(converted_lines, line)
                case ModuleLineKind.IMPORT:
                    converted_lines.append(
                        self._make_import_include(line, converted_filename)
                    )
                case ModuleLineKind.EXPORT_DECLARATION:
                    converted_lines.append(line.indent + line.text + line.line_ending)
                case (
                    ModuleLineKind.EXPORT_BLOCK_START | ModuleLineKind.EXPORT_BLOCK_END
                ):
                    pass

        result = ''.join(converted_lines)
        if self.source_content_type == ContentType.MODULE_INTERFACE:
            pragma_once = f'#pragma once{self.parsed_file.line_ending}'
            if not result.startswith('#pragma once'):
                result = pragma_once + result
        return result

    def _make_module_include(self, line: ModuleLine, converted_filename: Path) -> str:
        include_filename = self._resolve_module_header(
            line.name, converted_filename, line.line_number
        )
        return self._make_include_line(line, f'"{include_filename.as_posix()}"')

    def _make_import_include(self, line: ModuleLine, converted_filename: Path) -> str:
        if (line.name.startswith('<') and line.name.endswith('>')) or (
            line.name.startswith('"') and line.name.endswith('"')
        ):
            include_target = line.name
        else:
            include_filename = self._resolve_module_header(
                line.name, converted_filename, line.line_number
            )
            include_target = f'"{include_filename.as_posix()}"'
        return self._make_include_line(line, include_target)

    def _resolve_module_header(
        self, module_name: str, converted_filename: Path, line_number: int
    ) -> Path:
        resolved_name = module_name
        current_module = self.parsed_file.declared_module
        if module_name.startswith(':') and current_module:
            resolved_name = current_module.split(':', 1)[0] + module_name
        header_filename = self.header_filenames_by_module.get(resolved_name)
        if header_filename is None:
            raise ConversionError(
                f'Cannot resolve imported module "{module_name}" in '
                f'"{self.source_filename}" at line {line_number}'
            )
        relative_filename = os.path.relpath(
            header_filename, start=converted_filename.parent
        )
        return Path(relative_filename)

    @staticmethod
    def _make_include_line(line: ModuleLine, target: str) -> str:
        return f'{line.indent}#include {target}{line.suffix}{line.line_ending}'

    @staticmethod
    def _append_removed_declaration_comment(
        converted_lines: list[str], line: ModuleLine
    ) -> None:
        comment_index = line.suffix.find('//')
        if comment_index >= 0:
            converted_lines.append(line.suffix[comment_index:] + line.line_ending)
