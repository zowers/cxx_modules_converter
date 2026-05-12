from cxx_modules_converter_lib import (
    ConvertAction,
    Converter,
    FileEntryType,
    convert_file_content,
)


def test_module_impl_include_local():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "local_include.h"
''',
        'simple.cpp',
    )
    assert converted == '''import local_include;
'''


def test_module_impl_include_system():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include <vector>
''',
        'simple.cpp',
    )
    assert converted == '''#include <vector>
'''


def test_module_impl_include_self_header():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "simple.h"
''',
        'simple.cpp',
    )
    assert converted == '''module simple;
'''


def test_module_impl_include_self_header_and_system():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "simple.h"
#include <vector>
''',
        'simple.cpp',
    )
    assert converted == '''module;
#include <vector>
module simple;
'''


def test_module_impl_include_self_header_and_system_and_local():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "simple.h"
#include "local_include.h"
#include <vector>
''',
        'simple.cpp',
    )
    assert converted == '''module;
#include <vector>
module simple;
import local_include;
'''


def test_module_impl_include_self_header_and_system_and_local_and_assert_h():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "simple.h"
#include "local_include.h"
#include "assert.h"
#include <vector>
''',
        'simple.cpp',
    )
    assert converted == '''module;
#include "assert.h"
#include <vector>
module simple;
import local_include;
'''


def test_module_impl_export():
    converter = Converter(ConvertAction.MODULES)
    converter.options.add_export_module('simple', 'simple_fwd')
    converted = converter.convert_file_content(
        '''#include "simple.h"
#include "simple_fwd.h"
#include "simple2.h"
''',
        'simple.cpp',
    )
    assert converted[0].content == '''module simple;
import simple_fwd;
import simple2;
'''


def test_module_impl_export_suffix():
    converter = Converter(ConvertAction.MODULES)
    converter.options.export_suffixes.append('_fwd')
    converted = converter.convert_file_content(
        '''#include "simple.h"
#include "simple_fwd.h"
#include "simple2.h"
''',
        'simple.cpp',
    )
    assert converted[0].content == '''module simple;
import simple_fwd;
import simple2;
'''


def test_module_impl_include_local_self_header_subdir():
    converter = Converter(ConvertAction.MODULES)
    converter.resolver.files_map.add_files_map_dict(
        {
            'subdir': {
                'local_include.h': FileEntryType.FILE,
                'simple.h': FileEntryType.FILE,
            },
        }
    )
    converted = converter.convert_file_content(
        '''#include "simple.h"
#include "local_include.h"
''',
        'subdir/simple.cpp',
    )
    assert converted[0].content == '''module subdir.simple;
import subdir.local_include;
'''


def test_module_impl_include_local_self_header_subdir_prefix():
    converter = Converter(ConvertAction.MODULES)
    converter.resolver.files_map.add_files_map_dict(
        {
            'prefix': {
                'subdir': {
                    'local_include.h': FileEntryType.FILE,
                    'simple.h': FileEntryType.FILE,
                },
            },
        }
    )
    converted = converter.convert_file_content(
        '''#include "simple.h"
#include "local_include.h"
''',
        'prefix/subdir/simple.cpp',
    )
    assert converted[0].content == '''module prefix.subdir.simple;
import prefix.subdir.local_include;
'''
