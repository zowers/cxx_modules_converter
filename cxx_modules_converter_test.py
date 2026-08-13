import subprocess
import sys
from pathlib import Path


def test_cli_accepts_headers_action_and_extensions(tmp_path: Path):
    source_dir = tmp_path / 'modules'
    result_dir = tmp_path / 'headers'
    source_dir.mkdir()
    (source_dir / 'example.ixx').write_text(
        'export module example;\nexport struct Example {};\n'
    )
    (source_dir / 'example.cxxm').write_text('module example;\n')

    result = subprocess.run(
        [
            sys.executable,
            'cxx_modules_converter.py',
            '--action',
            'headers',
            '--directory',
            str(source_dir),
            '--destination',
            str(result_dir),
            '--root',
            str(source_dir),
            '--inextmod',
            '.ixx',
            '--inextmodimpl',
            '.cxxm',
            '--outextheader',
            '.hpp',
            '--outextcxx',
            '.cc',
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (result_dir / 'example.hpp').read_text() == (
        '#pragma once\nstruct Example {};\n'
    )
    assert (result_dir / 'example.cc').read_text() == '#include "example.hpp"\n'


def test_cli_accepts_modules_path(tmp_path: Path):
    source_dir = tmp_path / 'project'
    result_dir = tmp_path / 'modules'
    source_dir.joinpath('src').mkdir(parents=True)
    source_dir.joinpath('src/example.h').write_text('struct Example {};\n')

    result = subprocess.run(
        [
            sys.executable,
            'cxx_modules_converter.py',
            '--directory',
            str(source_dir),
            '--destination',
            str(result_dir),
            '--root',
            str(source_dir),
            '--modules',
            'example=src',
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (
        'export module example.example;'
        in result_dir.joinpath('src/example.cppm').read_text()
    )
