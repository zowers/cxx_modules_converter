"""Custom exceptions for cxx_modules_converter."""

class CxxModulesConverterError(Exception):
    """Base exception for all cxx_modules_converter errors."""
    pass


class ConfigurationError(CxxModulesConverterError):
    """Raised when there is a configuration error."""
    pass


class ConversionError(CxxModulesConverterError):
    """Raised when a conversion error occurs."""
    pass


class FileSystemError(CxxModulesConverterError):
    """Raised when a file system operation fails."""
    pass


class ValidationError(CxxModulesConverterError):
    """Raised when input validation fails."""
    pass
