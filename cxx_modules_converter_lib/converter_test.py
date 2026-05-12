import os
import os.path
import subprocess
from pathlib import Path

import pytest

from cxx_modules_converter_lib import (
    ContentType,
    ConvertAction,
    Converter,
    convert_directory,
)


@pytest.fixture(scope="function")
def dir_simple(tmp_path_factory: pytest.TempPathFactory):
    path = tmp_path_factory.mktemp("simple")
    return path


def assert_files(expected_dir: Path, result_dir: Path, expected_files: list[str]):
    result_files: set[str] = set()
    for root, _, files in os.walk(result_dir):
        if 'build' in Path(root).parts:
            continue
        relative_root = Path(os.path.relpath(root, result_dir))
        for name in files:
            result_files.add(relative_root.joinpath(name).as_posix())
    assert result_files == set(expected_files)

    for filename in expected_files:
        result_path = result_dir.joinpath(filename)
        print('assert_files filename:', filename)
        assert os.path.exists(result_path)
        with open(expected_dir.joinpath(filename)) as expected_file:
            expected_content = expected_file.read()
        with open(result_dir.joinpath(filename)) as result_file:
            result_content = result_file.read()
        assert result_content == expected_content


def run_cmake_test(dir_simple: Path, preset: str):
    configure_cmd = ["cmake", "--preset", preset, "--fresh"]
    result_configure = subprocess.run(
        configure_cmd, cwd=dir_simple, capture_output=True, text=True
    )

    assert result_configure.returncode == 0, (
        f"CMake configure failed for preset {preset}:\n"
        f"Command: {' '.join(configure_cmd)}\n"
        f"STDOUT:\n{result_configure.stdout}\n"
        f"STDERR:\n{result_configure.stderr}"
    )

    build_cmd = ["cmake", "--build", "--preset", preset]
    result_build = subprocess.run(
        build_cmd, cwd=dir_simple, capture_output=True, text=True
    )

    assert result_build.returncode == 0, (
        f"CMake build failed for preset {preset}:\n"
        f"Command: {' '.join(build_cmd)}\n"
        f"STDOUT:\n{result_build.stdout}\n"
        f"STDERR:\n{result_build.stderr}"
    )


CMAKE_TEST_CASES = ["test-clang-20", "test-clang-21", "test-gcc-15"]


def test_dir_simple(dir_simple: Path):
    data_directory = Path('test_data/simple')
    convert_directory(
        ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple
    )
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'simple.cppm',
            'simple.cpp',
            'main.cpp',
            'CMakeLists.txt',
            'CMakePresets.json',
        ],
    )


@pytest.mark.slow
@pytest.mark.parametrize("preset", CMAKE_TEST_CASES)
def test_dir_simple_cmake(dir_simple: Path, preset: str):
    data_directory = Path('test_data/simple')
    convert_directory(
        ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple
    )
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'simple.cppm',
            'simple.cpp',
            'main.cpp',
            'CMakeLists.txt',
            'CMakePresets.json',
        ],
    )

    run_cmake_test(dir_simple, preset)


@pytest.mark.slow
@pytest.mark.parametrize("preset", CMAKE_TEST_CASES)
def test_dir_circular_dependencies_partitions_impl_cmake(dir_simple: Path, preset: str):
    """Test for detecting circular dependencies in partitions implementation using CMake"""  # noqa: E501
    data_directory = Path('test_data/circular_partitions_impl')
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_join_configuration('mymodule', 'mymodule/*')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)

    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'mymodule/part1.cppm',
            'mymodule/part2.cppm',
            'mymodule/part1.cpp',
            'mymodule/part2.cpp',
            'mymodule.cppm',
            'main.cpp',
            'CMakeLists.txt',
            'CMakePresets.json',
            'build.sh',
        ],
    )

    run_cmake_test(dir_simple, preset)


def test_dir_simple_std(dir_simple: Path):
    data_directory = Path('test_data/simple_std')
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_std_module()
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'simple.cppm',
            'simple.cpp',
        ],
    )


def test_dir_named1(dir_simple: Path):
    data_directory = Path('test_data/named1')
    converter = Converter(ConvertAction.MODULES)
    converter.options.set_root_dir_module_name('org')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    # convert_directory(ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple)  # noqa: E501
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'simple.cppm',
            'simple.cpp',
        ],
    )


def test_dir_prefix(dir_simple: Path):
    data_directory = Path('test_data/prefix')
    converter = Converter(ConvertAction.MODULES)
    input_dir = data_directory.joinpath('input')
    converter.options.root_dir = input_dir
    converter.convert_directory(input_dir.joinpath('subdir'), dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'subdir/simple.cppm',
            'subdir/simple.cpp',
        ],
    )


def test_dir_prefix_named(dir_simple: Path):
    data_directory = Path('test_data/prefix_named')
    converter = Converter(ConvertAction.MODULES)
    input_dir = data_directory.joinpath('input')
    converter.options.root_dir = input_dir
    converter.options.set_root_dir_module_name('org')
    converter.convert_directory(input_dir.joinpath('subdir'), dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'subdir/local_include.cppm',
            'subdir/simple.cppm',
            'subdir/simple.cpp',
        ],
    )


def test_dir_modules_path(dir_simple: Path):
    data_directory = Path('test_data/modules_path')
    converter = Converter(ConvertAction.MODULES)
    input_dir = data_directory.joinpath('input')
    converter.options.root_dir = input_dir
    converter.options.add_modules_path(
        'org', ''
    )  # same as `.set_root_dir_module_name('org')`
    converter.options.add_modules_path('org2', 'dir2')
    converter.convert_directory(input_dir, dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'subdir/local_include.cppm',
            'subdir/simple.cppm',
            'subdir/simple.cpp',
            'dir2/local_include.cppm',
            'dir2/simple.cppm',
            'dir2/simple.cpp',
        ],
    )


def test_dir_compat(dir_simple: Path):
    data_directory = Path('test_data/compat')
    converter = Converter(ConvertAction.MODULES)
    converter.options.compat_patterns = [
        'simple.h',
        'simple.cpp',
        'subdir/*',
    ]
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'simple.h',
            'simple.cppm',
            'simple.cpp',
            'subdir/simple2.h',
            'subdir/simple2.cppm',
            'subdir/simple2.cpp',
        ],
    )


def test_dir_other(dir_simple: Path):
    data_directory = Path('test_data/other')
    convert_directory(
        ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple
    )
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'other.txt',
        ],
    )


def test_dir_two(dir_simple: Path):
    data_directory = Path('test_data/two')
    convert_directory(
        ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple
    )
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'simple1.cppm',
            'simple2.cppm',
        ],
    )


def test_dir_subdir(dir_simple: Path):
    data_directory = Path('test_data/subdir')
    convert_directory(
        ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple
    )
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'subdir1/simple1.cppm',
            'subdir1/simple2.cppm',
        ],
    )


def test_dir_skip(dir_simple: Path):
    data_directory = Path('test_data/skip')
    converter = Converter(ConvertAction.MODULES)
    converter.options.skip_patterns = [
        'skipdir',
        'subdir1/simple2.h',
        'subdir1/skipsubdir',
    ]
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'subdir1/simple1.cppm',
        ],
    )


def test_dir_subdirs(dir_simple: Path):
    data_directory = Path('test_data/subdirs')
    convert_directory(
        ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple
    )
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'simple1.cppm',
            'subdir1/simple1.cppm',
            'subdir1/simple2.cppm',
            'subdir1/subdir2/simple1.cppm',
            'subdir1/subdir2/simple2.cppm',
        ],
    )


def test_dir_subdirs_rooted(dir_simple: Path):
    data_directory = Path('test_data/subdirs_rooted')
    converter = Converter(ConvertAction.MODULES)
    input_dir = data_directory.joinpath('input')
    converter.options.root_dir = input_dir
    converter.convert_directory(input_dir.joinpath('subdir'), dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'subdir/simple1.cppm',
            'subdir/subdir1/simple1.cppm',
            'subdir/subdir1/simple2.cppm',
            'subdir/subdir1/use_relative_include.cppm',
            'subdir/subdir1/use_relative_include_missing.cppm',
            'subdir/subdir1/use_search_path_include_existing.cppm',
            'subdir/subdir1/subdir2/simple1.cppm',
            'subdir/subdir1/subdir2/simple1.cpp',
            'subdir/subdir1/subdir2/simple2.cppm',
        ],
    )


def test_dir_subdirs_rooted_brackets(dir_simple: Path):
    data_directory = Path('test_data/subdirs_rooted_brackets')
    converter = Converter(ConvertAction.MODULES)
    input_dir = data_directory.joinpath('input')
    converter.options.root_dir = input_dir
    converter.convert_directory(input_dir.joinpath('subdir'), dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'subdir/simple1.cppm',
            'subdir/subdir1/simple1.cppm',
            'subdir/subdir1/simple2.cppm',
            'subdir/subdir1/use_relative_include.cppm',
            'subdir/subdir1/use_relative_include_missing.cppm',
            'subdir/subdir1/use_search_path_include_existing.cppm',
            'subdir/subdir1/subdir2/simple1.cppm',
            'subdir/subdir1/subdir2/simple1.cpp',
            'subdir/subdir1/subdir2/simple2.cppm',
        ],
    )


def test_dir_header(dir_simple: Path):
    data_directory = Path('test_data/header')
    converter = Converter(ConvertAction.MODULES)
    converter.options.always_include_names.append('simple.h')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'simple.h',
            'simple.cpp',
        ],
    )


def test_dir_header_subdir(dir_simple: Path):
    data_directory = Path('test_data/header_subdir')
    converter = Converter(ConvertAction.MODULES)
    converter.options.always_include_names.append('subdir/**')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'subdir/simple.h',
            'subdir/simple.cpp',
        ],
    )


def test_dir_header_subdir_nested(dir_simple: Path):
    data_directory = Path('test_data/header_subdir_nested')
    converter = Converter(ConvertAction.MODULES)
    converter.options.always_include_names.append('subdir/**')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'subdir/nested/simple.h',
            'subdir/nested/simple.cpp',
        ],
    )


def test_dir_twice(dir_simple: Path):
    data_directory = Path('test_data/twice')
    converter = Converter(ConvertAction.MODULES)
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'simple.cppm',
            'simple.cpp',
            'other.txt',
        ],
    )
    assert converter.all_files == 3
    assert converter.convertable_files == 2
    assert converter.converted_files == 2
    assert converter.copied_files == 1
    converter = Converter(ConvertAction.MODULES)
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert converter.all_files == 3
    assert converter.convertable_files == 2
    assert converter.converted_files == 0
    assert converter.copied_files == 0


def test_dir_inext(dir_simple: Path):
    data_directory = Path('test_data/inext')
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_module_action_ext_type('.hpp', ContentType.HEADER)
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'simple.cppm',
            'simple2.h',
            'simple.cpp',
        ],
    )


def test_dir_outext(dir_simple: Path):
    data_directory = Path('test_data/outext')
    converter = Converter(ConvertAction.MODULES)
    converter.options.set_output_content_type_to_ext(
        ContentType.MODULE_INTERFACE, '.ixx'
    )
    converter.options.set_output_content_type_to_ext(ContentType.MODULE_IMPL, '.cxx')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'simple.ixx',
            'simple.cxx',
            'simple2.hpp',
        ],
    )


def test_dir_partitions(dir_simple: Path):
    data_directory = Path('test_data/partitions')
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_join_configuration('mymodule', '*')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'part1.cppm',
            'part2.cppm',
            'subdir/part3.cppm',
            'mymodule.cppm',
        ],
    )


def test_dir_partitions_local_import(dir_simple: Path):
    data_directory = Path('test_data/partitions_local_import')
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_join_configuration('mymodule', '*')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'part1.cppm',
            'part2.cppm',
            'subdir/part3.cppm',
            'mymodule.cppm',
        ],
    )


def test_dir_custom_join_configurations(dir_simple: Path):
    data_directory = Path('test_data/custom_join_test')
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_join_configuration('mymodule1', 'subdir1/*')
    converter.options.add_join_configuration('mymodule2', 'subdir2/*')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'subdir1/simple.cppm',
            'subdir2/simple.cpp',
            'subdir2/simple.cppm',
            'mymodule1.cppm',
            'mymodule2.cppm',
        ],
    )


def test_dir_partitions_header_match(dir_simple: Path):
    data_directory = Path('test_data/partitions_header_match')
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_join_configuration('mymodule', 'mymodule/*')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'mymodule.cppm',
            'mymodule/part1.cppm',
            'mymodule/part2.cppm',
        ],
    )


def test_dir_circular_dependencies(dir_simple: Path):
    """Test for detecting circular dependencies in directory"""
    data_directory = Path('test_data/circular')
    converter = Converter(ConvertAction.MODULES)
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)

    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'moduleA.cppm',
            'moduleB.cppm',
            'moduleC.cppm',
        ],
    )

    assert len(converter.circular_dependencies) == 1

    cycle = converter.circular_dependencies[0]
    expected_modules = {'moduleA', 'moduleB', 'moduleC'}
    assert set(cycle) == expected_modules


def test_dir_circular_dependencies_self(dir_simple: Path):
    """Test that dependency between implementation and interface of the same module is not counted as circular"""  # noqa: E501
    data_directory = Path('test_data/circular_dependency_self')
    converter = Converter(ConvertAction.MODULES)
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)

    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'moduleA.cppm',
            'moduleA.cpp',
        ],
    )

    assert len(converter.circular_dependencies) == 0


def test_dir_circular_dependencies_partitions(dir_simple: Path):
    """Test for detecting circular dependencies in partitions"""
    data_directory = Path('test_data/circular_partitions')
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_join_configuration('mymodule', '*')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)

    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'part1.cppm',
            'part2.cppm',
            'part3.cppm',
            'mymodule.cppm',
        ],
    )

    assert len(converter.circular_dependencies) == 1

    cycle = converter.circular_dependencies[0]
    expected_modules = {'mymodule:part1', 'mymodule:part2', 'mymodule:part3'}
    assert set(cycle) == expected_modules


def test_dir_circular_dependencies_partitions_impl(dir_simple: Path):
    """Test for detecting circular dependencies in partitions implementation"""
    data_directory = Path('test_data/circular_partitions_impl')
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_join_configuration('mymodule', 'mymodule/*')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)

    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'mymodule/part1.cppm',
            'mymodule/part2.cppm',
            'mymodule/part1.cpp',
            'mymodule/part2.cpp',
            'mymodule.cppm',
            'main.cpp',
            'CMakeLists.txt',
            'CMakePresets.json',
            'build.sh',
        ],
    )

    assert len(converter.circular_dependencies) == 1

    cycle = converter.circular_dependencies[0]
    expected_modules = {'mymodule:part1', 'mymodule:part2'}
    assert set(cycle) == expected_modules


def test_dir_circular_dependencies_impl(dir_simple: Path):
    """Test for detecting circular dependencies implementation without partitions"""
    data_directory = Path('test_data/circular_impl')
    converter = Converter(ConvertAction.MODULES)
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)

    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'moduleA.cppm',
            'moduleB.cppm',
            'moduleC.cppm',
            'moduleA.cpp',
            'moduleB.cpp',
            'moduleC.cpp',
            'main.cpp',
            'CMakeLists.txt',
            'CMakePresets.json',
        ],
    )

    assert len(converter.circular_dependencies) == 1

    cycle = converter.circular_dependencies[0]
    expected_modules = {'moduleA', 'moduleB', 'moduleC'}
    assert set(cycle) == expected_modules


@pytest.mark.slow
@pytest.mark.parametrize("preset", CMAKE_TEST_CASES)
def test_dir_circular_dependencies_impl_cmake(dir_simple: Path, preset: str):
    """Test for detecting circular dependencies implementation without partitions using CMake"""  # noqa: E501
    data_directory = Path('test_data/circular_impl')
    convert_directory(
        ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple
    )
    assert_files(
        data_directory.joinpath('expected'),
        dir_simple,
        [
            'moduleA.cppm',
            'moduleB.cppm',
            'moduleC.cppm',
            'moduleA.cpp',
            'moduleB.cpp',
            'moduleC.cpp',
            'main.cpp',
            'CMakeLists.txt',
            'CMakePresets.json',
        ],
    )

    run_cmake_test(dir_simple, preset)
