from __future__ import annotations

import copy
import logging
import shutil
from pathlib import Path, PurePosixPath
from typing import cast

from .compat_header_builder import CompatHeaderBuilder
from .exceptions import ConversionError
from .file_processing import (
    FileContent,
    FileContentList,
    find_declared_module,
    get_converted_content_type,
    interface_content_types,
    parse_module_file,
    process_header_content,
)
from .header_builder import HeaderBuilder
from .module_base_builder import ModuleBaseBuilder, any_pattern_maches
from .module_impl_builder import ModuleImplUnitBuilder
from .module_interface_builder import ModuleInterfaceUnitBuilder
from .options import ContentType, ConvertAction, FileOptions, Options
from .resolvers import FilesResolver


class Converter:
    """Main converter class that orchestrates conversion between headers and modules.

    Attributes:
        action (ConvertAction): Conversion direction (MODULES or HEADERS).
        options (Options): Configuration options for the conversion.
        resolver (FilesResolver): File resolver instance.
        all_files (int): Total number of files processed.
        convertable_files (int): Number of files that can be converted.
        converted_files (int): Number of files successfully converted.
        copied_files (int): Number of files copied unchanged.
        module_interface_builders (dict[str, ModuleInterfaceUnitBuilder]):
            Builders for module interface units.
        joint_module_builders (dict[str, ModuleInterfaceUnitBuilder]):
            Builders for joined modules.
        module_dependencies (dict[str, set[str]]): Graph of module dependencies.
        circular_dependencies (list[list[str]]): Detected circular dependency cycles.
    """

    def __init__(self, action: ConvertAction):
        """Initialize a converter with the given action.

        Args:
            action: Whether to convert to modules (MODULES) or to headers (HEADERS).
        """
        self.action = action
        self.options = Options()
        self.resolver = FilesResolver(self.options)
        self.all_files = 0
        self.convertable_files = 0
        self.converted_files = 0
        self.copied_files = 0
        self.module_interface_builders: dict[str, ModuleInterfaceUnitBuilder] = {}
        self.joint_module_builders: dict[str, ModuleInterfaceUnitBuilder] = {}
        # dependency graph: module_name -> set of imported modules
        self.module_dependencies: dict[str, set[str]] = {}
        # list of found circular dependencies
        self.circular_dependencies: list[list[str]] = []
        self.header_filenames_by_module: dict[str, Path] = {}
        self.output_sources: dict[Path, Path] = {}

    def convert_file_content_to_module(
        self,
        content: str,
        filename: Path,
        content_type: ContentType,
        file_options: FileOptions,
    ) -> FileContentList:
        if content_type in {ContentType.MODULE_INTERFACE, ContentType.MODULE_IMPL}:
            return [FileContent(filename, content_type, content)]

        builder = self.make_builder_to_module(filename, content_type, file_options)
        process_header_content(content, builder)

        result: FileContentList = []
        result.append(builder.build_file_content())

        module_dependencies = builder.get_module_dependencies()
        self.add_module_dependencies(builder.module_name, module_dependencies)

        if (
            file_options.convert_as_compat
            and builder.content_type == ContentType.MODULE_INTERFACE
        ):
            compat_header_builder = CompatHeaderBuilder(self.options, builder)
            compat_header_builder.set_source_filename(Path(filename))
            result.append(compat_header_builder.build_file_content())

        return result

    def make_builder_to_module(
        self,
        filename: str | Path,
        content_type: ContentType,
        file_options: FileOptions | None = None,
    ) -> ModuleBaseBuilder:
        filename = Path(filename)
        if not file_options:
            file_options = FileOptions()
        match content_type:
            case ContentType.HEADER:
                pure_filename = PurePosixPath(filename)
                module_name = self.resolver.make_defined_module_for_path(pure_filename)
                if not module_name:
                    module_name = self.resolver.convert_filename_to_module_name(
                        pure_filename
                    )
                if module_name in self.joint_module_builders:
                    builder = self.joint_module_builders[module_name]
                else:
                    builder = ModuleInterfaceUnitBuilder(
                        self.options, self.resolver, file_options
                    )
            case ContentType.CXX:
                builder = ModuleImplUnitBuilder(
                    self.options, self.resolver, file_options
                )
            case _:
                raise RuntimeError(f'Unknown content type {content_type}')

        builder.set_source_filename(filename)

        if content_type == ContentType.HEADER:
            interface_builder = cast(ModuleInterfaceUnitBuilder, builder)
            self._add_module_interface_builder(interface_builder)
            if interface_builder.get_is_partition():
                self._associate_partition_with_joint_builder(
                    interface_builder, file_options
                )
        elif content_type == ContentType.CXX:
            cast(ModuleImplUnitBuilder, builder).set_module_interface_builder(
                self.module_interface_builders.get(builder.module_name, None)
            )
        return builder

    def _associate_partition_with_joint_builder(
        self, builder: ModuleInterfaceUnitBuilder, file_options: FileOptions
    ):
        target_module_name = builder.get_external_module_name()
        if target_module_name not in self.joint_module_builders:
            if target_module_name in self.module_interface_builders:
                joint_builder = self.module_interface_builders[target_module_name]
            else:
                joint_builder = ModuleInterfaceUnitBuilder(
                    self.options, self.resolver, file_options
                )
                module_filename = Path(
                    target_module_name
                    + self.options.content_type_to_ext[ContentType.MODULE_INTERFACE]
                )
                joint_builder.set_source_filename(module_filename)
                joint_builder.set_module_name(target_module_name)
            self._add_joint_module_builder(joint_builder)
        self.joint_module_builders[target_module_name].add_partition(builder)

    def _add_module_interface_builder(
        self, builder: ModuleInterfaceUnitBuilder
    ) -> None:
        self.module_interface_builders[builder.module_name] = builder

    def _add_joint_module_builder(self, builder: ModuleInterfaceUnitBuilder) -> None:
        self.joint_module_builders[builder.module_name] = builder

    def convert_file_content_to_headers(
        self,
        content: str,
        filename: Path,
        content_type: ContentType,
        file_options: FileOptions,
    ) -> FileContentList:
        if content_type not in {
            ContentType.MODULE_INTERFACE,
            ContentType.MODULE_IMPL,
        }:
            return [FileContent(filename, content_type, content)]

        parsed_file = parse_module_file(content, filename, self.options.compat_macro)
        converted_type = get_converted_content_type(content_type)
        converted_filename = Path(
            self.resolver.convert_filename_to_content_type(filename, converted_type)
        )
        if content_type == ContentType.MODULE_INTERFACE and parsed_file.declared_module:
            self._register_module_header(
                parsed_file.declared_module, converted_filename
            )

        builder = HeaderBuilder(
            self.options,
            self.resolver,
            content_type,
            parsed_file,
            self.header_filenames_by_module,
        )
        builder.set_source_filename(filename)
        return [builder.build_file_content()]

    def _register_module_header(self, module_name: str, filename: Path) -> None:
        existing_filename = self.header_filenames_by_module.get(module_name)
        if existing_filename is not None and existing_filename != filename:
            raise ConversionError(
                f'Module "{module_name}" is declared by both '
                f'"{existing_filename}" and "{filename}"'
            )
        self.header_filenames_by_module[module_name] = filename

    def convert_file_content(
        self,
        content: str,
        filename: str | Path,
        file_options: FileOptions | None = None,
    ) -> FileContentList:
        filename = Path(filename)
        if file_options is None:
            file_options = FileOptions()
        action = self.action
        content_type = self.resolver.get_source_content_type(action, filename)
        match action:
            case ConvertAction.MODULES:
                return self.convert_file_content_to_module(
                    content, filename, content_type, file_options
                )
            case ConvertAction.HEADERS:
                return self.convert_file_content_to_headers(
                    content, filename, content_type, file_options
                )
            case _:  # type: ignore
                raise RuntimeError(f'Unknown action: "{action}"')

    def convert_file(
        self,
        source_directory: Path,
        destination_directory: Path,
        filename: Path,
        file_options: FileOptions,
    ) -> FileContentList:
        self.convertable_files += 1
        with open(source_directory.joinpath(filename)) as source_file:
            source_content = source_file.read()
        converted_files = self.convert_file_content(
            source_content, filename, file_options
        )
        for converted_file in converted_files:
            converted_content = converted_file.content
            converted_filename = converted_file.filename
            self._create_or_update_file_content_if_diff(
                destination_directory.joinpath(converted_filename), converted_content
            )
        return converted_files

    def _create_or_update_file_content_if_diff(self, file_path: Path, content: str):
        if file_path.exists():
            with open(file_path, 'r') as existing_destination_file:
                existing_file_content = existing_destination_file.read()
                if existing_file_content == content:
                    return
        with open(file_path, 'w') as destination_file:
            destination_file.write(content)
        self.converted_files += 1

    def convert_or_copy_file(
        self,
        source_directory: Path,
        destination_directory: Path,
        filename: Path,
        file_options: FileOptions,
    ):
        self.all_files += 1
        content_type = self.resolver.get_source_content_type(self.action, filename)
        if content_type == ContentType.OTHER or any_pattern_maches(
            self.options.always_include_names, PurePosixPath(filename)
        ):
            self._copy_file_content_if_diff(
                source_directory.joinpath(filename),
                destination_directory.joinpath(filename),
            )
        else:
            logging.info(f'converting {filename}')
            converted_files = self.convert_file(
                source_directory, destination_directory, filename, file_options
            )
            for converted_file in converted_files:
                logging.info(
                    f'converted {converted_file.filename}\t{converted_file.content_type}'  # noqa: E501
                )

    def _copy_file_content_if_diff(
        self, source_file_path: Path, destination_file_path: Path
    ):
        with open(source_file_path, 'rb') as source_file:
            source_file_content = source_file.read()
        if destination_file_path.exists():
            with open(destination_file_path, 'rb') as existing_destination_file:
                existing_file_content = existing_destination_file.read()
                if existing_file_content == source_file_content:
                    return
        shutil.copy2(source_file_path, destination_file_path)
        self.copied_files += 1

    def convert_directory(self, source_directory: Path, destination_directory: Path):
        source_directory = Path(source_directory)
        destination_directory = Path(destination_directory)
        if (
            self.options.root_dir
            and self.options.root_dir != Path()
            and source_directory != self.options.root_dir
        ):
            self.add_filesystem_directory(self.options.root_dir)
            if self.action == ConvertAction.HEADERS:
                self._index_module_interfaces(
                    self.options.root_dir,
                    source_directory.relative_to(self.options.root_dir),
                )
            self.convert_directory_impl(
                self.options.root_dir,
                destination_directory,
                source_directory.relative_to(self.options.root_dir),
                FileOptions(),
            )
        else:
            self.add_filesystem_directory(source_directory)
            if self.action == ConvertAction.HEADERS:
                self._index_module_interfaces(source_directory, Path())
            self.convert_directory_impl(
                source_directory, destination_directory, Path(), FileOptions()
            )

        self.create_joined_module_files(destination_directory)
        self.print_circular_dependencies()

    def _index_module_interfaces(self, source_directory: Path, subdir: Path) -> None:
        scan_directory = source_directory.joinpath(subdir)
        for filepath in scan_directory.rglob('*'):
            if not filepath.is_file():
                continue
            filename = filepath.relative_to(source_directory)
            if any_pattern_maches(self.options.skip_patterns, PurePosixPath(filename)):
                continue
            content_type = self.resolver.get_source_content_type(
                ConvertAction.HEADERS, filename
            )
            if content_type not in {
                ContentType.MODULE_INTERFACE,
                ContentType.MODULE_IMPL,
            }:
                continue
            converted_type = get_converted_content_type(content_type)
            output_filename = Path(
                self.resolver.convert_filename_to_content_type(filename, converted_type)
            )
            existing_source = self.output_sources.get(output_filename)
            if existing_source is not None and existing_source != filename:
                raise ConversionError(
                    f'Both "{existing_source}" and "{filename}" convert to '
                    f'"{output_filename}"'
                )
            output_path = source_directory / output_filename
            if output_path.exists() and output_path != filepath:
                raise ConversionError(
                    f'Cannot convert "{filename}": output file '
                    f'"{output_filename}" already exists'
                )
            self.output_sources[output_filename] = filename
            if content_type != ContentType.MODULE_INTERFACE:
                continue
            with open(filepath) as source_file:
                content = source_file.read()
            module_name = find_declared_module(content)
            if not module_name:
                continue
            self._register_module_header(module_name, output_filename)

    def create_joined_module_files(self, destination_directory: Path):
        for _, joint_builder in self.joint_module_builders.items():
            file_content = joint_builder.build_file_content()
            output_path = destination_directory / file_content.filename
            self._create_or_update_file_content_if_diff(
                output_path, file_content.content
            )

    def add_module_dependencies(
        self, module_name: str, imported_module_names: set[str]
    ) -> None:
        if module_name not in self.module_dependencies:
            self.module_dependencies[module_name] = set()
        self.module_dependencies[module_name].update(imported_module_names)

    def print_circular_dependencies(self) -> None:
        self.circular_dependencies = find_cycles(self.module_dependencies)

        if not self.circular_dependencies:
            return

        circular_dependencies_count = len(self.circular_dependencies)
        logging.warning(
            f"Circular dependencies detected, count: {circular_dependencies_count}"
        )
        for i, cycle in enumerate(self.circular_dependencies, 1):
            cycle_str = " -> ".join(cycle)
            logging.warning(
                f"Circular dependency {i}/{circular_dependencies_count}: {cycle_str}"
            )

    def add_filesystem_directory(self, directory: Path):
        logging.info(f'adding filesystem directory {directory}')
        self.resolver.files_map.add_filesystem_directory(directory)

    def convert_directory_impl(
        self,
        source_directory: Path,
        destination_directory: Path,
        subdir: Path,
        file_options: FileOptions,
    ):
        source_directory_w_subdir = source_directory.joinpath(subdir or '')
        destination_directory_w_subdir = destination_directory.joinpath(subdir or '')
        destination_directory_w_subdir.mkdir(parents=True, exist_ok=True)
        for filepath in sorted(
            source_directory_w_subdir.iterdir(),
            key=lambda filepath: self.interface_then_impl_key(filepath),
        ):
            filename = filepath.relative_to(source_directory)
            if any_pattern_maches(self.options.skip_patterns, PurePosixPath(filename)):
                logging.info(f'skipping "{filename}"')
                continue
            next_file_options = self.make_next_file_options(file_options, filename)
            if filepath.is_file():
                self.convert_or_copy_file(
                    source_directory, destination_directory, filename, next_file_options
                )
            if filepath.is_dir():
                self.convert_directory_impl(
                    source_directory, destination_directory, filename, next_file_options
                )

    def interface_then_impl_key(self, file_path: Path):
        content_type = self.resolver.get_source_content_type(self.action, file_path)
        if content_type in interface_content_types:
            return 0
        return 1

    def make_next_file_options(self, file_options: FileOptions, filename: Path):
        next_file_options = copy.copy(file_options)
        if not file_options.convert_as_compat:
            convert_as_compat = any_pattern_maches(
                self.options.compat_patterns, PurePosixPath(filename)
            )
            if convert_as_compat:
                next_file_options.convert_as_compat = convert_as_compat
        return next_file_options


def convert_file_content(action: ConvertAction, content: str, filename: str) -> str:
    converter = Converter(action)
    file_content_list: FileContentList = converter.convert_file_content(
        content, filename, FileOptions()
    )
    return file_content_list[0].content


def find_cycles(dependencies: dict[str, set[str]]) -> list[list[str]]:
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []
    cycles: list[list[str]] = []

    def dfs(node: str) -> None:
        if node in rec_stack:
            # Cycle detected
            try:
                cycle_start_index = path.index(node)
                cycle = path[cycle_start_index:] + [node]
                # Skip self-references (A -> A)
                if len(cycle) > 1:
                    cycles.append(cycle)
            except ValueError:
                pass
            return

        if node in visited:
            return

        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        # Recursively traverse all neighbors
        if node in dependencies:
            for neighbor in dependencies[node]:
                # Skip self-dependencies
                if neighbor != node:
                    dfs(neighbor)

        path.pop()
        rec_stack.remove(node)

    # Run DFS for all nodes
    for node in dependencies:
        if node not in visited:
            dfs(node)

    return cycles


def convert_directory(
    action: ConvertAction,
    source_directory: Path,
    destination_directory: Path,
    subdir: str | None = None,
):
    converter = Converter(action)
    return converter.convert_directory(source_directory, destination_directory)
