# API Documentation

This document describes the public API of the `cxx_modules_converter` library.

## Overview

The `cxx_modules_converter` library provides functionality to convert C++ header files to C++20 module interface units and implementation units, and vice versa. The main entry points are the `Converter` class and the convenience functions `convert_directory`, `convert_file_content`, and `find_cycles`.

## Core Classes

### `Converter`

The main class that orchestrates the conversion process.

**Constructor:**
```python
def __init__(self, action: ConvertAction)
```
- `action`: Either `ConvertAction.MODULES` (convert headers to modules) or `ConvertAction.HEADERS` (convert modules to headers).

**Attributes:**
- `options`: An instance of `Options` that holds configuration settings.
- `resolver`: A `FilesResolver` instance used for file resolution.
- `all_files`, `convertable_files`, `converted_files`, `copied_files`: Statistics counters.

**Methods:**
- `convert_directory(source_dir: Path, dest_dir: Path) -> None`: Convert all files in `source_dir` and write results to `dest_dir`.
- `convert_file_content(content: FileContent, file_options: FileOptions) -> FileContent`: Convert a single file's content.
- `find_cycles() -> list[list[str]]`: Detect circular dependencies among modules.

**Example:**
```python
from cxx_modules_converter_lib import Converter, ConvertAction
from pathlib import Path

converter = Converter(ConvertAction.MODULES)
converter.options.set_root_dir_module_name("mymodule")
converter.convert_directory(Path("input"), Path("output"))
```

### `Options`

Holds configuration options for the conversion.

**Attributes:**
- `always_include_names` (list[str]): Header names that are always treated as system headers. Default: `['cassert', 'assert.h']`.
- `root_dir` (Path): Root directory for module name resolution. Default: current directory.
- `search_path` (list[str]): Include search paths. Default: empty list.
- `skip_patterns` (list[str]): Patterns for files/directories to skip. Default: empty list.
- `compat_patterns` (list[str]): Patterns for compatibility-mode files. Default: empty list.
- `compat_macro` (str): Macro name used in compatibility headers. Default: `'CXX_COMPAT_HEADER'`.
- `export` (dict[str, set[str]]): Export mapping (module → set of exported modules). Default: empty dict. Configure with `add_export_module`.
- `export_suffixes` (list[str]): Suffixes that trigger export import. Default: empty list.
- `modules_ext_types` (dict[str, ContentType]): Mapping from file extension to content type. Default: `{'.h': ContentType.HEADER, '.cpp': ContentType.CXX}`. Modify with `add_module_action_ext_type`.
- `headers_ext_types` (dict[str, ContentType]): Mapping from header extension to content type. Default: `{'.cppm': ContentType.MODULE_INTERFACE, '.cpp': ContentType.MODULE_IMPL}`. Modify with `add_header_action_ext_type`.
- `content_type_to_ext` (dict[ContentType, str]): Output extension for each content type. Default: `{HEADER: '.h', CXX: '.cpp', MODULE_INTERFACE: '.cppm', MODULE_IMPL: '.cpp'}`. Set via `set_output_content_type_to_ext`.
- `path_to_module_prefix_map` (dict[PurePosixPath, str]): Mapping from path to module prefix. Default: empty dict. Add mappings with `add_modules_path`.
- `join_configurations` (dict[str, str]): Join module partitions file patterns (pattern → target module). Default: empty dict. Add with `add_join_configuration`. Each pattern maps to the primary module that will contain the matching files as module partitions.

**Methods:**

- `add_export_module(owner: str, export: str)` – configure export relationships (`--export A=B`).
- `add_module_action_ext_type(ext: str, type: ContentType)` – map file extensions for module conversion (`--inextheader`, `--inextcxx`).
- `add_header_action_ext_type(ext: str, type: ContentType)` – map file extensions for header conversion.
- `set_output_content_type_to_ext(type: ContentType, ext: str)` – set output file extensions (`--outextmod`, `--outextmodimpl`).
- `add_modules_path(module_prefix: str, pathStr: str)` – map a filesystem path to a module prefix (`--modules M=P`).
- `root_dir_module_name() -> str` – get the module prefix for the root directory.
- `set_root_dir_module_name(prefix: str)` – set the root directory module prefix (`--name`).
- `add_std_module()` – enable the `std` module (`--modulestd`).
- `add_std_compat_module()` – enable the `std.compat` module (`--modulestdcompat`).
- `add_join_configuration(target_module: str, pattern: str)` – configure joining of files into a module (`--join A=B`).

**Example:**
```python
from cxx_modules_converter_lib import Options

options = Options()
# Set the top-level module name for files in the root directory (--name)
options.set_root_dir_module_name("mymodule")
# Configure export: mymodule will export submodule (--export mymodule=submodule)
options.add_export_module("mymodule", "submodule")
# Map files under "subdir" to the module prefix "submodule" (--modules submodule=subdir)
options.add_modules_path("submodule", "subdir")
# Join all header files matching "**/part*.h" into module "mymodule" as partitions (--join mymodule=**/part*.h)
options.add_join_configuration("mymodule", "**/part*.h")
```

### `FileOptions`

Per-file configuration derived from global options.

**Attributes:**
- `convert_as_compat` (bool): Whether the file should be converted in compatibility mode.

### `ConvertAction` Enum

- `MODULES`: Convert headers to modules.
- `HEADERS`: Convert modules to headers.

### `ContentType` Enum

- `HEADER`: Traditional C++ header file (.h, .hpp, .hxx).
- `CXX`: C++ source file (.cpp, .cxx, .cc).
- `MODULE_INTERFACE`: C++20 module interface unit (.cppm, .ixx).
- `MODULE_IMPL`: C++20 module implementation unit (.cpp).
- `OTHER`: Any other file type.

## Resolvers

### `FilesResolver`

Resolves file paths, determines content types, and builds dependency graphs.

**Constructor:**
```python
def __init__(self, options: Options)
```

**Methods:**
- `resolve_file(path: Path) -> FileOptions`: Determine options for a given file.
- `add_file(path: Path, content_type: ContentType) -> None`: Register a file with a given content type.
- `get_module_name(path: Path) -> str`: Compute the module name from a file path.

### `ModuleFilesResolver`

Specialized resolver for module files.

### `FilesMap`

A mapping from file paths to `FileOptions`.

## Builders

Builders are responsible for generating the output content.

### `ModuleInterfaceUnitBuilder`

Builds a module interface unit (`.cppm`).

**Methods:**
- `set_module_name(name: str) -> None`
- `add_module_content(line: str) -> None`
- `add_import(module_name: str) -> None`
- `add_export_import(module_name: str) -> None`
- `build() -> FileContent`

### `ModuleImplUnitBuilder`

Builds a module implementation unit (`.cpp`).

### `CompatHeaderBuilder`

Builds a compatibility header (`.h`) that re-exports a module via `#include`.

### `HeaderBuilder`

Builds a traditional header (`.h`) or C++ source from records produced by `parse_module_file`.

### `FileBaseBuilder`

Base class for all builders.

## File Processing

### `FileContent`

Represents the content of a file with metadata.

**Attributes:**
- `lines`: List of strings (the file lines).
- `path`: The file path.
- `content_type`: The `ContentType`.

### `Matcher`

Utility for matching lines against regular expressions.

### `HeaderScanState`

Tracks the state while scanning a header for `#include` directives.

### `ParsedModuleFile` and `ModuleLine`

Structured output from parsing a module interface or implementation file. `ModuleLineKind` identifies module declarations, imports, export blocks, exported declarations, and unchanged content.

### Parsing Functions

- `parse_module_file(content, filename, compatibility_macro) -> ParsedModuleFile` parses module syntax for reverse conversion.
- `find_declared_module(content) -> str | None` extracts a named module declaration.
- `process_header_content(content, handler) -> None` parses traditional headers and dispatches records to a module builder.

## Convenience Functions

### `convert_directory(source_dir: Path, dest_dir: Path, action: ConvertAction = ConvertAction.MODULES, **kwargs) -> None`

High-level function that creates a `Converter` with the given `action`, configures it via `kwargs`, and runs the conversion.

**Example:**
```python
from cxx_modules_converter_lib import convert_directory, ConvertAction
from pathlib import Path

convert_directory(Path("input"), Path("output"), ConvertAction.MODULES, root_dir_module_name="mymodule")
```

### `convert_file_content(content: FileContent, file_options: FileOptions) -> FileContent`

Convert a single `FileContent` object according to `file_options`.

### `find_cycles(dependencies: dict[str, set[str]]) -> list[list[str]]`

Find circular dependencies in a graph represented as a dict mapping module names to sets of imported modules.

## Exceptions

The library defines a hierarchy of exceptions:

- `CxxModulesConverterError`: Base exception for all library errors.
- `ConfigurationError`: Invalid configuration (e.g., missing required options).
- `ConversionError`: Error during conversion (e.g., unsupported syntax).
- `FileSystemError`: I/O errors (e.g., file not found, permission denied).
- `ValidationError`: Validation of input parameters failed.

## Constants

- `COMPAT_MACRO_DEFAULT`: Default macro name used in compatibility headers.
- `always_include_names`: Set of header names that are always treated as system headers (e.g., `<iostream>`).

## Usage Example (Library API)

```python
from pathlib import Path
from cxx_modules_converter_lib import (
    Converter,
    ConvertAction,
    Options,
    FileContent,
    ContentType,
)

# Create converter
converter = Converter(ConvertAction.MODULES)

# Configure options
converter.options.set_root_dir_module_name("mymodule")
converter.options.add_include_path("include")

# Convert a whole directory
converter.convert_directory(Path("project/src"), Path("project/out"))

# Convert a single file
content = FileContent.from_path(Path("project/src/foo.h"))
file_opts = converter.resolver.resolve_file(content.path)
converted = converter.convert_file_content(content, file_opts)
print(converted.lines)
```

## See Also

- [Usage Examples](usage_examples.md) – more detailed examples of using the library.
- [Development Guide](development.md) – for contributors.
