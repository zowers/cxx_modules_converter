from __future__ import annotations

import os
from .options import Options, ContentType
from .module_base_builder import ModuleBaseBuilder
from .file_base_builder import FileBaseBuilder
from .exceptions import ConfigurationError
from .file_processing import new_line


class CompatHeaderBuilder(FileBaseBuilder):
    content_type = ContentType.HEADER
    def __init__(self, options: Options, module_builder: ModuleBaseBuilder):
        super().__init__(options, module_builder.parent_resolver)
        self.module_builder: ModuleBaseBuilder = module_builder
        if module_builder.content_type != ContentType.MODULE_INTERFACE:
            raise ConfigurationError(f"CompatHeaderBuilder requires MODULE_INTERFACE builder, got {module_builder.content_type}")
        module_interface_unit_filename: str = module_builder.converted_filename()
        if not module_interface_unit_filename:
            raise ConfigurationError("module_interface_unit_filename is empty")
        self.relative_module_interface_unit_filename: str = os.path.basename(module_interface_unit_filename)

    def build_result(self) -> str:
        compat_macro = self.options.compat_macro
        if not compat_macro:
            raise ConfigurationError("compat_macro is not set in options")
        relative_module_interface_unit_filename = self.relative_module_interface_unit_filename
        parts = [
            f'''#pragma once''',
            f'''#ifndef {compat_macro}''',
            f'''#define {compat_macro}''',
            f'''#include "{relative_module_interface_unit_filename}"''',
            f'''#undef {compat_macro}''',
            f'''#else''',
            f'''#include "{relative_module_interface_unit_filename}"''',
            f'''#endif''',
        ]
        return new_line.join(parts) + new_line
