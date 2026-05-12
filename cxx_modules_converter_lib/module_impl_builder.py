from __future__ import annotations

from .module_base_builder import ModuleBaseBuilder
from .module_interface_builder import ModuleInterfaceUnitBuilder
from .options import ContentType, FileOptions, Options
from .resolvers import FilesResolver


class ModuleImplUnitBuilder(ModuleBaseBuilder):
    content_type = ContentType.MODULE_IMPL
    '''
// Module implementation unit.

// File copyright

module;                    // Start of global module fragment.

<header includes>

module <name>;             // Start of module purview.

<extra module imports>     // Only additional to interface.

<module implementation>
    '''
    module_purview_start_prefix: str = 'module'

    def __init__(
        self,
        options: Options,
        parent_resolver: FilesResolver,
        file_options: FileOptions,
    ):
        super().__init__(options, parent_resolver, file_options)
        self._is_actually_module = False
        self.module_interface_builder: ModuleInterfaceUnitBuilder | None = None

    def set_is_actually_module(self) -> None:
        self._is_actually_module = True
        super().set_is_actually_module()

    def get_is_actually_module(self) -> bool:
        return self._is_actually_module

    def get_module_interface_builder(self) -> ModuleInterfaceUnitBuilder | None:
        return self.module_interface_builder

    def set_module_interface_builder(
        self, module_interface_builder: ModuleInterfaceUnitBuilder | None
    ):
        self.module_interface_builder = module_interface_builder
