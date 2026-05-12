# TODO: Improvement Plan for cxx_modules_converter

## Overview
This document contains an improvement plan for the `cxx_modules_converter` project - a tool for converting C++ headers to C++20 modules and vice versa.

## Stories
### MOD-1000: Improve Documentation (Medium)
**Problem**: Incomplete API documentation.

**Tasks:**
- [ ] Add API documentation with examples in `docs/api.md`
- [ ] Create `docs/usage_examples.md` with usage examples
- [ ] Add `docs/development.md` for developers
- [ ] Update README.md with links to documentation
- [ ] Add docstrings for all public classes and methods

### MOD-1001: Add Configuration Validation (Medium)
**Problem**: Lack of input parameter validation.

**Tasks:**
- [ ] Add file extension validation
- [ ] Check existence of paths and files
- [ ] Validate patterns for skip/compat/header
- [ ] Add warnings about potential issues
- [ ] Create configuration validation utility

### MOD-1002: Code Formatting and Style Enforcement (Medium)
**Problem**: Inconsistent code style across the codebase.

**Tasks:**
- [ ] Apply `black` formatter to all Python files
- [ ] Apply `isort` for consistent import ordering
- [ ] Add `flake8` linting with project-specific configuration
- [ ] Create pre-commit hooks for automatic formatting
- [ ] Add CI check for code style compliance

**Files to format:**
- `cxx_modules_converter.py`
- All files in `cxx_modules_converter_lib/` directory


### MOD-1003: Performance Optimization (Long)
**Problem**: Repeated file reading and writing.

**Tasks:**
- [ ] Add caching of parsing results
- [ ] Optimize file system operations
- [ ] Add support for incremental conversion
- [ ] Implement parallel file processing
- [ ] Add progress bar for large projects

### MOD-1004: Extend Functionality (Long)
**Problem**: Limited preprocessor directive support.

**Tasks:**
- [ ] Add support for more preprocessor directives
- [ ] Improve handling of complex macro cases
- [ ] Add plugin system for custom transformations
- [ ] Support C++23 modules
- [ ] Add customization of transformations via config

### MOD-1005: Improve UX (Long)
**Problem**: Basic command line interface.

**Tasks:**
- [ ] Add colored output for better readability
- [ ] Improve error messages with fix suggestions
- [ ] Add dry-run mode for previewing changes
- [ ] Create interactive mode for configuration
- [ ] Add support for configuration files (JSON/YAML)

### MOD-1006: CI/CD Improvements (Long)
**Problem**: Basic testing setup.

**Tasks:**
- [ ] Add type checking (mypy)
- [ ] Add linters (flake8, black)
- [ ] Set up automated testing for different Python versions (3.10+)
- [ ] Add performance tests
- [ ] Set up automatic deployment to PyPI

## Implementation Recommendations

### Phase 1: Preparation (1-2 weeks)
1. Create refactoring branch
2. Add additional tests for critical functionality
3. Set up CI/CD for new structure

### Phase 2: Refactoring (2-3 weeks)
1. Implement structured logging
2. Improve error handling
3. Split monolithic file into modules

### Phase 3: Testing (1-2 weeks)
1. Update tests for new structure
2. Perform regression testing
3. Test on real projects

### Phase 4: Documentation and Release (1 week)
1. Update documentation
2. Create migration guide
3. Release new version

## Success Criteria

### For each improvement:
- [ ] All existing tests pass
- [ ] New functionality is covered by tests
- [ ] Documentation is updated
- [ ] Backward compatibility is preserved (where possible)
- [ ] Performance is not degraded

### General metrics:
- Reduce size of largest file from 1246 to <500 lines
- Increase test coverage to 90%+
- Reduce test execution time by 20%
- Improve code readability (analysis tool scores)

## Resources

### Required:
- 1 senior Python developer (8 weeks)
- 1 QA engineer (4 weeks)
- CI/CD infrastructure

### Existing:
- Extensive test data
- Working CI via pytest
- CLI documentation

## Timeline
- **Start**: ASAP
- **End of Phase 1**: 2 weeks
- **End of Phase 2**: 5 weeks
- **End of Phase 3**: 7 weeks
- **End of Phase 4**: 8 weeks

## Risks and Mitigation

1. **Risk**: Breaking backward compatibility
   **Mitigation**: Thorough testing, semantic versioning

2. **Risk**: Increased code complexity
   **Mitigation**: Code reviews, documentation, usage examples

3. **Risk**: Resource shortage
   **Mitigation**: Task prioritization, community involvement

## References
- [Source code](https://gitverse.ru/zowers/cxx_modules_converter)
- [Documentation](README.md)
- [Test data](test_data/)
- [PyPI page](https://pypi.org/project/cxx-modules-converter/)

---
*Last updated: 2026-05-12*
*Document version: 1.3*
