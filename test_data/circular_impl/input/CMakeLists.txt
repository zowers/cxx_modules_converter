cmake_minimum_required(VERSION 3.31)
project(test_mod)
set(CMAKE_CXX_STANDARD 23)
add_executable(test_mod)
target_sources(test_mod
    PUBLIC
        main.cpp
        moduleA.cpp
        moduleB.cpp
        moduleC.cpp
)

file(GLOB CXX_MODULES "*.cppm")
if (CXX_MODULES)
    target_sources(test_mod
        PUBLIC
            FILE_SET CXX_MODULES
            FILES ${CXX_MODULES}
    )
endif()
