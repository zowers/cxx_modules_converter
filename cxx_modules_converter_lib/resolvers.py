from __future__ import annotations

import fnmatch
import logging
import os
from pathlib import Path, PurePosixPath
from typing import TypeAlias

from .options import (
    ConvertAction,
    ContentType,
    Options,
    FileEntryType,
    ExtTypes,
    STD_MODULE,
    STD_COMPAT_MODULE,
    STD_MODULE_PATHS,
)
from .exceptions import ValidationError

# Type aliases
FilesMapDict: TypeAlias = dict[str, "FilesMapDict | FileEntryType"]
ActionExtTypes: TypeAlias = dict[ConvertAction, ExtTypes]
EmptyPath = PurePosixPath('')

class FilesMap:
    def __init__(self):
        self.value: FilesMapDict = {}

    def find(self, path: PurePosixPath) -> FilesMapDict | FileEntryType | None:
        value: FilesMapDict = self.value
        for part in path.parts:
            if not value:
                break
            nextValue = value.get(part, None)
            if type(nextValue) is not dict:
                return nextValue
            value = nextValue
        return value

    def add_filesystem_directory(self, path: Path):
        for (root, dirs, files) in os.walk(path):
            relative_root = Path(os.path.relpath(root, path))
            if relative_root == Path(''):
                root_node: FilesMapDict = self.value
            else:
                parent_node = self.find(PurePosixPath(relative_root.parent))
                if not isinstance(parent_node, dict):
                    raise RuntimeError(f"Expected dict for parent node, got {type(parent_node).__name__}")
                root_node = parent_node[relative_root.name] = {}

            for name in dirs:
                root_node[name] = {}
            for name in files:
                root_node[name] = FileEntryType.FILE
    
    def add_files_map_dict(self, other: FilesMapDict):
        self.value.update(other)


class FilesResolver:
    def __init__(self, options: Options):
        self.options: Options = options
        self.files_map = FilesMap()
        self.source_ext_types: ActionExtTypes = {
            ConvertAction.MODULES: self.options.modules_ext_types,
            ConvertAction.HEADERS: self.options.headers_ext_types,
        }
        self.destination_ext_types: ActionExtTypes = {
            ConvertAction.HEADERS: self.options.modules_ext_types,
            ConvertAction.MODULES: self.options.headers_ext_types,
        }
    
    def resolve_in_search_path(self, current_dir: Path, current_filename: str|Path, include_filename: str, is_quote: bool) -> PurePosixPath | None:
        include_path = PurePosixPath(include_filename)
        # search relative to root
        if self.files_map.find(include_path):
            return include_path
        # search relative to current_dir
        full_path = PurePosixPath(current_dir.joinpath(include_path))
        if is_quote and self.files_map.find(full_path):
            return full_path
        # search in search_path
        for search_path_item in self.options.search_path:
            path = PurePosixPath(search_path_item).joinpath(include_path)
            if self.files_map.find(path):
                return path
        if is_quote:
            logging.warning(f'file not found: "{include_filename}" referenced from "{current_filename}"')
            return include_path
        return None

    def convert_filename_to_module_name(self, filename: PurePosixPath) -> str:
        base_module = None
        root_dir_module_name = self.options.root_dir_module_name()
        if root_dir_module_name and self.files_map.find(filename):
            base_module = root_dir_module_name
        module_name = self.filename_to_module_name(filename, base_module)
        return module_name

    def filename_to_module_name(self, filename: PurePosixPath, base_module: str|None) -> str:
        matched_target_module = None
        matched_pattern_dir = None
        for pattern, target_module in self.options.join_configurations.items():
            if fnmatch.fnmatchcase(filename.as_posix(), pattern):
                is_star_pattern = pattern == '*'
                is_slash_star_pattern = pattern.endswith('/*')
                
                if is_star_pattern or is_slash_star_pattern:
                    if is_star_pattern:
                        pattern_dir = ''
                    else:
                        pattern_dir = pattern[:-2]
                    
                    if is_star_pattern or filename.as_posix().startswith(pattern_dir + '/'):
                        matched_target_module = target_module
                        matched_pattern_dir = pattern_dir
                        break
        
        if matched_target_module is not None and matched_pattern_dir is not None:
            remaining_path = filename.as_posix()[len(matched_pattern_dir):]
            if remaining_path.startswith('/'):
                remaining_path = remaining_path[1:]
            remaining_path = remaining_path.split('.')[0]
            remaining_path = remaining_path.replace('/', '.')
            return f"{matched_target_module}:{remaining_path}"
        
        filenameStr, _ = os.path.splitext(filename)
        parts = list(PurePosixPath(filenameStr).parts)
        if base_module:
            parts.insert(0, base_module)
        result = '.'.join(parts)
        if result.startswith('.'):
            result = result[1:]
        return result

    def get_source_content_type(self, action: ConvertAction, filename: Path) -> ContentType:
        parts = os.path.splitext(filename)
        extension = parts[-1]
        action_ext_types = self.source_ext_types[action]
        return action_ext_types.get(extension, ContentType.OTHER)

    def convert_filename_to_content_type(self, filename: Path, content_type: ContentType) -> str:
        parts = os.path.splitext(filename)
        new_extension = self.options.content_type_to_ext[content_type]
        new_filename = parts[0] + new_extension
        return new_filename
    
    def make_defined_module_for_path(self, filename: PurePosixPath) -> str | None:
        inmodule_path = EmptyPath
        while True:
            module_prefix = self.options.path_to_module_prefix_map.get(filename, None)
            if module_prefix is not None:
                if filename == EmptyPath:
                    return self.convert_filename_to_module_name(filename)
                else:
                    return self.filename_to_module_name(inmodule_path, module_prefix)
            name = PurePosixPath(filename.name)
            if inmodule_path == EmptyPath:
                inmodule_path = PurePosixPath(self.filename_to_module_name(name, ''))
            else:
                inmodule_path = name.joinpath(inmodule_path)
            # go up
            filename = filename.parent
            if filename == EmptyPath:
                break
        return None


class ModuleFilesResolver:
    def __init__(self, parent_resolver: FilesResolver, options: Options):
        self.parent_resolver: FilesResolver = parent_resolver
        self.options: Options = options
        self.module_filename: Path = Path()
        self.module_dir: Path = Path()
        self.module_name: str | None = None

    def set_module_name(self, name: str):
        self.module_name = name

    def set_filename(self, filename: Path):
        self.module_filename = filename
        self.module_dir = self.module_filename.parent

    def resolve_include(self, include_filename: str, is_quote: bool) -> PurePosixPath | None:
        result = self.parent_resolver.resolve_in_search_path(self.module_dir, self.module_filename, include_filename, is_quote)
        return result

    def resolve_include_to_module_name(self, include_filename: str, is_quote: bool, use_full_name: bool = False) -> str | None:
        resolved_include_filename = self.parent_resolver.resolve_in_search_path(self.module_dir, self.module_filename, include_filename, is_quote)
        if resolved_include_filename is None:
            result = self.parent_resolver.make_defined_module_for_path(PurePosixPath(include_filename))
            return self.get_module_name_for_import(result, use_full_name) if result else result
        result = self.parent_resolver.make_defined_module_for_path(resolved_include_filename)
        if result is not None:
            return self.get_module_name_for_import(result, use_full_name)
        result = self.parent_resolver.convert_filename_to_module_name(resolved_include_filename)
        return self.get_module_name_for_import(result, use_full_name)

    def get_module_name_for_import(self, module_name: str, use_full_name: bool) -> str:
        if use_full_name:
            return module_name
        
        module_parts = module_name.split(':', 1)
        external_module_name = module_parts[0]
        
        if self.module_name and len(module_parts) > 1:
            partition_name = module_parts[1]
            
            current_module_parts = self.module_name.split(':', 1)
            current_external_module_name = current_module_parts[0]
            
            if external_module_name == current_external_module_name:
                return ':' + partition_name
        
        return external_module_name
