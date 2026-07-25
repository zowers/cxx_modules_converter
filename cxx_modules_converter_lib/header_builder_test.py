from pathlib import Path

from cxx_modules_converter_lib import (
    ContentType,
    HeaderBuilder,
    Options,
    parse_module_file,
)
from cxx_modules_converter_lib.resolvers import FilesResolver


def test_header_builder_builds_relative_imports():
    options = Options()
    resolver = FilesResolver(options)
    parsed = parse_module_file(
        'export module example;\n'
        'export import dependency;\n'
        'export struct Example {};\n',
        'nested/example.cppm',
        options.compat_macro,
    )
    builder = HeaderBuilder(
        options,
        resolver,
        ContentType.MODULE_INTERFACE,
        parsed,
        {'example': Path('nested/example.h'), 'dependency': Path('dependency.h')},
    )
    builder.set_source_filename(Path('nested/example.cppm'))

    result = builder.build_file_content()

    assert result.filename == Path('nested/example.h')
    assert result.content_type == ContentType.HEADER
    assert result.content == (
        '#pragma once\n#include "../dependency.h"\nstruct Example {};\n'
    )
