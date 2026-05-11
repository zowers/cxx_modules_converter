#!/bin/bash -ex

# Build script similar to CMakePresets.json
# Supported compilers: clang++-20, clang++-21, g++-14, g++-15

# Function to display help
show_help() {
    echo "Usage: $0 <preset>"
    echo ""
    echo "Available presets:"
    echo "  test-clang-20    Build using clang++-20"
    echo "  test-clang-21    Build using clang++-21"
    echo "  test-gcc-15      Build using g++-15"
    echo ""
    echo "Examples:"
    echo "  $0 test-clang-20          # Build with clang++-20"
    echo "  $0 test-clang-21          # Build with clang++-21"
    echo "  $0 test-gcc-15            # Build with g++-15"
}

# Check for required tools
check_compiler() {
    local compiler=$1
    if command -v "$compiler" &> /dev/null; then
        echo "Found compiler: $compiler"
        return 0
    else
        echo "Error: compiler $compiler not found"
        return 1
    fi
}

# Function to build the project
build_project() {
    local preset=$1
    local compiler=""
    local module_compile_flag=""
    local module_output_ext="pcm"
    local module_path_flag=""
    local source_compile_flags=""
    local module_output_dir="build"
    
    # Select compiler and specific options based on preset
    case $preset in
        test-clang-20)
            compiler="clang++-20"
            module_compile_flag="--precompile"
            module_output_ext="pcm"
            module_path_flag="-fprebuilt-module-path=build"
            source_compile_flags="-fprebuilt-module-path=build -c"
            module_output_dir="build"
            ;;
        test-clang-21)
            compiler="clang++-21"
            module_compile_flag="--precompile"
            module_output_ext="pcm"
            module_path_flag="-fprebuilt-module-path=build"
            source_compile_flags="-fprebuilt-module-path=build -c"
            module_output_dir="build"
            ;;
        test-gcc-15)
            compiler="g++-15"
            module_compile_flag="-fmodules -c"
            module_output_ext="o"
            module_path_flag=""
            source_compile_flags="-fmodules -c"
            module_output_dir="build"
            ;;
        *)
            echo "Error: Unknown preset '$preset'"
            show_help
            exit 1
            ;;
    esac
    
    # Check compiler availability
    if ! check_compiler "$compiler"; then
        exit 1
    fi
    
    echo "Building project with preset: $preset"
    echo "  Compiler: $compiler"
    echo "  Module flag: $module_compile_flag"
    echo "  Output extension: $module_output_ext"
    
    # Create build directory
    rm -rf build gcm.cache && mkdir -p build $module_output_dir
    
    # Compile module partitions
    echo "Compiling module partitions..."
    $compiler -std=gnu++23 $module_compile_flag mymodule/part1.cppm -o $module_output_dir/mymodule-part1.$module_output_ext
    if [ $? -ne 0 ]; then
        echo "Error compiling partition mymodule:part1"
        exit 1
    fi
    
    $compiler -std=gnu++23 $module_compile_flag mymodule/part2.cppm -o $module_output_dir/mymodule-part2.$module_output_ext
    if [ $? -ne 0 ]; then
        echo "Error compiling partition mymodule:part2"
        exit 1
    fi
    
    # Compile main module with path to partitions
    echo "Compiling main module..."
    $compiler -std=gnu++23 $module_path_flag $module_compile_flag mymodule.cppm -o $module_output_dir/mymodule.$module_output_ext
    if [ $? -ne 0 ]; then
        echo "Error compiling main module mymodule"
        exit 1
    fi
    
    # Compile source files using modules
    echo "Compiling source files..."
    $compiler -std=gnu++23 $source_compile_flags mymodule/part1.cpp -o build/part1.o
    if [ $? -ne 0 ]; then
        echo "Error compiling part1.cpp"
        exit 1
    fi
    
    $compiler -std=gnu++23 $source_compile_flags mymodule/part2.cpp -o build/part2.o
    if [ $? -ne 0 ]; then
        echo "Error compiling part2.cpp"
        exit 1
    fi
    
    $compiler -std=gnu++23 $source_compile_flags main.cpp -o build/main.o
    if [ $? -ne 0 ]; then
        echo "Error compiling main.cpp"
        exit 1
    fi
    
    # Link object files
    echo "Linking..."
    $compiler -std=gnu++23 -o build/test_mod build/main.o build/part1.o build/part2.o
    if [ $? -eq 0 ]; then
        echo "Build completed successfully"
        echo "Executable: build/test_mod"
    else
        echo "Linking error"
        exit 1
    fi
}

# Main script logic
main() {
    # Check number of arguments
    if [ $# -ne 1 ]; then
        echo "Error: Must specify one preset"
        show_help
        exit 1
    fi
    
    local preset=$1
    
    # Process command line arguments
    case $preset in
        -h|--help)
            show_help
            exit 0
            ;;
        test-clang-20|test-clang-21|test-gcc-15)
            build_project "$preset"
            ;;
        *)
            echo "Error: Unknown argument '$preset'"
            show_help
            exit 1
            ;;
    esac
}

# Launch main logic
main "$@"