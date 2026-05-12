from cxx_modules_converter_lib import (
    Converter,
    ConvertAction,
    ContentType,
    FileOptions,
    FileContent,
    )


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


