from __future__ import annotations

from .compat_header_builder import CompatHeaderBuilder
from .converter import Converter, convert_directory, convert_file_content, find_cycles
from .exceptions import (
    ConfigurationError,
    ConversionError,
    CxxModulesConverterError,
    FileSystemError,
    ValidationError,
)
from .file_base_builder import FileBaseBuilder, FileProcessingState
from .file_processing import (
    FileContent,
    HeaderScanState,
    LineCompatibility,
    Matcher,
    ModuleLine,
    ModuleLineKind,
    ParsedModuleFile,
    find_declared_module,
    parse_module_file,
    process_header_content,
)
from .header_builder import HeaderBuilder
from .module_base_builder import ModuleBaseBuilder, any_pattern_maches
from .module_impl_builder import ModuleImplUnitBuilder
from .module_interface_builder import ModuleInterfaceUnitBuilder
from .options import (
    COMPAT_MACRO_DEFAULT,
    ContentType,
    ConvertAction,
    FileEntryType,
    FileOptions,
    Options,
    always_include_names,
)
from .resolvers import FilesMap, FilesResolver, ModuleFilesResolver

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
    'HeaderBuilder',
    'ModuleLine',
    'ModuleLineKind',
    'ParsedModuleFile',
    'find_declared_module',
    'parse_module_file',
    'process_header_content',
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
