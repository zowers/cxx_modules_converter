from cxx_modules_converter_lib import (
    Converter,
    ConvertAction,
    FileEntryType,
    )


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

