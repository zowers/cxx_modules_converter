from cxx_modules_converter_lib import (
    ConvertAction,
    Converter,
    FileEntryType,
    convert_file_content,
)


def test_module_empty():
    converted = convert_file_content(ConvertAction.MODULES, '''''', 'simple.h')
    assert converted == '''export module simple;
'''


def test_module_include_system():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include <vector>
''',
        'simple.h',
    )
    assert converted == '''module;
#include <vector>
export module simple;
'''


def test_module_include_local():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "local_include.h"
''',
        'simple.h',
    )
    assert converted == '''export module simple;
import local_include;
'''


def test_module_include_system_w_inline_comment():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include <vector>    // inline comment
''',
        'simple.h',
    )
    assert converted == '''module;
#include <vector>    // inline comment
export module simple;
'''


def test_module_include_local_w_inline_comment():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "local_include.h"   // inline comment
''',
        'simple.h',
    )
    assert converted == '''export module simple;
import local_include;   // inline comment
'''


def test_module_include_system_w_left_padding():
    converted = convert_file_content(
        ConvertAction.MODULES,
        ''' # include <vector>
''',
        'simple.h',
    )
    assert converted == '''module;
 # include <vector>
export module simple;
'''


def test_module_include_local_w_left_padding():
    converted = convert_file_content(
        ConvertAction.MODULES,
        ''' # include "local_include.h"
''',
        'simple.h',
    )
    assert converted == '''export module simple;
  import local_include;
'''


def test_module_include_system_ifdef():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "local_include.h"
#ifdef FLAG
 # include <vector>
#endif // FLAG
''',
        'simple.h',
    )
    assert converted == '''module;
#ifdef FLAG
 # include <vector>
#endif // FLAG
export module simple;
import local_include;
'''


def test_module_include_system_ifdef_and_content():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "local_include.h"
#ifdef FLAG
 # include <vector>
#endif // FLAG
namespace TestNS {}
''',
        'simple.h',
    )
    assert converted == '''module;
#ifdef FLAG
 # include <vector>
#endif // FLAG
export module simple;
import local_include;
export {
namespace TestNS {}
} // export
'''


def test_module_include_local_ifdef():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "local_include.h"
#ifdef FLAG
 # include "local_include_2.h"
#endif // FLAG
''',
        'simple.h',
    )
    assert converted == '''export module simple;
import local_include;
#ifdef FLAG
  import local_include_2;
#endif // FLAG
'''


def test_module_include_local_ifdef_and_content():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "local_include.h"
#ifdef FLAG
 # include "local_include_2.h"
#endif // FLAG
namespace TestNS {}
''',
        'simple.h',
    )
    assert converted == '''export module simple;
import local_include;
#ifdef FLAG
  import local_include_2;
#endif // FLAG
export {
namespace TestNS {}
} // export
'''


def test_module_include_system_ifdef_and_content_w_newlines():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "local_include.h"

#ifdef FLAG

 # include <vector>

#endif // FLAG

namespace TestNS {}
''',
        'simple.h',
    )
    assert converted == '''module;

#ifdef FLAG

 # include <vector>

#endif // FLAG
export module simple;
import local_include;
export {

namespace TestNS {}
} // export
'''


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
''',
        'simple.h',
    )
    assert converted == '''module;
#ifdef FLAG1
 # include <vector>
#endif // FLAG1
#ifdef FLAG2
 # include <string>
#endif // FLAG2
export module simple;
import local_include;
'''


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
''',
        'simple.h',
    )
    assert converted == '''export module simple;
import local_include;
#ifdef FLAG1
  import local_include_2;
#endif // FLAG1
#ifdef FLAG2
  import local_include_3;
#endif // FLAG2
'''


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
''',
        'simple.h',
    )
    assert converted == '''module;
#ifdef FLAG1
 # include <vector>
#elif FLAG2
 # include <string>
#else // FLAG2
 # include <map>
#endif // FLAG2
export module simple;
import local_include;
'''


def test_module_include_pragma_once():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#pragma once
#include "local_include.h"
#include <vector>
''',
        'simple.h',
    )
    assert converted == '''module;
#include <vector>
export module simple;
// #pragma once
import local_include;
'''


def test_module_include_system_pragma_define():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "local_include.h"
#define FLAG
#error "error"
#pragma test
#warning "warning"
#include <vector>
''',
        'simple.h',
    )
    assert converted == '''module;
#define FLAG
#error "error"
#pragma test
#warning "warning"
#include <vector>
export module simple;
import local_include;
'''


def test_module_include_local_and_system_multiline_define():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "local_include.h"
#define FLAG \\
    1 \\
    2
#include <vector>
''',
        'simple.h',
    )
    assert converted == '''module;
#define FLAG \\
    1 \\
    2
#include <vector>
export module simple;
import local_include;
'''


def test_module_include_system_and_local_in_one_ifdef():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "local_include.h"
#ifdef FLAG
 # include <vector>
 # include "local_include_2.h"
#endif // FLAG
''',
        'simple.h',
    )
    assert converted == '''module;
#ifdef FLAG
 # include <vector>
#endif // FLAG
export module simple;
import local_include;
#ifdef FLAG
  import local_include_2;
#endif // FLAG
'''


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
''',
        'simple.h',
    )
    assert converted == '''module;
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
'''


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
''',
        'simple.h',
    )
    assert converted == '''module;
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
'''


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
''',
        'simple.h',
    )
    assert converted == '''module;
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
'''


def test_module_include_system_comment():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "local_include.h"
// comment before system include
#include <vector>
''',
        'simple.h',
    )
    assert converted == '''module;
// comment before system include
#include <vector>
export module simple;
import local_include;
'''


def test_module_include_local_comment():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "local_include.h"
// comment before local include
 # include "local_include_2.h"
''',
        'simple.h',
    )
    assert converted == '''export module simple;
import local_include;
// comment before local include
  import local_include_2;
'''


def test_module_include_always_include_names_assert_h():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "assert.h"
''',
        'simple.h',
    )
    assert converted == '''module;
#include "assert.h"
export module simple;
'''


def test_module_include_always_include_names_options():
    converter = Converter(ConvertAction.MODULES)
    converter.options.always_include_names.append('options.h')
    converted = converter.convert_file_content(
        '''#include "options.h"
''',
        'simple.h',
    )
    assert converted[0].content == '''module;
#include "options.h"
export module simple;
'''


def test_module_include_always_include_names_in_subdir():
    converter = Converter(ConvertAction.MODULES)
    converter.options.always_include_names.append('subdir/options.h')
    converter.resolver.files_map.add_files_map_dict(
        {
            'subdir': {
                'options.h': FileEntryType.FILE,
                'simple.h': FileEntryType.FILE,
            },
        }
    )
    converted = converter.convert_file_content(
        '''#include "options.h"
''',
        'subdir/simple.h',
    )
    assert converted[0].content == '''module;
#include "options.h"
export module subdir.simple;
'''


def test_module_include_always_include_names_subdir():
    converter = Converter(ConvertAction.MODULES)
    converter.options.always_include_names.append('subdir/*')
    converter.resolver.files_map.add_files_map_dict(
        {
            'subdir': {
                'options.h': FileEntryType.FILE,
                'simple.h': FileEntryType.FILE,
            },
        }
    )
    converted = converter.convert_file_content(
        '''#include "options.h"
''',
        'subdir/simple.h',
    )
    assert converted[0].content == '''module;
#include "options.h"
export module subdir.simple;
'''


def test_module_include_always_include_names_subdir_root_named():
    converter = Converter(ConvertAction.MODULES)
    converter.options.always_include_names.append('subdir/options.h')
    converter.resolver.files_map.add_files_map_dict(
        {
            'subdir': {
                'options.h': FileEntryType.FILE,
                'simple.h': FileEntryType.FILE,
            },
        }
    )
    converter.options.set_root_dir_module_name('org')
    converted = converter.convert_file_content(
        '''#include "options.h"
''',
        'subdir/simple.h',
    )
    assert converted[0].content == '''module;
#include "options.h"
export module org.subdir.simple;
'''


def test_module_include_local_and_system():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''#include "local_include.h"
#include <vector>
''',
        'simple.h',
    )
    assert converted == '''module;
#include <vector>
export module simple;
import local_include;
'''


def test_module_file_comment():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''// this is file comment
''',
        'simple.h',
    )
    assert converted == '''// this is file comment
export module simple;
'''


def test_module_bom_and_file_comment():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''\ufeff// this is file comment
''',
        'simple.h',
    )
    assert converted == '''\ufeff// this is file comment
export module simple;
'''


def test_module_file_comment_and_include_system():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''// this is file comment
#include <vector>
''',
        'simple.h',
    )
    assert converted == '''// this is file comment
module;
#include <vector>
export module simple;
'''


def test_module_file_comment_and_include_local_and_system():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''// this is file comment
#include "local_include.h"
#include <vector>
''',
        'simple.h',
    )
    assert converted == '''// this is file comment
module;
#include <vector>
export module simple;
import local_include;
'''


def test_module_file_comment_and_include_system_w_newlines():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''
// this is file comment

#include <vector>

''',
        'simple.h',
    )
    assert converted == '''
// this is file comment

module;
#include <vector>
export module simple;
'''


def test_module_file_comment_and_include_local_and_system_w_newlines():
    converted = convert_file_content(
        ConvertAction.MODULES,
        '''
// this is file comment

#include "local_include.h"

#include <vector>
''',
        'simple.h',
    )
    assert converted == '''
// this is file comment

module;

#include <vector>
export module simple;
import local_include;
'''


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

''',
        'simple.h',
    )
    assert converted == '''
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
'''
