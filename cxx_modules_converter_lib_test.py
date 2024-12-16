import os.path
import pathlib
import pytest
from cxx_modules_converter_lib import (
    Converter,
    convert_file_content,
    convert_directory,
    ConvertAction,
    ContentType,
    )

def test_module_empty():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''''', 'simple.h')
    assert(converted == '''export module simple;
''')

def test_module_include_system():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include <vector>
''', 'simple.h')
    assert(converted ==
'''module;
#include <vector>
export module simple;
''')

def test_module_include_local():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
''', 'simple.h')
    assert(converted == 
'''export module simple;
import local_include;
''')

def test_module_include_always_include_names_assert_h():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "assert.h"
''', 'simple.h')
    assert(converted == 
'''export module simple;
#include "assert.h"
''')

def test_module_impl_include_local():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
''', 'simple.cpp')
    assert(converted == 
'''module simple;
import local_include;
''')

def test_module_impl_include_self_header():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "simple.h"
''', 'simple.cpp')
    assert(converted == 
'''module simple;
''')

def test_module_impl_include_local_self_header_prefix():
    converter = Converter(ConvertAction.MODULES)
    converted = converter.convert_file_content(
'''#include "simple.h"
#include "local_include.h"
''', 'prefix/simple.cpp')
    assert(converted == 
'''module prefix.simple;
import prefix.local_include;
''')

def test_resolve_include():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('subdir/simple.cpp', ContentType.CXX)
    assert(builder.module_dir == pathlib.PurePosixPath('subdir'))
    assert(builder.resolve_include('simple.h') == pathlib.PurePosixPath('subdir/simple.h'))

def test_resolve_include_no_dir():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    assert(builder.module_dir == pathlib.PurePosixPath(''))
    assert(builder.resolve_include('simple.h') == pathlib.PurePosixPath('simple.h'))

def test_module_impl_include_local_self_header_subdir():
    converter = Converter(ConvertAction.MODULES)
    converted = converter.convert_file_content(
'''#include "simple.h"
#include "local_include.h"
''', 'subdir/simple.cpp')
    assert(converted == 
'''module subdir.simple;
import subdir.local_include;
''')

def test_module_impl_include_local_self_header_subdir_prefix():
    converter = Converter(ConvertAction.MODULES)
    converted = converter.convert_file_content(
'''#include "simple.h"
#include "local_include.h"
''', 'prefix/subdir/simple.cpp')
    assert(converted == 
'''module prefix.subdir.simple;
import prefix.subdir.local_include;
''')

def test_module_include_local_and_system():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
#include <vector>
''', 'simple.h')
    assert(converted == 
'''module;
#include <vector>
export module simple;
import local_include;
''')

def test_module_file_comment():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''// this is file comment
''', 'simple.h')
    assert(converted == '''// this is file comment
export module simple;
''')

def test_module_bom_and_file_comment():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''\ufeff// this is file comment
''', 'simple.h')
    assert(converted ==
'''\ufeff// this is file comment
export module simple;
''')

def test_module_file_comment_and_include_system():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''// this is file comment
#include <vector>
''', 'simple.h')
    assert(converted == '''// this is file comment
module;
#include <vector>
export module simple;
''')

def test_module_file_comment_and_include_local_and_system():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''// this is file comment
#include "local_include.h"
#include <vector>
''', 'simple.h')
    assert(converted ==
'''// this is file comment
module;
#include <vector>
export module simple;
import local_include;
''')

def test_module_file_comment_and_include_system_w_newlines():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''
// this is file comment

#include <vector>

''', 'simple.h')
    assert(converted == 
'''
// this is file comment

module;
#include <vector>
export module simple;
''')

def test_module_file_comment_and_include_local_and_system_w_newlines():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''
// this is file comment

#include "local_include.h"

#include <vector>
''', 'simple.h')
    assert(converted ==
'''
// this is file comment

module;
#include <vector>
export module simple;
import local_include;

''')

def test_module_file_comment_and_include_local_and_system_w_content():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''
// this is file comment

#include "local_include.h"

#include <vector>

namespace TestNS
{
namespace Test
{
class TestClass
{
};
} // namespace Test
} // namespace TestNS

''', 'simple.h')
    assert(converted ==
'''
// this is file comment

module;
#include <vector>
export module simple;
import local_include;


namespace TestNS
{
namespace Test
{
class TestClass
{
};
} // namespace Test
} // namespace TestNS

''')

@pytest.fixture(scope="session")
def dir_simple(tmp_path_factory):
    path = tmp_path_factory.mktemp("simple")
    return path

def assert_files(expected_dir: pathlib.Path, result_dir: pathlib.Path, expected_files: list[str]):
    for filename in expected_files:
        result_path = result_dir.joinpath(filename)
        print('assert_files filename:', filename)
        assert os.path.exists(result_path)
        with open(expected_dir.joinpath(filename)) as expected_file:
            expected_content = expected_file.read()
        with open(result_dir.joinpath(filename)) as result_file:
            result_content = result_file.read()
        assert(result_content == expected_content)

def test_dir_simple(dir_simple: pathlib.Path):
    data_directory = pathlib.Path('test_data/simple')
    convert_directory(ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'simple.cppm',
        'simple.cpp',
    ])

def test_dir_prefix(dir_simple: pathlib.Path):
    data_directory = pathlib.Path('test_data/prefix')
    converter = Converter(ConvertAction.MODULES)
    input_dir = data_directory.joinpath('input')
    converter.options.root_dir = input_dir
    converter.convert_directory(input_dir.joinpath('subdir'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'subdir/simple.cppm',
        'subdir/simple.cpp',
    ])

def test_dir_other(dir_simple: pathlib.Path):
    data_directory = pathlib.Path('test_data/other')
    convert_directory(ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'other.txt',
    ])

def test_dir_two(dir_simple: pathlib.Path):
    data_directory = pathlib.Path('test_data/two')
    convert_directory(ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'simple1.cppm',
        'simple2.cppm',
    ])

def test_dir_subdir(dir_simple: pathlib.Path):
    data_directory = pathlib.Path('test_data/subdir')
    convert_directory(ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'subdir1/simple1.cppm',
        'subdir1/simple2.cppm',
    ])

def test_dir_subdirs(dir_simple: pathlib.Path):
    data_directory = pathlib.Path('test_data/subdirs')
    convert_directory(ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'simple1.cppm',
        'subdir1/simple1.cppm',
        'subdir1/simple2.cppm',
        'subdir1/subdir2/simple1.cppm',
        'subdir1/subdir2/simple2.cppm',
    ])

def test_dir_subdirs_rooted(dir_simple: pathlib.Path):
    data_directory = pathlib.Path('test_data/subdirs_rooted')
    converter = Converter(ConvertAction.MODULES)
    input_dir = data_directory.joinpath('input')
    converter.options.root_dir = input_dir
    converter.convert_directory(input_dir.joinpath('subdir'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'subdir/simple1.cppm',
        'subdir/subdir1/simple1.cppm',
        'subdir/subdir1/simple2.cppm',
        'subdir/subdir1/subdir2/simple1.cppm',
        'subdir/subdir1/subdir2/simple1.cpp',
        'subdir/subdir1/subdir2/simple2.cppm',
    ])
