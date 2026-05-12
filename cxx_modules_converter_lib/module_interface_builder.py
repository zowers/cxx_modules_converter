from __future__ import annotations

from .module_base_builder import ModuleBaseBuilder
from .options import ContentType, FileOptions, Options
from .resolvers import FilesResolver


class ModuleInterfaceUnitBuilder(ModuleBaseBuilder):
    content_type = ContentType.MODULE_INTERFACE
    '''
    // Module interface unit.

    // File copyright

    module;                    // Start of global module fragment.

    <header includes>

    export module <name>;      // Start of module purview.

    <module imports>

    <special header includes>  // Configuration, export, etc.

    <module interface>

    <inline/template includes>
    '''
    module_purview_start_prefix: str = 'export module'

    def __init__(
        self,
        options: Options,
        parent_resolver: FilesResolver,
        file_options: FileOptions,
    ):
        super().__init__(options, parent_resolver, file_options)
        self.partitions: list[ModuleInterfaceUnitBuilder] = []

    def set_is_actually_module(self) -> None:
        pass

    def get_is_actually_module(self) -> bool:
        '''module interface unit is always actually module'''
        return True

    def get_module_interface_builder(self) -> 'ModuleInterfaceUnitBuilder | None':
        return None

    def get_is_partition(self) -> bool:
        return ':' in self.module_name

    def get_external_module_name(self) -> str:
        if self.get_is_partition():
            return self.module_name.split(':', 1)[0]
        return self.module_name

    def get_partition_name(self) -> str:
        if self.get_is_partition():
            return self.module_name.split(':', 1)[1]
        return ''

    def add_partition(self, partition_builder: 'ModuleInterfaceUnitBuilder') -> None:
        assert not self.get_is_partition(), "A partition cannot have partitions"
        self.partitions.append(partition_builder)

    def build_result(self):
        if self.partitions:
            partition_names: list[str] = []
            for partition_builder in self.partitions:
                if partition_builder.get_is_partition():
                    partition_name: str = partition_builder.get_partition_name()
                    partition_names.append(f":{partition_name}")
            partition_names.sort()

            self.add_module_content('')

            for partition_name in partition_names:
                self.add_module_content(f'''export import {partition_name};''')

        return super().build_result()
