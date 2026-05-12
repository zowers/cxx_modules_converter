# AGENTS.md - Information for AI about cxx_modules_converter project

## Project Overview

**cxx_modules_converter** is a Python tool for converting C++ headers to C++20 modules and vice versa. The project automates migration of traditional C++ projects to modern C++20 modules.

## Project Architecture

### Core Components

1. **CLI Interface** (`cxx_modules_converter.py`)
   - Command line argument processing
   - Conversion process coordination
   - Logging and statistics output

2. **Core Library** (`cxx_modules_converter_lib/` module package)
   - `converter.py` - `Converter` class, main conversion logic
   - `options.py` - `Options`, `FileOptions`, `ConvertAction`, `ContentType`, constants
   - `resolvers.py` - `FilesResolver`, `ModuleFilesResolver`, `FilesMap`
   - `file_processing.py` - `FileContent`, `Matcher`, regular expressions, helper functions
   - `file_base_builder.py` - `FileBaseBuilder`, `FileProcessingState`
   - `module_base_builder.py` - `ModuleBaseBuilder`, `any_pattern_maches`
   - `module_interface_builder.py` - `ModuleInterfaceUnitBuilder`
   - `module_impl_builder.py` - `ModuleImplUnitBuilder`
   - `compat_header_builder.py` - `CompatHeaderBuilder`
   - `exceptions.py` - custom exception hierarchy
   - `__init__.py` - public API exports

3. **Test Infrastructure**
   - Modular test files with `_test.py` suffix placed next to source code
   - `test_data/` - test data with input/expected structure
   - Test files: `module_base_builder_test.py`, `converter_test.py`, `resolvers_test.py`, etc.

### Key Concepts

- **ContentType**: `HEADER`, `CXX`, `MODULE_INTERFACE`, `MODULE_IMPL`, `OTHER`
- **ConvertAction**: `MODULES` (headers → modules), `HEADERS` (modules → headers)
- **Module naming**: paths converted to module names using dots (e.g., `subdir/file.h` → `subdir.file`)

## Current Issues (for AI to fix)

### Architectural
1. **Dependency Resolution**: Complex logic in `FilesResolver`
2. **Module Building**: Multiple Builder classes with inheritance
3. **Configuration**: `Options` class is too large

## Recommendations for AI Working on the Project

### During Refactoring
1. **Maintain API backward compatibility**
   - Don't change public class methods
   - Use deprecation warnings for old APIs
   - Update version in pyproject.toml

2. **Test every change**
   - Run `pytest` after each change
   - Use test data from `test_data/`
   - Check edge cases

3. **Follow code style**
   - Use type hints (already present)
   - Naming: snake_case for functions/variables, PascalCase for classes
   - Document public methods

4. **Keep documentation current**
   - Remove completed tasks from TODO.md and AGENTS.md instead of marking them as done
   - Delete entire sections that are no longer relevant
   - Update version numbers and dates when making significant changes

### When Adding Functionality
1. **Extend, don't modify**
   - Add new parameters to `Options` with default values
   - Create new classes instead of modifying existing ones
   - Use inheritance for specialization

2. **Add tests**
   - Create test data in `test_data/new_feature/`
   - Write unit tests for new functionality
   - Update existing tests if necessary

3. **Document changes**
   - Update README.md for new CLI features
   - Add docstrings for new classes/methods
   - Update usage examples

## Test Data Structure

```
test_data/
├── test_case_name/
│   ├── input/          # Source files for conversion
│   │   ├── file1.h
│   │   └── subdir/file2.cpp
│   └── expected/       # Expected result
│       ├── file1.cppm
│       └── subdir/file2.cpp
```

**Important**: Tests compare conversion results with expected files.

## Common Code Patterns

### 1. Processing Include Directives
```python
if m.match(preprocessor_include_brackets_rx, line):
    builder.handle_include_brackets(line, m.matched)
elif m.match(preprocessor_include_quote_rx, line):
    builder.handle_include_quote(line, m.matched)
```

### 2. Building Modules
```python
builder = ModuleInterfaceUnitBuilder(options, resolver, file_options)
builder.set_module_name(module_name)
builder.add_module_content("// implementation")
```

### 3. Converting Files
```python
converter = Converter(ConvertAction.MODULES)
converter.options.set_root_dir_module_name("mymodule")
converter.convert_directory(input_path, output_path)
```

## Known Limitations

1. **Preprocessor**: Limited support for complex macros
2. **System Headers**: Only basic transformations
3. **Performance**: No caching, repeated file reads
4. **Memory**: Loads all files into memory

## Improvement Paths (for AI Agents)

### Mid-level Tasks
- [ ] Add caching for parsing results
- [ ] Improve preprocessor directive handling
- [ ] Add configuration validation

### High-level Tasks
- [ ] Implement incremental conversion
- [ ] Add C++23 module support
- [ ] Create plugin system

## Working Commands

### Testing
```bash
# Run all tests
pytest -vv

# Run specific test
pytest cxx_modules_converter_lib/module_base_builder_test.py::test_module_empty -vv

# Run with coverage
pytest --cov=cxx_modules_converter_lib --cov-report=html
```

### Development
```bash
# Install dependencies
pip install -r requirements-test.txt

# Run the script
python cxx_modules_converter.py -s test_data/simple/input -d output

# Type checking
mypy cxx_modules_converter.py cxx_modules_converter_lib
```

### Code Quality Tools
```bash
# Format code with black (preserves single quotes)
python -m black .

# Sort imports with isort
python -m isort . --profile black

# Lint with flake8
python -m flake8 .

# Remove unused imports
python -m autoflake --in-place --remove-all-unused-imports cxx_modules_converter_lib/*.py

# Pre-commit hooks (install first: pip install pre-commit)
pre-commit install    # Install hooks
pre-commit run --all-files  # Run on all files
```

## Contacts and Resources

- **Author**: Alexander Petrov (zowers@zowers.net)
- **Repository**: https://gitverse.ru/zowers/cxx_modules_converter
- **Documentation**: README.md
- **Version**: 0.1.17 (see pyproject.toml)

## For AI Agents: How to Help the Project

1. **Start small**: Fix one `print()` or `assert()` usage
2. **Test**: Ensure tests pass after changes
3. **Document**: Explain what and why was changed
4. **Follow the plan**: See TODO.md for priorities and timelines
5. **Story management**: All improvement stories are stored in TODO.md. New stories should be added at the end of the "Stories" section, before "Implementation Recommendations".
6. **Use English**: Ensure all changes maintain English-only policy

---
*Document created to assist AI agents in understanding and improving the project*
*Version: 1.6 | Date: 2026-05-12 | Status: Current*
