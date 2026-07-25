# Development Guide for Contributors

This document is intended for developers who want to understand the internal architecture of `cxx_modules_converter` and contribute to its codebase. It complements the user-focused README with technical details about design decisions, code organization, and development workflows.

## Architecture Overview

The converter follows a pipeline architecture:

1. **File Discovery** – `FilesResolver` scans the source directory, classifies files by `ContentType`, and applies skip/compat/header patterns.
2. **Dependency Resolution** – The resolver builds a graph of `#include` relationships and maps them to module imports.
3. **Parsing** – `file_processing.py` parses traditional files or module files into handler calls or structured records.
4. **Content Transformation** – A **Builder** selected by content type and conversion action rewrites the parsed input:
   - `#include <...>` → moved to global module fragment or replaced with `import std;`
   - `#include "..."` → converted to `import module.name;`
   - `#pragma once` and include guards are removed.
   - Module declarations (`export module ...`) and partitions are added.
5. **Output Generation** – The builder produces a `FileContent` object that is written to the destination directory.

### Core Data Structures

- **`FileContent`** – Immutable representation of a file’s lines with metadata (path, content type).
- **`FileOptions`** – Per-file configuration derived from global `Options` (module name, compat flag, etc.).
- **`FilesMap`** – Mapping from file paths to `FileOptions`, used by the resolver.

### Key Algorithms

- **Module name derivation**: The module name is computed from the file’s relative path (dots replace directory separators). The `--join` option can merge multiple files into a single module with partitions.
- **Circular dependency detection**: A depth-first search (DFS) on the import graph; cycles are reported but conversion continues (the generated modules may not compile).
- **Include-to-import translation**: For each `#include`, the resolver looks up the included file’s module name. If the included file is outside the conversion scope (e.g., a system header), the `#include` is kept in the global module fragment.

## Code Organization

### `cxx_modules_converter_lib/` Module

- **`converter.py`** – The central `Converter` class orchestrates the whole conversion. It uses the resolver and builders.
- **`options.py`** – `Options` (global settings), `FileOptions` (per-file settings), and enums (`ConvertAction`, `ContentType`).
- **`resolvers.py`** – `FilesResolver` and `ModuleFilesResolver` implement file classification and dependency resolution.
- **`file_processing.py`** – File parsers, parsed module records, `FileContent`, `Matcher`, and parsing regular expressions.
- **`file_base_builder.py`** – Abstract `FileBaseBuilder` and `FileProcessingState`; common logic for all builders.
- **`header_builder.py`** – `HeaderBuilder` converts parsed module files to traditional headers and C++ sources.
- **`module_base_builder.py`** – `ModuleBaseBuilder` extends `FileBaseBuilder` and adds module-specific logic (global module fragment, import/export handling).
- **`module_interface_builder.py`** – `ModuleInterfaceUnitBuilder` produces module interface units (`.cppm`).
- **`module_impl_builder.py`** – `ModuleImplUnitBuilder` produces module implementation units (`.cpp`).
- **`compat_header_builder.py`** – `CompatHeaderBuilder` generates compatibility headers that `#include` the corresponding module.
- **`exceptions.py`** – Custom exception hierarchy rooted at `CxxModulesConverterError`.

### Public API

The library’s public API is defined in `cxx_modules_converter_lib/__init__.py`. Only the symbols listed in `__all__` are intended for external use. When adding new features, consider whether they should be exposed via the public API.

## Adding a New Feature

### Step-by-Step Example: Adding Support for a New Preprocessor Directive

Suppose we want to handle `#warning` directives (pass them through unchanged but keep them in the correct location).

1. **Extend the regex patterns** in `file_processing.py`:
   ```python
   preprocessor_warning_rx = re.compile(r'^\s*#\s*warning\b')
   ```

2. **Update the `Matcher` logic** in `file_base_builder.py` or `module_base_builder.py` to recognize the new pattern and call a handler method.

3. **Add a handler method** to the builder classes (if the directive needs special treatment). For `#warning`, we can simply keep it as-is, so we can add it to the “other preprocessor” category.

4. **Write tests** in the corresponding `*_test.py` file, and add test data in `test_data/` to verify the directive is preserved.

5. **Update documentation** in `docs/` and `README.md` if the change affects user-visible behavior.

### Backward Compatibility

The library follows [Semantic Versioning](https://semver.org/). Breaking changes require a major version bump. To maintain backward compatibility:

- Do not remove or rename public classes/methods.
- Deprecate old APIs with a `DeprecationWarning` before removing them.
- Keep default values of options unchanged; add new options with sensible defaults.

## Testing Strategy

### Unit Tests

Each source file has a corresponding `*_test.py` file. Tests should be small, fast, and independent. Use `pytest` fixtures for common setup.

### Integration Tests

The `test_data/` directory contains whole-project test cases. Each subdirectory has an `input/` folder with source files and an `expected/` folder with the expected conversion output. The test runner:

1. Copies `input/` to a temporary directory.
2. Runs the converter on it.
3. Compares the result with `expected/` file-by-file.

Adding a new integration test:

```bash
mkdir -p test_data/new_feature/input
mkdir -p test_data/new_feature/expected
# Create sample files in input/
# Run the converter manually to generate expected/ content
# Add a test function in converter_test.py that references "new_feature"
```

### Property-Based Testing

Consider using `hypothesis` for generating random C++ code and verifying that conversion is idempotent or that certain invariants hold. (Not yet implemented.)

## Debugging Tips

### Logging

The converter uses the standard `logging` module. Set the log level to `DEBUG` to see detailed steps:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or from the CLI:

```bash
python cxx_modules_converter.py -s input -d output --log-level DEBUG
```

### Interactive Debugging with `pdb`

Insert a breakpoint in the code:

```python
import pdb; pdb.set_trace()
```

Or run the script under `pdb`:

```bash
python -m pdb cxx_modules_converter.py -s test_data/simple/input -d /tmp/output
```

### Visualizing Dependency Graphs

You can dump the module dependency graph (available in `Converter.module_dependencies`) to a DOT file and render it with Graphviz. A helper script could be added to `scripts/`.

## Performance Profiling

To identify bottlenecks, use Python’s `cProfile`:

```bash
python -m cProfile -o profile.stats cxx_modules_converter.py -s large_project -d /tmp/out
python -m pstats profile.stats
```

Common optimizations:

- Cache the results of `FilesResolver.resolve_file()`.
- Use `lru_cache` for expensive pure functions.
- Read files once and keep them in memory (already done).
- Parallelize file processing (future work).

## Code Style and Conventions

- **Naming**: `snake_case` for functions and variables, `PascalCase` for classes, `UPPER_CASE` for constants.
- **Type hints**: Use them for all function arguments and return values. Run `mypy` to verify.
- **Docstrings**: Follow [Google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings). Document public classes and methods.
- **Imports**: Group standard library, third-party, and local imports separated by a blank line. Sort with `isort --profile black`.
- **Line length**: 88 characters (Black’s default).

## Pre-commit Hooks

The project uses pre-commit to enforce code quality before each commit. The hooks are configured in `.pre-commit-config.yaml` and include:

- `black` (formatting)
- `isort` (import sorting)
- `flake8` (linting)
- `mypy` (type checking)
- `end-of-file-fixer`, `trailing-whitespace` (basic cleanliness)

To run hooks manually on all files:

```bash
pre-commit run --all-files
```

## Release Checklist

1. **Update version** using Poetry:
   ```bash
   poetry version patch   # for bug fixes
   poetry version minor   # for new features
   poetry version major   # for breaking changes
   ```
   This updates `pyproject.toml` and optionally creates a Git tag.
2. **Ensure all tests pass** (`pytest -vv`).
3. **Update documentation**:
   - `README.md` if there are new features or breaking changes.
   - `docs/` files (api.md, usage_examples.md, development.md).
   - `AGENTS.md` – update version and date.
   - `TODO.md` – remove completed stories.
4. **Create a Git tag** (if not already created by Poetry):
   ```bash
   git tag -a v0.1.18 -m "Release version 0.1.18"
   git push origin v0.1.18
   ```
5. **Build and publish** with Poetry:
   ```bash
   poetry build
   poetry publish
   ```
6. **Announce** on appropriate channels (if any).

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Make your changes, adhering to the code style and writing tests.
4. Run the full test suite and pre-commit hooks.
5. Submit a pull request with a clear description of the changes and the problem they solve.

For larger changes, it’s a good idea to open an issue first to discuss the design.

*Last updated: 2026-05-12*
*Document version: 1.0*
