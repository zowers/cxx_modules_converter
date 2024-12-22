#ifndef CXX_COMPAT_HEADER
module;
#else
#pragma once
#include "local_include.h"
#endif
#include <vector>
#ifndef CXX_COMPAT_HEADER
export module subdir.simple2;
#endif
#ifndef CXX_COMPAT_HEADER
import local_include;
#endif

#ifndef CXX_COMPAT_HEADER
extern "C++" {
export {
#endif
namespace TestNS
{
namespace Test
{
class TestClass
{
    TestClass();
};
} // namespace Test
} // namespace TestNS
#ifndef CXX_COMPAT_HEADER
} // export
} // extern "C++"
#endif
