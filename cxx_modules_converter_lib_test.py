import os
import os.path
from pathlib import Path, PurePosixPath
import pytest
from cxx_modules_converter_lib import (
    Converter,
    convert_file_content,
    convert_directory,
    ConvertAction,
    ContentType,
    FilesMap,
    FileEntryType,
    Options,
    FileOptions,
    FilesResolver,
    ModuleFilesResolver,
    FileContent,
    find_cycles,
    )
import subprocess


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

def test_module_include_system_w_inline_comment():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include <vector>    // inline comment
''', 'simple.h')
    assert(converted ==
'''module;
#include <vector>    // inline comment
export module simple;
''')

def test_module_include_local_w_inline_comment():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"   // inline comment
''', 'simple.h')
    assert(converted == 
'''export module simple;
import local_include;   // inline comment
''')

def test_module_include_system_w_left_padding():
    converted = convert_file_content(
        ConvertAction.MODULES,
''' # include <vector>
''', 'simple.h')
    assert(converted ==
'''module;
 # include <vector>
export module simple;
''')

def test_module_include_local_w_left_padding():
    converted = convert_file_content(
        ConvertAction.MODULES,
''' # include "local_include.h"
''', 'simple.h')
    assert(converted == 
'''export module simple;
  import local_include;
''')

def test_module_include_system_ifdef():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
#ifdef FLAG
 # include <vector>
#endif // FLAG
''', 'simple.h')
    assert(converted == 
'''module;
#ifdef FLAG
 # include <vector>
#endif // FLAG
export module simple;
import local_include;
''')

def test_module_include_system_ifdef_and_content():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
#ifdef FLAG
 # include <vector>
#endif // FLAG
namespace TestNS {}
''', 'simple.h')
    assert(converted == 
'''module;
#ifdef FLAG
 # include <vector>
#endif // FLAG
export module simple;
import local_include;
export {
namespace TestNS {}
} // export
''')

def test_module_include_local_ifdef():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
#ifdef FLAG
 # include "local_include_2.h"
#endif // FLAG
''', 'simple.h')
    assert(converted == 
'''export module simple;
import local_include;
#ifdef FLAG
  import local_include_2;
#endif // FLAG
''')

def test_module_include_local_ifdef_and_content():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
#ifdef FLAG
 # include "local_include_2.h"
#endif // FLAG
namespace TestNS {}
''', 'simple.h')
    assert(converted == 
'''export module simple;
import local_include;
#ifdef FLAG
  import local_include_2;
#endif // FLAG
export {
namespace TestNS {}
} // export
''')

def test_module_include_system_ifdef_and_content_w_newlines():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"

#ifdef FLAG

 # include <vector>

#endif // FLAG

namespace TestNS {}
''', 'simple.h')
    assert(converted == 
'''module;

#ifdef FLAG

 # include <vector>

#endif // FLAG
export module simple;
import local_include;
export {

namespace TestNS {}
} // export
''')

def test_module_include_system_ifdef_twice():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
#ifdef FLAG1
 # include <vector>
#endif // FLAG1
#ifdef FLAG2
 # include <string>
#endif // FLAG2
''', 'simple.h')
    assert(converted == 
'''module;
#ifdef FLAG1
 # include <vector>
#endif // FLAG1
#ifdef FLAG2
 # include <string>
#endif // FLAG2
export module simple;
import local_include;
''')

def test_module_include_local_ifdef_twice():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
#ifdef FLAG1
 # include "local_include_2.h"
#endif // FLAG1
#ifdef FLAG2
 # include "local_include_3.h"
#endif // FLAG2
''', 'simple.h')
    assert(converted == 
'''export module simple;
import local_include;
#ifdef FLAG1
  import local_include_2;
#endif // FLAG1
#ifdef FLAG2
  import local_include_3;
#endif // FLAG2
''')

def test_module_include_system_ifdef_elif_else():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
#ifdef FLAG1
 # include <vector>
#elif FLAG2
 # include <string>
#else // FLAG2
 # include <map>
#endif // FLAG2
''', 'simple.h')
    assert(converted == 
'''module;
#ifdef FLAG1
 # include <vector>
#elif FLAG2
 # include <string>
#else // FLAG2
 # include <map>
#endif // FLAG2
export module simple;
import local_include;
''')

def test_module_include_pragma_once():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#pragma once
#include "local_include.h"
#include <vector>
''', 'simple.h')
    assert(converted == 
'''module;
#include <vector>
export module simple;
// #pragma once
import local_include;
''')

def test_module_include_system_pragma_define():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
#define FLAG
#error "error"
#pragma test
#warning "warning"
#include <vector>
''', 'simple.h')
    assert(converted == 
'''module;
#define FLAG
#error "error"
#pragma test
#warning "warning"
#include <vector>
export module simple;
import local_include;
''')

def test_module_include_local_and_system_multiline_define():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
#define FLAG \\
    1 \\
    2
#include <vector>
''', 'simple.h')
    assert(converted == 
'''module;
#define FLAG \\
    1 \\
    2
#include <vector>
export module simple;
import local_include;
''')

def test_module_include_system_and_local_in_one_ifdef():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
#ifdef FLAG
 # include <vector>
 # include "local_include_2.h"
#endif // FLAG
''', 'simple.h')
    assert(converted == 
'''module;
#ifdef FLAG
 # include <vector>
#endif // FLAG
export module simple;
import local_include;
#ifdef FLAG
  import local_include_2;
#endif // FLAG
''')

def test_module_include_system_and_local_in_two_ifdefs_and_comments():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
// comment flag1
#ifdef FLAG1
 // comment system include
 # include <vector>
#endif // FLAG1
// comment flag2
#ifdef FLAG2
 // comment local include
 # include "local_include_2.h"
#endif // FLAG2
''', 'simple.h')
    assert(converted == 
'''module;
// comment flag1
#ifdef FLAG1
 // comment system include
 # include <vector>
#endif // FLAG1
export module simple;
import local_include;
// comment flag2
#ifdef FLAG2
 // comment local include
  import local_include_2;
#endif // FLAG2
''')

def test_module_include_system_and_local_multiline_ifdef_elif():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
#ifdef FLAG1 \\
    && FLAG11
 # include <vector>
#elif FLAG1 \\
    && FLAG11
 // nothing
#endif // FLAG1
#ifdef FLAG2 \\
    && FLAG22
 # include "local_include_2.h"
#endif // FLAG2
''', 'simple.h')
    assert(converted == 
'''module;
#ifdef FLAG1 \\
    && FLAG11
 # include <vector>
#elif FLAG1 \\
    && FLAG11
 // nothing
#endif // FLAG1
export module simple;
import local_include;
#ifdef FLAG2 \\
    && FLAG22
  import local_include_2;
#endif // FLAG2
''')


def test_module_ifdef_w_content():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
#include <vector>

// before preprocessor
#ifdef FLAG1

// inside preprocessor
namespace TestNS
{

namespace Test
{

class TestClass
{
};

} // namespace Test
} // namespace TestNS
#endif // FLAG1
''', 'simple.h')
    assert(converted == 
'''module;
#include <vector>
export module simple;
import local_include;

// before preprocessor
export {
#ifdef FLAG1

// inside preprocessor
namespace TestNS
{

namespace Test
{

class TestClass
{
};

} // namespace Test
} // namespace TestNS
#endif // FLAG1
} // export
''')

def test_module_include_system_comment():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
// comment before system include
#include <vector>
''', 'simple.h')
    assert(converted == 
'''module;
// comment before system include
#include <vector>
export module simple;
import local_include;
''')

def test_module_include_local_comment():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
// comment before local include
 # include "local_include_2.h"
''', 'simple.h')
    assert(converted == 
'''export module simple;
import local_include;
// comment before local include
  import local_include_2;
''')

def test_module_include_always_include_names_assert_h():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "assert.h"
''', 'simple.h')
    assert(converted == 
'''module;
#include "assert.h"
export module simple;
''')

def test_module_include_always_include_names_options():
    converter = Converter(ConvertAction.MODULES)
    converter.options.always_include_names.append('options.h')
    converted = converter.convert_file_content(
'''#include "options.h"
''', 'simple.h')
    assert(converted[0].content == 
'''module;
#include "options.h"
export module simple;
''')

def test_module_include_always_include_names_in_subdir():
    converter = Converter(ConvertAction.MODULES)
    converter.options.always_include_names.append('subdir/options.h')
    converter.resolver.files_map.add_files_map_dict({
        'subdir': {
            'options.h': FileEntryType.FILE,
            'simple.h': FileEntryType.FILE,
        },
    })
    converted = converter.convert_file_content(
'''#include "options.h"
''', 'subdir/simple.h')
    assert(converted[0].content == 
'''module;
#include "options.h"
export module subdir.simple;
''')

def test_module_include_always_include_names_subdir():
    converter = Converter(ConvertAction.MODULES)
    converter.options.always_include_names.append('subdir/*')
    converter.resolver.files_map.add_files_map_dict({
        'subdir': {
            'options.h': FileEntryType.FILE,
            'simple.h': FileEntryType.FILE,
        },
    })
    converted = converter.convert_file_content(
'''#include "options.h"
''', 'subdir/simple.h')
    assert(converted[0].content == 
'''module;
#include "options.h"
export module subdir.simple;
''')

def test_module_include_always_include_names_subdir_root_named():
    converter = Converter(ConvertAction.MODULES)
    converter.options.always_include_names.append('subdir/options.h')
    converter.resolver.files_map.add_files_map_dict({
        'subdir': {
            'options.h': FileEntryType.FILE,
            'simple.h': FileEntryType.FILE,
        },
    })
    converter.options.set_root_dir_module_name('org')
    converted = converter.convert_file_content(
'''#include "options.h"
''', 'subdir/simple.h')
    assert(converted[0].content == 
'''module;
#include "options.h"
export module org.subdir.simple;
''')

def test_module_impl_include_local():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "local_include.h"
''', 'simple.cpp')
    assert(converted == 
'''import local_include;
''')

def test_module_impl_include_system():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include <vector>
''', 'simple.cpp')
    assert(converted == 
'''#include <vector>
''')

def test_module_impl_include_self_header():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "simple.h"
''', 'simple.cpp')
    assert(converted == 
'''module simple;
''')

def test_module_impl_include_self_header_and_system():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "simple.h"
#include <vector>
''', 'simple.cpp')
    assert(converted ==
'''module;
#include <vector>
module simple;
''')

def test_module_impl_include_self_header_and_system_and_local():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "simple.h"
#include "local_include.h"
#include <vector>
''', 'simple.cpp')
    assert(converted ==
'''module;
#include <vector>
module simple;
import local_include;
''')

def test_module_impl_include_self_header_and_system_and_local_and_assert_h():
    converted = convert_file_content(
        ConvertAction.MODULES,
'''#include "simple.h"
#include "local_include.h"
#include "assert.h"
#include <vector>
''', 'simple.cpp')
    assert(converted ==
'''module;
#include "assert.h"
#include <vector>
module simple;
import local_include;
''')

def test_module_impl_include_self_header_compat():
    converter = Converter(ConvertAction.MODULES)
    file_options = FileOptions()
    file_options.convert_as_compat = True
    converted = converter.convert_file_content(
'''#include "simple.h"
''', 'simple.cpp', file_options)
    assert(converted == [
        FileContent("simple.cpp", ContentType.MODULE_IMPL,
'''module simple;
'''),
])

def test_module_impl_include_assert_and_self_header_compat():
    converter = Converter(ConvertAction.MODULES)
    file_options = FileOptions()
    file_options.convert_as_compat = True
    converted = converter.convert_file_content(
'''#include "assert.h"
#include "simple.h"
''', 'simple.cpp', file_options)
    assert(converted == [
        FileContent("simple.cpp", ContentType.MODULE_IMPL,
'''module;
#include "assert.h"
module simple;
'''),
])

def test_module_interface_export():
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_export_module('simple', 'simple_fwd')
    converted = converter.convert_file_content(
'''#include "simple_fwd.h"
#include "simple2.h"
''', 'simple.h')
    assert(converted[0].content == 
'''export module simple;
export import simple_fwd;
import simple2;
''')

def test_module_impl_export():
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_export_module('simple', 'simple_fwd')
    converted = converter.convert_file_content(
'''#include "simple.h"
#include "simple_fwd.h"
#include "simple2.h"
''', 'simple.cpp')
    assert(converted[0].content == 
'''module simple;
import simple_fwd;
import simple2;
''')

def test_module_interface_export_A_star():
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_export_module('simple', '*')
    converted = converter.convert_file_content(
'''#include "simple_fwd.h"
#include "simple2.h"
''', 'simple.h')
    assert(converted[0].content == 
'''export module simple;
export import simple_fwd;
export import simple2;
''')

def test_module_interface_export_star_B():
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_export_module('*', 'simple2')
    converted = converter.convert_file_content(
'''#include "simple_fwd.h"
#include "simple2.h"
''', 'simple.h')
    assert(converted[0].content == 
'''export module simple;
import simple_fwd;
export import simple2;
''')

def test_module_interface_export_star_star():
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_export_module('*', '*')
    converted = converter.convert_file_content(
'''#include "simple_fwd.h"
#include "simple2.h"
''', 'simple.h')
    assert(converted[0].content == 
'''export module simple;
export import simple_fwd;
export import simple2;
''')

def test_module_interface_export_suffix():
    converter = Converter(ConvertAction.MODULES)
    converter.options.export_suffixes.append('_fwd')
    converted = converter.convert_file_content(
'''#include "simple_fwd.h"
#include "simple2.h"
#include "simple2_fwd.h"
''', 'simple.h')
    assert(converted[0].content == 
'''export module simple;
export import simple_fwd;
import simple2;
import simple2_fwd;
''')

def test_module_impl_export_suffix():
    converter = Converter(ConvertAction.MODULES)
    converter.options.export_suffixes.append('_fwd')
    converted = converter.convert_file_content(
'''#include "simple.h"
#include "simple_fwd.h"
#include "simple2.h"
''', 'simple.cpp')
    assert(converted[0].content == 
'''module simple;
import simple_fwd;
import simple2;
''')

def test_module_interface_export_suffix_named():
    converter = Converter(ConvertAction.MODULES)
    converter.options.export_suffixes.append('_fwd')
    converter.options.set_root_dir_module_name('org')
    converter.resolver.files_map.add_files_map_dict({
        'simple.h': FileEntryType.FILE,
        'simple_fwd.h': FileEntryType.FILE,
        'simple2.h': FileEntryType.FILE,
        'simple2_fwd.h': FileEntryType.FILE,
    })
    converted = converter.convert_file_content(
'''#include "simple_fwd.h"
#include "simple2.h"
#include "simple2_fwd.h"
''', 'simple.h')
    assert(converted[0].content == 
'''export module org.simple;
export import org.simple_fwd;
import org.simple2;
import org.simple2_fwd;
''')

def test_resolve_include():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('subdir/simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    assert(resolver.module_dir == PurePosixPath('subdir'))
    assert(resolver.resolve_include('simple.h', True) == PurePosixPath('simple.h'))
    assert(resolver.resolve_include('simple.h', False) is None)
    # make `simple.h` available in subdir
    resolver.parent_resolver.files_map.add_files_map_dict({
        'subdir': {
            'simple.h': FileEntryType.FILE,
        },
    })
    assert(resolver.resolve_include('simple.h', True) == PurePosixPath('subdir/simple.h'))
    assert(resolver.resolve_include('simple.h', False) is None)
    # make `simple.h` available in root
    resolver.parent_resolver.files_map.add_files_map_dict({
        'simple.h': FileEntryType.FILE,
    })
    assert(resolver.resolve_include('simple.h', False) == PurePosixPath('simple.h'))

def test_resolve_include_no_dir():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    assert(resolver.module_dir == PurePosixPath(''))
    assert(resolver.resolve_include('simple.h', True) == PurePosixPath('simple.h'))
    assert(resolver.resolve_include('simple.h', False) is None)
    # make `simple.h` available
    resolver.parent_resolver.files_map.add_files_map_dict({
        'simple.h': FileEntryType.FILE,
    })
    assert(resolver.resolve_include('simple.h', False) == PurePosixPath('simple.h'))

def test_resolve_include_to_module_name():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    assert(resolver.resolve_include_to_module_name('simple.h', True) == 'simple')
    assert(resolver.resolve_include_to_module_name('simple.h', False) is None)
    assert(resolver.resolve_include_to_module_name('subdir/simple.h', True) == 'subdir.simple')
    assert(resolver.resolve_include_to_module_name('subdir/simple.h', False) is None)
    # make `simple.h` available
    resolver.parent_resolver.files_map.add_files_map_dict({
        'simple.h': FileEntryType.FILE,
    })
    assert(resolver.resolve_include_to_module_name('simple.h', False) == 'simple')
    assert(resolver.resolve_include_to_module_name('subdir/simple.h', False) is None)
    # make `subdir/simple.h` available
    resolver.parent_resolver.files_map.add_files_map_dict({
        'subdir': {
            'simple.h': FileEntryType.FILE,
        }
    })
    assert(resolver.resolve_include_to_module_name('simple.h', False) == 'simple')
    assert(resolver.resolve_include_to_module_name('subdir/simple.h', False) == 'subdir.simple')

def test_resolve_include_to_module_name_add_modules_path_subdir():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    assert(resolver.resolve_include_to_module_name('subdir/simple.h', True) == 'subdir.simple')
    assert(resolver.resolve_include_to_module_name('subdir/simple.h', False) is None)
    resolver.options.add_modules_path('TestModule', 'subdir')
    assert(resolver.resolve_include_to_module_name('subdir/simple.h', True) == 'TestModule.simple')
    assert(resolver.resolve_include_to_module_name('subdir/simple.h', False) == 'TestModule.simple')
    assert(resolver.resolve_include_to_module_name('subdir/subdir2/simple.h', True) == 'TestModule.subdir2.simple')
    assert(resolver.resolve_include_to_module_name('subdir/subdir2/simple.h', False) == 'TestModule.subdir2.simple')

def test_resolve_include_to_module_name_add_modules_path_subdir_level2():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    assert(resolver.resolve_include_to_module_name('subdir/subdir2/simple.h', True) == 'subdir.subdir2.simple')
    assert(resolver.resolve_include_to_module_name('subdir/subdir2/simple.h', False) is None)
    resolver.options.add_modules_path('TestModule', 'subdir/subdir2')
    assert(resolver.resolve_include_to_module_name('subdir/subdir2/simple.h', True) == 'TestModule.simple')
    assert(resolver.resolve_include_to_module_name('subdir/subdir2/simple.h', False) == 'TestModule.simple')

def test_resolve_include_to_module_name_add_modules_path_subdir_level2_in_subdir():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('subdir/simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    # make `simple.h` available in subdir
    resolver.parent_resolver.files_map.add_files_map_dict({
        'subdir': {
            'subdir2': {
                'simple.h': FileEntryType.FILE,
            },
        },
    })
    assert(resolver.resolve_include_to_module_name('subdir2/simple.h', True) == 'subdir.subdir2.simple')
    assert(resolver.resolve_include_to_module_name('subdir2/simple.h', False) is None)
    resolver.options.add_modules_path('TestModule', 'subdir/subdir2')
    assert(resolver.resolve_include_to_module_name('subdir2/simple.h', True) == 'TestModule.simple')
    assert(resolver.resolve_include_to_module_name('subdir/subdir2/simple.h', True) == 'TestModule.simple')
    assert(resolver.resolve_include_to_module_name('subdir2/simple.h', False) == None)
    assert(resolver.resolve_include_to_module_name('subdir/subdir2/simple.h', False) == 'TestModule.simple')

def test_resolve_include_to_module_name_std():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    assert(resolver.resolve_include_to_module_name('vector', False) is None)
    resolver.options.add_std_module()
    assert(resolver.resolve_include_to_module_name('vector', False) == 'std')

def test_resolve_include_to_module_name_std_compat():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    assert(resolver.resolve_include_to_module_name('vector', False) is None)
    resolver.options.add_std_compat_module()
    assert(resolver.resolve_include_to_module_name('vector', False) == 'std.compat')

def test_resolve_include_to_module_name_std_w_root_name():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    assert(resolver.resolve_include_to_module_name('vector', False) is None)
    resolver.options.add_std_module()
    resolver.options.set_root_dir_module_name('TestModule')
    assert(resolver.resolve_include_to_module_name('vector', False) == 'std')

def test_resolver_convert_filename_to_module_name():
    converter = Converter(ConvertAction.MODULES)
    assert(converter.resolver.convert_filename_to_module_name(PurePosixPath('simple.cpp')) == 'simple')
    assert(converter.resolver.convert_filename_to_module_name(PurePosixPath('subdir/simple.cpp')) == 'subdir.simple')

def test_FilesMap_add_filesystem_directory():
    files_map = FilesMap()
    files_map.add_filesystem_directory(Path('test_data/subdirs/input'))
    assert(files_map.value == {
        'simple1.h': FileEntryType.FILE,
        'subdir1': {
            'simple1.h': FileEntryType.FILE,
            'simple2.h': FileEntryType.FILE,
            'subdir2': {
                'simple1.h': FileEntryType.FILE,
                'simple2.h': FileEntryType.FILE,
            },
        },
    })
    files_map.add_filesystem_directory(Path('test_data/other/input'))
    assert(files_map.value == {
        'other.txt': FileEntryType.FILE,
        'simple1.h': FileEntryType.FILE,
        'subdir1': {
            'simple1.h': FileEntryType.FILE,
            'simple2.h': FileEntryType.FILE,
            'subdir2': {
                'simple1.h': FileEntryType.FILE,
                'simple2.h': FileEntryType.FILE,
            },
        },
    })

def test_FilesMap_add_map():
    files_map = FilesMap()
    files_map.add_files_map_dict({
        'simple1.h': FileEntryType.FILE,
    })
    assert(files_map.value == {
        'simple1.h': FileEntryType.FILE,
    })
    files_map.add_files_map_dict({
        'subdir1': {
            'simple2.h': FileEntryType.FILE,
        },
    })
    assert(files_map.value == {
        'simple1.h': FileEntryType.FILE,
        'subdir1': {
            'simple2.h': FileEntryType.FILE,
        },
    })

def test_FilesResolver_resolve_in_search_path_empty_map():
    options = Options()
    files_resolver = FilesResolver(options)
    assert(files_resolver.resolve_in_search_path(Path(''), 'test', 'root.h', True) == PurePosixPath('root.h'))
    assert(files_resolver.resolve_in_search_path(Path(''), 'test', 'root.h', False) is None)
    assert(files_resolver.resolve_in_search_path(Path('subdir1'), 'test', 'simple1.h', True) == PurePosixPath('simple1.h'))
    assert(files_resolver.resolve_in_search_path(Path('subdir1'), 'test', 'simple1.h', False) is None)


def test_ModuleFilesResolver_resolve_in_search_path():
    options = Options()
    files_resolver = FilesResolver(options)
    modules_resolver = ModuleFilesResolver(files_resolver, options)
    files_map = files_resolver.files_map
    files_map.add_files_map_dict({
        'root.h': FileEntryType.FILE,
        'subdir1': {
            'simple1.h': FileEntryType.FILE,
            'subdir2': {
                'simple2.h': FileEntryType.FILE,
            },
        },
        'dir2': {
            'simple1.h': FileEntryType.FILE,
            'subdir2': {
                'simple2.h': FileEntryType.FILE,
                'simple3.h': FileEntryType.FILE,
            },
        },
    })
    modules_resolver.set_filename(Path('subdir1/test'))
    # check existing file from root
    assert(modules_resolver.resolve_include('subdir1/subdir2/simple2.h', True) == PurePosixPath('subdir1/subdir2/simple2.h'))
    assert(modules_resolver.resolve_include('subdir1/subdir2/simple2.h', False) == PurePosixPath('subdir1/subdir2/simple2.h'))
    # check existing file in relative subdir
    assert(modules_resolver.resolve_include('subdir2/simple2.h', True) == PurePosixPath('subdir1/subdir2/simple2.h'))
    assert(modules_resolver.resolve_include('subdir2/simple2.h', False) is None)
    # check missing file
    assert(modules_resolver.resolve_include('subdir2/simple3.h', True) == PurePosixPath('subdir2/simple3.h'))
    assert(modules_resolver.resolve_include('subdir2/simple3.h', False) is None)
    # add search path in another dir
    options.search_path.append('dir2')
    # check file existing in relative subdir and search path
    assert(modules_resolver.resolve_include('subdir2/simple2.h', True) == PurePosixPath('subdir1/subdir2/simple2.h'))
    assert(modules_resolver.resolve_include('subdir2/simple2.h', False) == PurePosixPath('dir2/subdir2/simple2.h'))
    # check file existing in search path but missing in relative subdir
    assert(modules_resolver.resolve_include('subdir2/simple3.h', True) == PurePosixPath('dir2/subdir2/simple3.h'))
    assert(modules_resolver.resolve_include('subdir2/simple3.h', False) == PurePosixPath('dir2/subdir2/simple3.h'))
    # check file missing in relative subdir and search path
    assert(modules_resolver.resolve_include('subdir2/simple4.h', True) == PurePosixPath('subdir2/simple4.h'))
    assert(modules_resolver.resolve_include('subdir2/simple4.h', False) is None)

def test_FilesResolver_convert_filename_to_module_name():
    options = Options()
    files_resolver = FilesResolver(options)
    files_map = files_resolver.files_map
    files_map.add_files_map_dict({
        'root.h': FileEntryType.FILE,
        'subdir1': {
            'simple1.h': FileEntryType.FILE,
            'subdir2': {
                'simple2.h': FileEntryType.FILE,
            },
        },
        'dir2': {
            'simple1.h': FileEntryType.FILE,
            'subdir2': {
                'simple2.h': FileEntryType.FILE,
                'simple3.h': FileEntryType.FILE,
            },
        },
    })
    assert(files_resolver.convert_filename_to_module_name(PurePosixPath('root.h')) == 'root')
    assert(files_resolver.convert_filename_to_module_name(PurePosixPath('subdir1/simple1.h')) == 'subdir1.simple1')
    assert(files_resolver.convert_filename_to_module_name(PurePosixPath('missing.h')) == 'missing')
    options.set_root_dir_module_name('org')
    assert(files_resolver.convert_filename_to_module_name(PurePosixPath('root.h')) == 'org.root')
    assert(files_resolver.convert_filename_to_module_name(PurePosixPath('subdir1/simple1.h')) == 'org.subdir1.simple1')
    assert(files_resolver.convert_filename_to_module_name(PurePosixPath('missing.h')) == 'missing')

def test_FilesResolver_get_source_content_type():
    options = Options()
    files_resolver = FilesResolver(options)
    assert(files_resolver.get_source_content_type(ConvertAction.MODULES,  Path('test.h')) == ContentType.HEADER)
    assert(files_resolver.get_source_content_type(ConvertAction.MODULES,  Path('test.hpp')) == ContentType.OTHER)
    assert(files_resolver.get_source_content_type(ConvertAction.MODULES,  Path('test.cpp')) == ContentType.CXX)
    assert(files_resolver.get_source_content_type(ConvertAction.MODULES,  Path('test.cxx')) == ContentType.OTHER)
    # first use -- replace default
    options.add_module_action_ext_type(".hpp", ContentType.HEADER)
    assert(files_resolver.get_source_content_type(ConvertAction.MODULES,  Path('test.h')) == ContentType.OTHER)
    assert(files_resolver.get_source_content_type(ConvertAction.MODULES,  Path('test.hpp')) == ContentType.HEADER)
    # subsequent use -- append (+ no dot)
    options.add_module_action_ext_type("h", ContentType.HEADER)
    assert(files_resolver.get_source_content_type(ConvertAction.MODULES,  Path('test.h')) == ContentType.HEADER)
    assert(files_resolver.get_source_content_type(ConvertAction.MODULES,  Path('test.hpp')) == ContentType.HEADER)
    assert(files_resolver.get_source_content_type(ConvertAction.MODULES,  Path('test.cpp')) == ContentType.CXX)
    assert(files_resolver.get_source_content_type(ConvertAction.MODULES,  Path('test.cxx')) == ContentType.OTHER)

    # first use -- replace default
    options.add_module_action_ext_type(".cxx", ContentType.CXX)
    assert(files_resolver.get_source_content_type(ConvertAction.MODULES,  Path('test.cpp')) == ContentType.OTHER)
    assert(files_resolver.get_source_content_type(ConvertAction.MODULES,  Path('test.cxx')) == ContentType.CXX)
    # subsequent use -- append
    options.add_module_action_ext_type(".cpp", ContentType.CXX)
    assert(files_resolver.get_source_content_type(ConvertAction.MODULES,  Path('test.cpp')) == ContentType.CXX)
    assert(files_resolver.get_source_content_type(ConvertAction.MODULES,  Path('test.cxx')) == ContentType.CXX)
    assert(files_resolver.get_source_content_type(ConvertAction.MODULES,  Path('test.h')) == ContentType.HEADER)
    assert(files_resolver.get_source_content_type(ConvertAction.MODULES,  Path('test.hpp')) == ContentType.HEADER)

def test_FilesResolver_convert_filename_to_content_type():
    options = Options()
    files_resolver = FilesResolver(options)
    assert(files_resolver.convert_filename_to_content_type(Path('test.h'), ContentType.MODULE_INTERFACE) == 'test.cppm')
    assert(files_resolver.convert_filename_to_content_type(Path('test.cpp'), ContentType.MODULE_IMPL) == 'test.cpp')
    options.set_output_content_type_to_ext(ContentType.MODULE_INTERFACE, '.ixx')
    options.set_output_content_type_to_ext(ContentType.MODULE_IMPL, 'cxx')
    assert(files_resolver.convert_filename_to_content_type(Path('test.h'), ContentType.MODULE_INTERFACE) == 'test.ixx')
    assert(files_resolver.convert_filename_to_content_type(Path('test.cpp'), ContentType.MODULE_IMPL) == 'test.cxx')

def test_module_impl_include_local_self_header_subdir():
    converter = Converter(ConvertAction.MODULES)
    converter.resolver.files_map.add_files_map_dict({
        'subdir': {
            'local_include.h': FileEntryType.FILE,
            'simple.h': FileEntryType.FILE,
        },
    })
    converted = converter.convert_file_content(
'''#include "simple.h"
#include "local_include.h"
''', 'subdir/simple.cpp')
    assert(converted[0].content == 
'''module subdir.simple;
import subdir.local_include;
''')

def test_module_impl_include_local_self_header_subdir_prefix():
    converter = Converter(ConvertAction.MODULES)
    converter.resolver.files_map.add_files_map_dict({
        'prefix': {
            'subdir': {
                'local_include.h': FileEntryType.FILE,
                'simple.h': FileEntryType.FILE,
            },
        },
    })
    converted = converter.convert_file_content(
'''#include "simple.h"
#include "local_include.h"
''', 'prefix/subdir/simple.cpp')
    assert(converted[0].content == 
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
export {

namespace TestNS
{
namespace Test
{
class TestClass
{
};
} // namespace Test
} // namespace TestNS

} // export
''')

def test_module_interface_compat_header_empty():
    converter = Converter(ConvertAction.MODULES)
    file_options = FileOptions()
    file_options.convert_as_compat = True
    converted = converter.convert_file_content(
'''''', 'empty.h', file_options)
    assert(converted == [
        FileContent("empty.cppm", ContentType.MODULE_INTERFACE,
'''#ifndef CXX_COMPAT_HEADER
export module empty;
#endif
'''),
        FileContent("empty.h", ContentType.HEADER,
'''#pragma once
#ifndef CXX_COMPAT_HEADER
#define CXX_COMPAT_HEADER
#include "empty.cppm"
#undef CXX_COMPAT_HEADER
#else
#include "empty.cppm"
#endif
'''),
])

def test_module_interface_compat_header():
    converter = Converter(ConvertAction.MODULES)
    file_options = FileOptions()
    file_options.convert_as_compat = True
    converted = converter.convert_file_content(
'''#include "local_include.h"
''', 'simple.h', file_options)
    assert(converted == [
        FileContent("simple.cppm", ContentType.MODULE_INTERFACE,
'''#ifndef CXX_COMPAT_HEADER
module;
#else
#pragma once
#include "local_include.h"
#endif
#ifndef CXX_COMPAT_HEADER
export module simple;
#endif
#ifndef CXX_COMPAT_HEADER
import local_include;
#endif
'''),
        FileContent("simple.h", ContentType.HEADER,
'''#pragma once
#ifndef CXX_COMPAT_HEADER
#define CXX_COMPAT_HEADER
#include "simple.cppm"
#undef CXX_COMPAT_HEADER
#else
#include "simple.cppm"
#endif
'''),
])

def test_module_interface_compat_header_w_system_includes():
    converter = Converter(ConvertAction.MODULES)
    file_options = FileOptions()
    file_options.convert_as_compat = True
    converted = converter.convert_file_content(
'''#include "local_include.h"
#include <string>
''', 'simple.h', file_options)
    assert(converted == [
        FileContent("simple.cppm", ContentType.MODULE_INTERFACE,
'''#ifndef CXX_COMPAT_HEADER
module;
#else
#pragma once
#include "local_include.h"
#include <string>
#endif
#include <string>
#ifndef CXX_COMPAT_HEADER
export module simple;
#endif
#ifndef CXX_COMPAT_HEADER
import local_include;
#endif
'''),
        FileContent("simple.h", ContentType.HEADER,
'''#pragma once
#ifndef CXX_COMPAT_HEADER
#define CXX_COMPAT_HEADER
#include "simple.cppm"
#undef CXX_COMPAT_HEADER
#else
#include "simple.cppm"
#endif
'''),
])

def test_module_impl_compat():
    converter = Converter(ConvertAction.MODULES)
    file_options = FileOptions()
    file_options.convert_as_compat = True
    converted = converter.convert_file_content(
'''#include "local_include.h"
''', 'simple.cpp', file_options)
    assert(converted == [
        FileContent("simple.cpp", ContentType.MODULE_IMPL,
'''import local_include;
'''),
])


@pytest.fixture(scope="function")
def dir_simple(tmp_path_factory: pytest.TempPathFactory):
    path = tmp_path_factory.mktemp("simple")
    return path

def assert_files(expected_dir: Path, result_dir: Path, expected_files: list[str]):
    result_files: set[str] = set()
    for (root, _, files) in os.walk(result_dir):
        if 'build' in Path(root).parts:
            continue
        relative_root = Path(os.path.relpath(root, result_dir))
        for name in files:
            result_files.add(relative_root.joinpath(name).as_posix())
    assert(result_files == set(expected_files))

    for filename in expected_files:
        result_path = result_dir.joinpath(filename)
        print('assert_files filename:', filename)
        assert os.path.exists(result_path)
        with open(expected_dir.joinpath(filename)) as expected_file:
            expected_content = expected_file.read()
        with open(result_dir.joinpath(filename)) as result_file:
            result_content = result_file.read()
        assert(result_content == expected_content)

def run_cmake_test(dir_simple: Path, preset: str):
    configure_cmd = ["cmake", "--preset", preset, "--fresh"]
    result_configure = subprocess.run(
        configure_cmd,
        cwd=dir_simple,
        capture_output=True,
        text=True
    )
    
    assert result_configure.returncode == 0, (
        f"CMake configure failed for preset {preset}:\n"
        f"Command: {' '.join(configure_cmd)}\n"
        f"STDOUT:\n{result_configure.stdout}\n"
        f"STDERR:\n{result_configure.stderr}"
    )
    
    build_cmd = ["cmake", "--build", "--preset", preset]
    result_build = subprocess.run(
        build_cmd,
        cwd=dir_simple,
        capture_output=True,
        text=True
    )
    
    assert result_build.returncode == 0, (
        f"CMake build failed for preset {preset}:\n"
        f"Command: {' '.join(build_cmd)}\n"
        f"STDOUT:\n{result_build.stdout}\n"
        f"STDERR:\n{result_build.stderr}"
    )

CMAKE_TEST_CASES = [
    "test-clang-20",
    "test-clang-21",
    "test-gcc-15"
]


def test_dir_simple(dir_simple: Path):
    data_directory = Path('test_data/simple')
    convert_directory(ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'simple.cppm',
        'simple.cpp',
        'main.cpp',
        'CMakeLists.txt',
        'CMakePresets.json',
    ])

@pytest.mark.slow
@pytest.mark.parametrize("preset", CMAKE_TEST_CASES)
def test_dir_simple_cmake(dir_simple: Path, preset: str):
    data_directory = Path('test_data/simple')
    convert_directory(ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'simple.cppm',
        'simple.cpp',
        'main.cpp',
        'CMakeLists.txt',
        'CMakePresets.json',
    ])
    
    run_cmake_test(dir_simple, preset)


def test_dir_simple_std(dir_simple: Path):
    data_directory = Path('test_data/simple_std')
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_std_module()
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'simple.cppm',
        'simple.cpp',
    ])

def test_dir_named1(dir_simple: Path):
    data_directory = Path('test_data/named1')
    converter = Converter(ConvertAction.MODULES)
    converter.options.set_root_dir_module_name('org')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    # convert_directory(ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'simple.cppm',
        'simple.cpp',
    ])

def test_dir_prefix(dir_simple: Path):
    data_directory = Path('test_data/prefix')
    converter = Converter(ConvertAction.MODULES)
    input_dir = data_directory.joinpath('input')
    converter.options.root_dir = input_dir
    converter.convert_directory(input_dir.joinpath('subdir'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'subdir/simple.cppm',
        'subdir/simple.cpp',
    ])

def test_dir_prefix_named(dir_simple: Path):
    data_directory = Path('test_data/prefix_named')
    converter = Converter(ConvertAction.MODULES)
    input_dir = data_directory.joinpath('input')
    converter.options.root_dir = input_dir
    converter.options.set_root_dir_module_name('org')
    converter.convert_directory(input_dir.joinpath('subdir'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'subdir/local_include.cppm',
        'subdir/simple.cppm',
        'subdir/simple.cpp',
    ])

def test_dir_modules_path(dir_simple: Path):
    data_directory = Path('test_data/modules_path')
    converter = Converter(ConvertAction.MODULES)
    input_dir = data_directory.joinpath('input')
    converter.options.root_dir = input_dir
    converter.options.add_modules_path('org', '') # same as `.set_root_dir_module_name('org')`
    converter.options.add_modules_path('org2', 'dir2')
    converter.convert_directory(input_dir, dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'subdir/local_include.cppm',
        'subdir/simple.cppm',
        'subdir/simple.cpp',
        'dir2/local_include.cppm',
        'dir2/simple.cppm',
        'dir2/simple.cpp',
    ])

def test_dir_compat(dir_simple: Path):
    data_directory = Path('test_data/compat')
    converter = Converter(ConvertAction.MODULES)
    converter.options.compat_patterns = [
        'simple.h',
        'simple.cpp',
        'subdir/*',
    ]
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'simple.h',
        'simple.cppm',
        'simple.cpp',
        'subdir/simple2.h',
        'subdir/simple2.cppm',
        'subdir/simple2.cpp',
    ])

def test_dir_other(dir_simple: Path):
    data_directory = Path('test_data/other')
    convert_directory(ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'other.txt',
    ])

def test_dir_two(dir_simple: Path):
    data_directory = Path('test_data/two')
    convert_directory(ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'simple1.cppm',
        'simple2.cppm',
    ])

def test_dir_subdir(dir_simple: Path):
    data_directory = Path('test_data/subdir')
    convert_directory(ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'subdir1/simple1.cppm',
        'subdir1/simple2.cppm',
    ])

def test_dir_skip(dir_simple: Path):
    data_directory = Path('test_data/skip')
    converter = Converter(ConvertAction.MODULES)
    converter.options.skip_patterns = [
        'skipdir',
        'subdir1/simple2.h',
        'subdir1/skipsubdir',
    ]
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'subdir1/simple1.cppm',
    ])

def test_dir_subdirs(dir_simple: Path):
    data_directory = Path('test_data/subdirs')
    convert_directory(ConvertAction.MODULES, data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'simple1.cppm',
        'subdir1/simple1.cppm',
        'subdir1/simple2.cppm',
        'subdir1/subdir2/simple1.cppm',
        'subdir1/subdir2/simple2.cppm',
    ])

def test_dir_subdirs_rooted(dir_simple: Path):
    data_directory = Path('test_data/subdirs_rooted')
    converter = Converter(ConvertAction.MODULES)
    input_dir = data_directory.joinpath('input')
    converter.options.root_dir = input_dir
    converter.convert_directory(input_dir.joinpath('subdir'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'subdir/simple1.cppm',
        'subdir/subdir1/simple1.cppm',
        'subdir/subdir1/simple2.cppm',
        'subdir/subdir1/use_relative_include.cppm',
        'subdir/subdir1/use_relative_include_missing.cppm',
        'subdir/subdir1/use_search_path_include_existing.cppm',
        'subdir/subdir1/subdir2/simple1.cppm',
        'subdir/subdir1/subdir2/simple1.cpp',
        'subdir/subdir1/subdir2/simple2.cppm',
    ])

def test_dir_subdirs_rooted_brackets(dir_simple: Path):
    data_directory = Path('test_data/subdirs_rooted_brackets')
    converter = Converter(ConvertAction.MODULES)
    input_dir = data_directory.joinpath('input')
    converter.options.root_dir = input_dir
    converter.convert_directory(input_dir.joinpath('subdir'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'subdir/simple1.cppm',
        'subdir/subdir1/simple1.cppm',
        'subdir/subdir1/simple2.cppm',
        'subdir/subdir1/use_relative_include.cppm',
        'subdir/subdir1/use_relative_include_missing.cppm',
        'subdir/subdir1/use_search_path_include_existing.cppm',
        'subdir/subdir1/subdir2/simple1.cppm',
        'subdir/subdir1/subdir2/simple1.cpp',
        'subdir/subdir1/subdir2/simple2.cppm',
    ])

def test_dir_header(dir_simple: Path):
    data_directory = Path('test_data/header')
    converter = Converter(ConvertAction.MODULES)
    converter.options.always_include_names.append('simple.h')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'simple.h',
        'simple.cpp',
    ])

def test_dir_header_subdir(dir_simple: Path):
    data_directory = Path('test_data/header_subdir')
    converter = Converter(ConvertAction.MODULES)
    converter.options.always_include_names.append('subdir/**')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'subdir/simple.h',
        'subdir/simple.cpp',
    ])

def test_dir_header_subdir_nested(dir_simple: Path):
    data_directory = Path('test_data/header_subdir_nested')
    converter = Converter(ConvertAction.MODULES)
    converter.options.always_include_names.append('subdir/**')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'subdir/nested/simple.h',
        'subdir/nested/simple.cpp',
    ])

def test_dir_twice(dir_simple: Path):
    data_directory = Path('test_data/twice')
    converter = Converter(ConvertAction.MODULES)
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'simple.cppm',
        'simple.cpp',
        'other.txt',
    ])
    assert(converter.all_files == 3)
    assert(converter.convertable_files == 2)
    assert(converter.converted_files == 2)
    assert(converter.copied_files == 1)
    converter = Converter(ConvertAction.MODULES)
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert(converter.all_files == 3)
    assert(converter.convertable_files == 2)
    assert(converter.converted_files == 0)
    assert(converter.copied_files == 0)

def test_dir_inext(dir_simple: Path):
    data_directory = Path('test_data/inext')
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_module_action_ext_type('.hpp', ContentType.HEADER)
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'simple.cppm',
        'simple2.h',
        'simple.cpp',
    ])

def test_dir_outext(dir_simple: Path):
    data_directory = Path('test_data/outext')
    converter = Converter(ConvertAction.MODULES)
    converter.options.set_output_content_type_to_ext(ContentType.MODULE_INTERFACE, '.ixx')
    converter.options.set_output_content_type_to_ext(ContentType.MODULE_IMPL, '.cxx')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'simple.ixx',
        'simple.cxx',
        'simple2.hpp',
    ])

def test_add_join_configuration():
    options = Options()
    options.add_join_configuration('mymodule', 'subdir/*')
    assert(options.join_configurations == {'subdir/*': 'mymodule'})

def test_add_join_configuration_star():
    options = Options()
    options.add_join_configuration('mymodule', '*')
    assert(options.join_configurations == {'*': 'mymodule'})

    files_resolver = FilesResolver(options)
    result = files_resolver.filename_to_module_name(PurePosixPath('test.h'), None)
    assert(result == 'mymodule:test')

    result = files_resolver.filename_to_module_name(PurePosixPath('subdir/test.h'), None)
    assert(result == 'mymodule:subdir.test')

def test_filename_to_module_name_with_join_configuration():
    options = Options()
    files_resolver = FilesResolver(options)
    result = files_resolver.filename_to_module_name(PurePosixPath('subdir/test.h'), None)
    assert(result == 'subdir.test')

    options.join_configurations = {'subdir/*': 'mymodule'}
    files_resolver = FilesResolver(options)
    result = files_resolver.filename_to_module_name(PurePosixPath('subdir/test.h'), None)
    assert(result == 'mymodule:test')

    result = files_resolver.filename_to_module_name(PurePosixPath('other/test.h'), None)
    assert(result == 'other.test')

def test_set_root_dir_module_name_and_add_join_configuration():
    converter = Converter(ConvertAction.MODULES)
    converter.options.set_root_dir_module_name('org')
    converter.options.add_join_configuration('org.mymodule', 'subdir/*')
    converter.resolver.files_map.add_files_map_dict({
        'subdir': {
            'test.h': FileEntryType.FILE,
        },
        'other': {
            'test.h': FileEntryType.FILE,
        },
    })
    
    result1 = converter.resolver.convert_filename_to_module_name(PurePosixPath('subdir/test.h'))
    assert(result1 == 'org.mymodule:test')
    
    result2 = converter.resolver.convert_filename_to_module_name(PurePosixPath('other/test.h'))
    assert(result2 == 'org.other.test')

def test_dir_partitions(dir_simple: Path):
    data_directory = Path('test_data/partitions')
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_join_configuration('mymodule', '*')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'part1.cppm',
        'part2.cppm',
        'subdir/part3.cppm',
        'mymodule.cppm',
    ])

def test_dir_partitions_local_import(dir_simple: Path):
    data_directory = Path('test_data/partitions_local_import')
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_join_configuration('mymodule', '*')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'part1.cppm',
        'part2.cppm',
        'subdir/part3.cppm',
        'mymodule.cppm',
    ])

def test_dir_custom_join_configurations(dir_simple: Path):
    data_directory = Path('test_data/custom_join_test')
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_join_configuration('mymodule1', 'subdir1/*')
    converter.options.add_join_configuration('mymodule2', 'subdir2/*')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'subdir1/simple.cppm',
        'subdir2/simple.cpp',
        'subdir2/simple.cppm',
        'mymodule1.cppm',
        'mymodule2.cppm',
    ])

def test_dir_partitions_header_match(dir_simple: Path):
    data_directory = Path('test_data/partitions_header_match')
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_join_configuration('mymodule', 'mymodule/*')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'mymodule.cppm',
        'mymodule/part1.cppm',
        'mymodule/part2.cppm',
    ])

def test_resolve_include_to_module_name_use_full_name_true():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    resolver.set_module_name('test_module')
    resolver.parent_resolver.files_map.add_files_map_dict({
        'simple.h': FileEntryType.FILE,
    })
    assert(resolver.resolve_include_to_module_name('simple.h', False, True) == 'simple')

def test_resolve_include_to_module_name_use_full_name_false_same_external_module():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    resolver.set_module_name('mymodule:partition1')
    resolver.parent_resolver.files_map.add_files_map_dict({
        'simple.h': FileEntryType.FILE,
    })
    resolver.parent_resolver.files_map.add_files_map_dict({
        'subdir': {
            'simple2.h': FileEntryType.FILE,
        }
    })
    resolver.options.add_join_configuration('mymodule', 'subdir/*')
    assert(resolver.resolve_include_to_module_name('subdir/simple2.h', False, False) == ':simple2')

def test_resolve_include_to_module_name_use_full_name_false_different_external_module():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    resolver.set_module_name('mymodule:partition1')
    resolver.parent_resolver.files_map.add_files_map_dict({
        'simple.h': FileEntryType.FILE,
    })
    resolver.parent_resolver.files_map.add_files_map_dict({
        'otherdir': {
            'simple2.h': FileEntryType.FILE,
        }
    })
    resolver.options.add_join_configuration('othermodule', 'otherdir/*')
    assert(resolver.resolve_include_to_module_name('otherdir/simple2.h', False, False) == 'othermodule')

def test_resolve_include_to_module_name_use_full_name_false_no_partition():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    resolver.set_module_name('mymodule')
    resolver.parent_resolver.files_map.add_files_map_dict({
        'subdir': {
            'simple.h': FileEntryType.FILE,
        }
    })
    resolver.options.add_join_configuration('mymodule', 'subdir/*')
    assert(resolver.resolve_include_to_module_name('subdir/simple.h', False, False) == ':simple')

def test_resolve_include_to_module_name_use_full_name_false_no_current_module():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    resolver.parent_resolver.files_map.add_files_map_dict({
        'simple.h': FileEntryType.FILE,
    })
    assert(resolver.resolve_include_to_module_name('simple.h', False, False) == 'simple')

def test_resolve_include_to_module_name_use_full_name_false_std_module():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    resolver.set_module_name('mymodule:partition1')
    resolver.options.add_std_module()
    assert(resolver.resolve_include_to_module_name('vector', False, False) == 'std')

def test_resolve_include_to_module_name_use_full_name_false_std_compat_module():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    resolver.set_module_name('mymodule:partition1')
    resolver.options.add_std_compat_module()
    assert(resolver.resolve_include_to_module_name('vector', False, False) == 'std.compat')

# Tests for cycle detection function

def test_find_cycles_no_cycles():
    """Test graph without cycles"""
    graph: dict[str, set[str]] = {
        'A': {'B', 'C'},
        'B': {'D'},
        'C': {'D'},
        'D': set()
    }
    cycles = find_cycles(graph)
    assert cycles == []

def test_find_cycles_simple_cycle():
    """Test simple cycle"""
    graph: dict[str, set[str]] = {
        'A': {'B'},
        'B': {'C'},
        'C': {'A'}
    }
    cycles = find_cycles(graph)
    assert len(cycles) == 1
    assert set(cycles[0]) == {'A', 'B', 'C'}

def test_find_cycles_self_reference():
    """Test self-reference cycle"""
    graph: dict[str, set[str]] = {
        'A': {'A'},
        'B': {'C'},
        'C': set()
    }
    cycles = find_cycles(graph)
    # Self-references should be skipped
    assert len(cycles) == 0

def test_find_cycles_complex_cycles():
    """Test complex cycles"""
    graph: dict[str, set[str]] = {
        'A': {'B', 'C'},
        'B': {'D'},
        'C': {'D', 'E'},
        'D': {'A'},  # Creates cycles A->B->D->A and A->C->D->A
        'E': {'F'},
        'F': {'C'}   # Creates cycle C->E->F->C
    }
    cycles = find_cycles(graph)
    assert len(cycles) == 2
    
    # Check that both cycles are found
    cycle_sets = [set(cycle) for cycle in cycles]
    # The algorithm may find either A->B->D->A or A->C->D->A cycle
    # Both are valid representations of the same cycle in this graph
    assert {'A', 'B', 'D'} in cycle_sets or {'A', 'C', 'D'} in cycle_sets
    assert {'C', 'E', 'F'} in cycle_sets

def test_find_cycles_disconnected_components():
    """Test disconnected components"""
    graph: dict[str, set[str]] = {
        'A': {'B'},
        'B': {'C'},
        'C': {'A'},  # First cycle
        'D': {'E'},
        'E': {'F'},
        'F': {'D'},  # Second cycle
        'G': set()   # Isolated node
    }
    cycles = find_cycles(graph)
    assert len(cycles) == 2
    
    # Check that both cycles are found
    cycle_sets = [set(cycle) for cycle in cycles]
    assert {'A', 'B', 'C'} in cycle_sets
    assert {'D', 'E', 'F'} in cycle_sets

def test_dir_circular_dependencies(dir_simple: Path):
    """Test for detecting circular dependencies in directory"""
    data_directory = Path('test_data/circular')
    converter = Converter(ConvertAction.MODULES)
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)
    
    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'moduleA.cppm',
        'moduleB.cppm',
        'moduleC.cppm',
    ])

    assert len(converter.circular_dependencies) == 1

    cycle = converter.circular_dependencies[0]
    expected_modules = {'moduleA', 'moduleB', 'moduleC'}
    assert set(cycle) == expected_modules


def test_dir_circular_dependencies_self(dir_simple: Path):
    """Test that dependency between implementation and interface of the same module is not counted as circular"""
    data_directory = Path('test_data/circular_dependency_self')
    converter = Converter(ConvertAction.MODULES)
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)

    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'moduleA.cppm',
        'moduleA.cpp',
    ])

    assert len(converter.circular_dependencies) == 0


def test_dir_circular_dependencies_partitions(dir_simple: Path):
    """Test for detecting circular dependencies in partitions"""
    data_directory = Path('test_data/circular_partitions')
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_join_configuration('mymodule', '*')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)

    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'part1.cppm',
        'part2.cppm',
        'part3.cppm',
        'mymodule.cppm',
    ])

    assert len(converter.circular_dependencies) == 1

    cycle = converter.circular_dependencies[0]
    expected_modules = {'mymodule:part1', 'mymodule:part2', 'mymodule:part3'}
    assert set(cycle) == expected_modules


def test_dir_circular_dependencies_partitions_impl(dir_simple: Path):
    """Test for detecting circular dependencies in partitions implementation"""
    data_directory = Path('test_data/circular_partitions_impl')
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_join_configuration('mymodule', '*')
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)

    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'part1.cppm',
        'part2.cppm',
        'part1.cpp',
        'part2.cpp',
        'mymodule.cppm',
    ])

    assert len(converter.circular_dependencies) == 1

    cycle = converter.circular_dependencies[0]
    expected_modules = {'mymodule:part1', 'mymodule:part2'}
    assert set(cycle) == expected_modules

def test_dir_circular_dependencies_impl(dir_simple: Path):
    """Test for detecting circular dependencies implementation without partitions"""
    data_directory = Path('test_data/circular_impl')
    converter = Converter(ConvertAction.MODULES)
    converter.convert_directory(data_directory.joinpath('input'), dir_simple)

    assert_files(data_directory.joinpath('expected'), dir_simple, [
        'moduleA.cppm',
        'moduleB.cppm',
        'moduleC.cppm',
        'moduleA.cpp',
        'moduleB.cpp',
        'moduleC.cpp',
    ])

    assert len(converter.circular_dependencies) == 1

    cycle = converter.circular_dependencies[0]
    expected_modules = {'moduleA', 'moduleB', 'moduleC'}
    assert set(cycle) == expected_modules
