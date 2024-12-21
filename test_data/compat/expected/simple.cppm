#ifndef CXX_COMPAT_HEADER
module;
#else
#pragma once
#include "local_include.h"
#endif
#include <vector>
#ifndef CXX_COMPAT_HEADER
export module simple;
#endif
#ifndef CXX_COMPAT_HEADER
import local_include;
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
