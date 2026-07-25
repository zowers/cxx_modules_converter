from pathlib import Path

from cxx_modules_converter_lib.file_processing import (
    ModuleLineKind,
    find_declared_module,
    parse_module_file,
)


def test_parse_module_file():
    content = (
        'module;\r\n'
        'export module example;\r\n'
        'export import dependency;\r\n'
        'export {\r\n'
        'constexpr auto brace = "}";\r\n'
        '}\r\n'
    )

    parsed = parse_module_file(content, Path('example.cppm'), 'COMPAT')

    assert parsed.declared_module == 'example'
    assert parsed.line_ending == '\r\n'
    assert [line.kind for line in parsed.lines] == [
        ModuleLineKind.GLOBAL_MODULE_FRAGMENT,
        ModuleLineKind.MODULE_DECLARATION,
        ModuleLineKind.IMPORT,
        ModuleLineKind.EXPORT_BLOCK_START,
        ModuleLineKind.CONTENT,
        ModuleLineKind.EXPORT_BLOCK_END,
    ]
    assert parsed.lines[2].name == 'dependency'


def test_find_declared_module():
    assert find_declared_module('module;\nexport module example:part;\n') == (
        'example:part'
    )


def test_parse_export_block_ignores_conditional_braces():
    parsed = parse_module_file(
        'export module example;\n'
        'export {\n'
        '#if ENABLE_EXTRA\n'
        '}\n'
        '#endif\n'
        'struct Example {};\n'
        '}\n',
        Path('example.cppm'),
        'COMPAT',
    )

    assert [line.kind for line in parsed.lines] == [
        ModuleLineKind.MODULE_DECLARATION,
        ModuleLineKind.EXPORT_BLOCK_START,
        ModuleLineKind.CONTENT,
        ModuleLineKind.CONTENT,
        ModuleLineKind.CONTENT,
        ModuleLineKind.CONTENT,
        ModuleLineKind.EXPORT_BLOCK_END,
    ]
    assert parsed.lines[-2].text == 'struct Example {};'


def test_parse_single_line_export_block():
    parsed = parse_module_file(
        'export module example;\nexport { struct Example {}; }\n',
        Path('example.cppm'),
        'COMPAT',
    )

    assert [line.kind for line in parsed.lines] == [
        ModuleLineKind.MODULE_DECLARATION,
        ModuleLineKind.EXPORT_BLOCK_START,
        ModuleLineKind.CONTENT,
        ModuleLineKind.EXPORT_BLOCK_END,
    ]
    assert parsed.lines[2].text == 'struct Example {};'
