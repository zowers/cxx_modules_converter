from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TypeAlias

from .exceptions import ConversionError
from .options import ContentType

# Type aliases
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

interface_content_types: set[ContentType] = {
    ContentType.MODULE_INTERFACE,
    ContentType.HEADER,
}


def get_converted_content_type(content_type: ContentType) -> ContentType:
    return content_type_to_converted[content_type]


class FileContent:
    def __init__(self, filename: str | Path, content_type: ContentType, content: str):
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


class LineCompatibility(enum.IntEnum):
    GLOBAL_MODULE_FRAGMENT = 1
    MODULE_CONTENT = 2
    ANY = 3


# Regular expressions for preprocessing
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
preprocessor_block_comment_end_rx = re.compile(r'''^\s*\*/.*$''')
# regex: #if
preprocessor_if_rx = re.compile(r'''^\s*#\s*if.*''')
# regex: #endif
preprocessor_endif_rx = re.compile(r'''^\s*#\s*endif.*$''')
# regex: #define
preprocessor_define_rx = re.compile(r'''^\s*#\s*define.*''')
# regex: #error, #elif, #else, #pragma, #warning
preprocessor_other_rx = re.compile(r'''^\s*#\s*(error|elif|else|pragma|warning).*''')
# regex: #pragma once
preprocessor_pragma_once_rx = re.compile(r'''^\s*#\s*pragma\s+once.*$''')


class HeaderScanState(enum.IntEnum):
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


class HeaderFileHandler(Protocol):
    def add_file_copyright(self, line: str): ...

    def handle_include_brackets(
        self, line: str, match: re.Match[str] | None = None
    ): ...

    def handle_include_quote(self, line: str, match: re.Match[str] | None = None): ...

    def handle_pragma_once(self, line: str): ...

    def handle_preprocessor(self, line: str, nesting_advance: int): ...

    def handle_main_content(self, line: str): ...


def process_header_content(content: str, handler: HeaderFileHandler) -> None:
    """Parse traditional C++ content and dispatch each line to a handler."""
    content_lines = content.splitlines()

    def is_comment(line: str) -> bool:
        line2 = line[0:2]
        line3 = line[0:3]
        return (
            not line
            or line2 == '//'
            or line2 == '/*'
            or line3 == '\ufeff//'
            or line3 == '\ufeff/*'
        )

    scan_state = HeaderScanState.START
    index = 0
    while index < len(content_lines):
        line = content_lines[index]
        while line and line[-1] == '\\' and index + 1 < len(content_lines):
            index += 1
            line += new_line + content_lines[index]

        match scan_state:
            case HeaderScanState.START:
                if is_comment(line):
                    scan_state = HeaderScanState.FILE_COMMENT
                    continue
                scan_state = HeaderScanState.MAIN
                continue
            case HeaderScanState.FILE_COMMENT:
                stripped_prefix = line.strip()[0:2]
                if is_comment(line) or stripped_prefix.startswith('*'):
                    handler.add_file_copyright(line)
                else:
                    scan_state = HeaderScanState.MAIN
                    continue
            case HeaderScanState.MAIN:
                matcher = Matcher()
                if matcher.match(preprocessor_include_brackets_rx, line):
                    handler.handle_include_brackets(line, matcher.matched)
                elif matcher.match(preprocessor_include_quote_rx, line):
                    handler.handle_include_quote(line, matcher.matched)
                elif matcher.match(preprocessor_pragma_once_rx, line):
                    handler.handle_pragma_once(line)
                elif (
                    matcher.match(preprocessor_line_comment_rx, line)
                    or matcher.match(preprocessor_other_rx, line)
                    or matcher.match(spaces_rx, line)
                ):
                    handler.handle_preprocessor(line, 0)
                elif matcher.match(preprocessor_define_rx, line):
                    handler.handle_preprocessor(line, 0)
                elif matcher.match(preprocessor_if_rx, line):
                    handler.handle_preprocessor(line, 1)
                elif matcher.match(preprocessor_endif_rx, line):
                    handler.handle_preprocessor(line, -1)
                else:
                    handler.handle_main_content(line)
        index += 1


class ModuleLineKind(enum.Enum):
    CONTENT = enum.auto()
    GLOBAL_MODULE_FRAGMENT = enum.auto()
    MODULE_DECLARATION = enum.auto()
    IMPORT = enum.auto()
    EXPORT_BLOCK_START = enum.auto()
    EXPORT_BLOCK_END = enum.auto()
    EXPORT_DECLARATION = enum.auto()


@dataclass(frozen=True)
class ModuleLine:
    kind: ModuleLineKind
    line_number: int
    text: str = ''
    line_ending: str = ''
    indent: str = ''
    name: str = ''
    suffix: str = ''


@dataclass(frozen=True)
class ParsedModuleFile:
    declared_module: str | None
    line_ending: str
    lines: list[ModuleLine]


module_declaration_rx = re.compile(
    r'^\s*(?:export\s+)?module\s+([^;\s]+)\s*;\s*(?://.*)?$'
)
global_module_fragment_rx = re.compile(r'^\s*module\s*;(?P<suffix>\s*(?://.*)?)$')
named_module_declaration_rx = re.compile(
    r'^(?P<indent>\s*)(?:export\s+)?module\s+'
    r'(?P<name>[^;\s]+)\s*;(?P<suffix>\s*(?://.*)?)$'
)
private_module_fragment_rx = re.compile(r'^\s*module\s+:private\s*;\s*(?://.*)?$')
import_declaration_rx = re.compile(
    r'^(?P<indent>\s*)(?:export\s+)?import\s+'
    r'(?P<name>[^;]+?)\s*;(?P<suffix>\s*(?://.*)?)$'
)
export_block_start_rx = re.compile(r'^(?P<indent>\s*)export\s*\{(?P<content>.*)$')
export_block_end_rx = re.compile(r'^\s*}\s*//\s*export\s*$')
export_declaration_rx = re.compile(r'^(?P<indent>\s*)export\s+(?P<declaration>.+)$')
preprocessor_conditional_start_rx = re.compile(r'^\s*#\s*(if|ifdef|ifndef)\b')
preprocessor_conditional_end_rx = re.compile(r'^\s*#\s*endif\b')


def find_declared_module(content: str) -> str | None:
    """Return the first named module declaration in content."""
    for line in content.splitlines():
        match = module_declaration_rx.match(line)
        if match:
            return match.group(1)
    return None


def parse_module_file(
    content: str, filename: str | Path, compatibility_macro: str
) -> ParsedModuleFile:
    """Parse a module file into records consumed by a header builder."""
    filename = Path(filename)
    if f'#ifndef {compatibility_macro}' in content:
        raise ConversionError(
            f'Compatibility module conversion is not supported: "{filename}"'
        )

    result: list[ModuleLine] = []
    export_block_depth = 0
    export_block_in_comment = False
    export_block_preprocessor_depth = 0
    for line_number, line in enumerate(content.splitlines(keepends=True), 1):
        body = line.rstrip('\r\n')
        line_ending = line[len(body) :]

        if export_block_depth:
            if preprocessor_conditional_start_rx.match(body):
                export_block_preprocessor_depth += 1
                brace_delta = 0
            elif preprocessor_conditional_end_rx.match(body):
                export_block_preprocessor_depth = max(
                    0, export_block_preprocessor_depth - 1
                )
                brace_delta = 0
            elif export_block_preprocessor_depth:
                brace_delta = 0
            else:
                brace_delta, export_block_in_comment = _brace_delta(
                    body, export_block_in_comment
                )
            export_block_depth += brace_delta
            if export_block_depth <= 0:
                export_block_depth = 0
                result.append(
                    ModuleLine(
                        ModuleLineKind.EXPORT_BLOCK_END,
                        line_number,
                        line_ending=line_ending,
                    )
                )
            else:
                result.append(
                    ModuleLine(
                        ModuleLineKind.CONTENT,
                        line_number,
                        text=body,
                        line_ending=line_ending,
                    )
                )
            continue

        match = global_module_fragment_rx.match(body)
        if match:
            result.append(
                ModuleLine(
                    ModuleLineKind.GLOBAL_MODULE_FRAGMENT,
                    line_number,
                    line_ending=line_ending,
                    suffix=match.group('suffix'),
                )
            )
            continue

        if private_module_fragment_rx.match(body):
            raise ConversionError(
                f'Private module fragment conversion is not supported: '
                f'"{filename}" at line {line_number}'
            )

        match = named_module_declaration_rx.match(body)
        if match:
            result.append(
                ModuleLine(
                    ModuleLineKind.MODULE_DECLARATION,
                    line_number,
                    line_ending=line_ending,
                    indent=match.group('indent'),
                    name=match.group('name'),
                    suffix=match.group('suffix'),
                )
            )
            continue

        match = import_declaration_rx.match(body)
        if match:
            result.append(
                ModuleLine(
                    ModuleLineKind.IMPORT,
                    line_number,
                    line_ending=line_ending,
                    indent=match.group('indent'),
                    name=match.group('name').strip(),
                    suffix=match.group('suffix'),
                )
            )
            continue

        match = export_block_start_rx.match(body)
        if match:
            block_content = match.group('content')
            result.append(ModuleLine(ModuleLineKind.EXPORT_BLOCK_START, line_number))
            if block_content.strip():
                content_without_close, is_closed = _strip_export_block_close(
                    block_content
                )
                if content_without_close.strip():
                    result.append(
                        ModuleLine(
                            ModuleLineKind.CONTENT,
                            line_number,
                            text=match.group('indent') + content_without_close.strip(),
                            line_ending=line_ending,
                        )
                    )
                if is_closed:
                    result.append(
                        ModuleLine(ModuleLineKind.EXPORT_BLOCK_END, line_number)
                    )
                    continue
            export_block_depth = 1
            continue

        if export_block_end_rx.match(body):
            result.append(ModuleLine(ModuleLineKind.EXPORT_BLOCK_END, line_number))
            continue

        if body.strip() == 'export':
            raise ConversionError(
                f'Multiline export conversion is not supported: '
                f'"{filename}" at line {line_number}'
            )

        match = export_declaration_rx.match(body)
        if match:
            result.append(
                ModuleLine(
                    ModuleLineKind.EXPORT_DECLARATION,
                    line_number,
                    text=match.group('declaration'),
                    line_ending=line_ending,
                    indent=match.group('indent'),
                )
            )
            continue

        result.append(
            ModuleLine(
                ModuleLineKind.CONTENT,
                line_number,
                text=body,
                line_ending=line_ending,
            )
        )

    if export_block_depth:
        raise ConversionError(f'Unclosed export block in "{filename}"')

    preferred_line_ending = '\r\n' if '\r\n' in content else '\n'
    return ParsedModuleFile(
        find_declared_module(content), preferred_line_ending, result
    )


def _brace_delta(line: str, in_block_comment: bool) -> tuple[int, bool]:
    delta = 0
    quote: str | None = None
    escaped = False
    index = 0
    while index < len(line):
        char = line[index]
        next_char = line[index + 1] if index + 1 < len(line) else ''
        if in_block_comment:
            if char == '*' and next_char == '/':
                in_block_comment = False
                index += 2
                continue
        elif quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == quote:
                quote = None
        elif char == '/' and next_char == '/':
            break
        elif char == '/' and next_char == '*':
            in_block_comment = True
            index += 2
            continue
        elif char in {'"', "'"}:
            quote = char
        elif char == '{':
            delta += 1
        elif char == '}':
            delta -= 1
        index += 1
    return delta, in_block_comment


def _strip_export_block_close(content: str) -> tuple[str, bool]:
    depth = 1
    in_block_comment = False
    quote: str | None = None
    escaped = False
    index = 0
    while index < len(content):
        char = content[index]
        next_char = content[index + 1] if index + 1 < len(content) else ''
        if in_block_comment:
            if char == '*' and next_char == '/':
                in_block_comment = False
                index += 2
                continue
        elif quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == quote:
                quote = None
        elif char == '/' and next_char == '/':
            break
        elif char == '/' and next_char == '*':
            in_block_comment = True
            index += 2
            continue
        elif char in {'"', "'"}:
            quote = char
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                if content[index + 1 :].strip():
                    return content, False
                return content[:index].rstrip(), True
        index += 1
    return content, False
