from __future__ import annotations

from .options import (
    ConvertAction,
    ContentType,
    Options,
    FileOptions,
    FileEntryType,
    COMPAT_MACRO_DEFAULT,
    always_include_names,
)
from .resolvers import FilesResolver, ModuleFilesResolver, FilesMap
from .file_processing import FileContent, Matcher, HeaderScanState, LineCompatibility
from .file_base_builder import FileBaseBuilder, FileProcessingState
from .module_base_builder import ModuleBaseBuilder, any_pattern_maches
from .module_interface_builder import ModuleInterfaceUnitBuilder
from .module_impl_builder import ModuleImplUnitBuilder
from .compat_header_builder import CompatHeaderBuilder
from .converter import Converter, convert_file_content, find_cycles, convert_directory
from .exceptions import (
    CxxModulesConverterError,
    ConfigurationError,
    ConversionError,
    FileSystemError,
    ValidationError,
)

__all__ = [
    'ConvertAction',
    'ContentType',
    'Options',
    'FileOptions',
    'FileEntryType',
    'COMPAT_MACRO_DEFAULT',
    'always_include_names',
    'FilesResolver',
    'ModuleFilesResolver',
    'FilesMap',
    'FileContent',
    'Matcher',
    'HeaderScanState',
    'LineCompatibility',
    'FileBaseBuilder',
    'FileProcessingState',
    'ModuleBaseBuilder',
    'any_pattern_maches',
    'ModuleInterfaceUnitBuilder',
    'ModuleImplUnitBuilder',
    'CompatHeaderBuilder',
    'Converter',
    'convert_file_content',
    'find_cycles',
    'convert_directory',
    'CxxModulesConverterError',
    'ConfigurationError',
    'ConversionError',
    'FileSystemError',
    'ValidationError',
]
