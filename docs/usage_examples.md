# Usage Examples

This document provides practical examples of using `cxx_modules_converter` both as a command-line tool and as a Python library.

## Command-Line Interface (CLI)

The main script `cxx_modules_converter.py` offers a rich set of options. Below are common scenarios.

### Basic Conversion (Headers → Modules)

Convert all `.h` and `.cpp` files in a directory to C++20 modules, writing the results to an output directory.

```bash
python cxx_modules_converter.py -s project/src -d project/out
```

This will:
- Scan `project/src` for header and source files.
- Create module interface units (`.cppm`) for each header.
- Create module implementation units (`.cpp`) for each source file (if needed).
- Copy other files unchanged.
- Place the results in `project/out`, preserving the directory structure.

### Converting Modules to Headers

Convert `.cppm` module interfaces to `.h` headers and update `.cpp` files to use `#include` directives:

```bash
python cxx_modules_converter.py -a headers -s project/modules -d project/src
```

The converter indexes module declarations before processing files, so named imports and relative partition imports resolve to relative paths for the corresponding generated headers. Generated headers use `#pragma once`. Header-unit imports such as `import <vector>;` become `#include <vector>`. An unresolved named import causes an error rather than an unsafe guessed include path.

Use `--inextmod`, `--inextmodimpl`, `--outextheader`, and `--outextcxx` to customize reverse-conversion extensions.

Compatibility modules, private module fragments, and multiline export declarations are not supported by reverse conversion and produce an explicit error.

### In-Place Conversion

Convert files in the same directory, replacing headers with module interface units and updating source files accordingly.

```bash
python cxx_modules_converter.py -s project/src -i
```

**Warning:** This operation overwrites original files. Make sure you have a backup or use version control.

### Specifying a Root Module Name

If you want all modules to be prefixed with a common name (e.g., `mylib`), use the `--name` option.

```bash
python cxx_modules_converter.py -s project/src -d project/out -n mylib
```

For a header `project/src/utils/helper.h` the resulting module will be named `mylib.utils.helper`.

### Using Include Search Paths

When your project uses `#include "subdir/header.h"` and the header is located in a different directory relative to the source, you can add include search paths with `-I`.

```bash
python cxx_modules_converter.py -s project/src -d project/out -I project/include -I external/lib/include
```

The converter will look for included files in those directories and convert the `#include` directives to appropriate `import` statements.

### Skipping Files and Directories

Exclude test files, generated code, or third-party headers from conversion.

```bash
python cxx_modules_converter.py -s project/src -d project/out -k "**/test*" -k "**/generated/*"
```

Patterns use `fnmatch` syntax. Skipped files are copied unchanged.

### Compatibility Headers

Generate compatibility headers (traditional `.h` files) that re-export a module via `#include`. This allows you to migrate incrementally: new code uses `import`, old code keeps `#include`.

```bash
python cxx_modules_converter.py -s project/src -d project/out -c "**/public/*.h"
```

Files matching the `-c` pattern will produce both a module interface unit (`.cppm`) and a compatibility header (`.h`). The compatibility header contains a macro guard and `#include` of the module.

### Joining Multiple Headers into a Single Module

Combine several headers into one module with partitions. For example, all headers under `project/src/core/` should become partitions of module `core`.

```bash
python cxx_modules_converter.py -s project/src -d project/out --join core=core/*
```

This creates:
- `core.cppm` – primary module interface unit.
- `core.part1.cppm`, `core.part2.cppm`, … – partition interface units for each header.

### Handling Standard Library Headers

Replace `#include <vector>`, `#include <iostream>`, etc. with `import std;` (or `import std.compat;`).

```bash
python cxx_modules_converter.py -s project/src -d project/out --modulestd
```

If you want to keep the old includes for compatibility but also provide a `std` module, use `--modulestdcompat`.

### Exporting Imports

Make certain imports visible to users of your module. For example, module `A` that imports module `B` can export `B` so that clients of `A` automatically gain access to `B`.

```bash
python cxx_modules_converter.py -s project/src -d project/out --export "A=B"
```

You can also use wildcards:
- `--export "*=*"` – every module exports every import.
- `--export "A=*"` – module `A` exports all its imports.
- `--export "*=B"` – every module that imports `B` exports it.

### Changing File Extensions

Use different extensions for input headers, input C++ sources, output module interfaces, and output module implementations.

```bash
python cxx_modules_converter.py -s project/src -d project/out \
  --inextheader .hpp \
  --inextcxx .cxx \
  --outextmod .ixx \
  --outextmodimpl .cpp
```

### Detecting Circular Dependencies

The converter automatically detects circular dependencies among modules and reports them. To just check for cycles without converting, you can run the conversion with a dry-run option (not yet implemented) or use the library function `find_cycles` (see below).

## Library Usage Examples

The `cxx_modules_converter_lib` module provides a Python API for programmatic conversion.

### Converting a Directory

```python
from pathlib import Path
from cxx_modules_converter_lib import convert_directory, ConvertAction

convert_directory(
    Path("project/src"),
    Path("project/out"),
    ConvertAction.MODULES,
    root_dir_module_name="mylib",
    include_paths=["project/include"],
    skip_patterns=["**/test*"],
)
```

### Using the Converter Class Directly

```python
from pathlib import Path
from cxx_modules_converter_lib import Converter, ConvertAction, Options

# Create converter
converter = Converter(ConvertAction.MODULES)

# Configure options
converter.options.set_root_dir_module_name("mylib")
converter.options.add_include_path("project/include")
converter.options.add_skip_pattern("**/test*")

# Perform conversion
converter.convert_directory(Path("project/src"), Path("project/out"))

# Print statistics
print(f"Processed {converter.all_files} files")
print(f"Converted {converter.converted_files} files")
print(f"Copied {converter.copied_files} files")
```

### Converting a Single File

```python
from pathlib import Path
from cxx_modules_converter_lib import (
    Converter,
    ConvertAction,
    FileContent,
    ContentType,
)

converter = Converter(ConvertAction.MODULES)
converter.options.set_root_dir_module_name("mylib")

# Load a header file
content = FileContent.from_path(Path("project/src/utils/helper.h"))

# Determine file options
file_opts = converter.resolver.resolve_file(content.path)

# Convert
converted = converter.convert_file_content(content, file_opts)

# Write result (or use it in memory)
with open("helper.cppm", "w", encoding="utf-8") as f:
    f.writelines(converted.lines)
```

### Finding Circular Dependencies

```python
from cxx_modules_converter_lib import find_cycles

# Suppose you have a dependency graph
deps = {
    "A": {"B", "C"},
    "B": {"C"},
    "C": {"A"},  # cycle A → B → C → A
}

cycles = find_cycles(deps)
print(cycles)  # [['A', 'B', 'C']]
```

### Creating a Compatibility Header Manually

```python
from cxx_modules_converter_lib import CompatHeaderBuilder, Options

options = Options()
builder = CompatHeaderBuilder(options, module_name="mylib.utils.helper")
builder.add_module_content("// module content")
builder.add_import("other.module")

compat_header = builder.build()
print("".join(compat_header.lines))
```

## Real-World Scenario

### Migrating a Large Codebase Step by Step

1. **Start with a small subsystem** – convert only the headers in `core/` and generate compatibility headers for them.

   ```bash
   python cxx_modules_converter.py -s project/core -d project/out -c "**/*.h" -n mylib.core
   ```

2. **Update the build system** – adjust your CMakeLists.txt or MSVC project to compile `.cppm` files as module interface units.

3. **Convert dependent source files** – after the headers are modules, convert the `.cpp` files that include them.

   ```bash
   python cxx_modules_converter.py -s project/core -d project/out -a modules
   ```

4. **Gradually expand** – repeat for other directories, using include search paths to resolve cross-directory includes.

5. **Finally, drop compatibility headers** – once all code uses `import`, you can stop generating compatibility headers (remove the `-c` option) and remove the old `.h` files.

## Troubleshooting

### “Cannot find included file”

If the converter complains about missing includes, make sure you have specified all necessary include search paths with `-I`. Also check that the file exists and is not skipped by a `-k` pattern.

### “Circular dependency detected”

The converter will list the cycles it found. You need to break the cycle by refactoring your code (e.g., extract common parts into a new module) or by using forward declarations. The converter will still produce output, but the generated modules may not compile until the cycle is resolved.

### “Unsupported preprocessor directive”

The converter handles `#include`, `#define`, `#if`, `#ifdef`, `#ifndef`, `#else`, `#elif`, `#endif`, `#pragma once`, and line comments (`#`). Other directives (e.g., `#error`, `#warning`, `#line`) are passed through unchanged but may affect conversion correctness. Consider simplifying or removing such directives before conversion.

## See Also

- [API Documentation](api.md) – detailed description of classes and functions.
- [Development Guide](development.md) – for contributors.
