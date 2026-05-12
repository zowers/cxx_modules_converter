from __future__ import annotations

import enum
import re
from pathlib import Path
from typing import TypeAlias

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
