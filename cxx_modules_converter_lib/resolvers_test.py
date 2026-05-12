from pathlib import Path, PurePosixPath

from cxx_modules_converter_lib import (
    ContentType,
    ConvertAction,
    Converter,
    FileEntryType,
    FilesMap,
    FilesResolver,
    ModuleFilesResolver,
    Options,
)


def test_resolve_include():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('subdir/simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    assert resolver.module_dir == Path('subdir')
    assert resolver.resolve_include('simple.h', True) == PurePosixPath('simple.h')
    assert resolver.resolve_include('simple.h', False) is None
    # make `simple.h` available in subdir
    resolver.parent_resolver.files_map.add_files_map_dict(
        {
            'subdir': {
                'simple.h': FileEntryType.FILE,
            },
        }
    )
    assert resolver.resolve_include('simple.h', True) == PurePosixPath(
        'subdir/simple.h'
    )
    assert resolver.resolve_include('simple.h', False) is None
    # make `simple.h` available in root
    resolver.parent_resolver.files_map.add_files_map_dict(
        {
            'simple.h': FileEntryType.FILE,
        }
    )
    assert resolver.resolve_include('simple.h', False) == PurePosixPath('simple.h')


def test_resolve_include_no_dir():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    assert resolver.module_dir == Path('')
    assert resolver.resolve_include('simple.h', True) == PurePosixPath('simple.h')
    assert resolver.resolve_include('simple.h', False) is None
    # make `simple.h` available
    resolver.parent_resolver.files_map.add_files_map_dict(
        {
            'simple.h': FileEntryType.FILE,
        }
    )
    assert resolver.resolve_include('simple.h', False) == PurePosixPath('simple.h')


def test_resolve_include_to_module_name():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    assert resolver.resolve_include_to_module_name('simple.h', True) == 'simple'
    assert resolver.resolve_include_to_module_name('simple.h', False) is None
    assert (
        resolver.resolve_include_to_module_name('subdir/simple.h', True)
        == 'subdir.simple'
    )
    assert resolver.resolve_include_to_module_name('subdir/simple.h', False) is None
    # make `simple.h` available
    resolver.parent_resolver.files_map.add_files_map_dict(
        {
            'simple.h': FileEntryType.FILE,
        }
    )
    assert resolver.resolve_include_to_module_name('simple.h', False) == 'simple'
    assert resolver.resolve_include_to_module_name('subdir/simple.h', False) is None
    # make `subdir/simple.h` available
    resolver.parent_resolver.files_map.add_files_map_dict(
        {
            'subdir': {
                'simple.h': FileEntryType.FILE,
            }
        }
    )
    assert resolver.resolve_include_to_module_name('simple.h', False) == 'simple'
    assert (
        resolver.resolve_include_to_module_name('subdir/simple.h', False)
        == 'subdir.simple'
    )


def test_resolve_include_to_module_name_add_modules_path_subdir():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    assert (
        resolver.resolve_include_to_module_name('subdir/simple.h', True)
        == 'subdir.simple'
    )
    assert resolver.resolve_include_to_module_name('subdir/simple.h', False) is None
    resolver.options.add_modules_path('TestModule', 'subdir')
    assert (
        resolver.resolve_include_to_module_name('subdir/simple.h', True)
        == 'TestModule.simple'
    )
    assert (
        resolver.resolve_include_to_module_name('subdir/simple.h', False)
        == 'TestModule.simple'
    )
    assert (
        resolver.resolve_include_to_module_name('subdir/subdir2/simple.h', True)
        == 'TestModule.subdir2.simple'
    )
    assert (
        resolver.resolve_include_to_module_name('subdir/subdir2/simple.h', False)
        == 'TestModule.subdir2.simple'
    )


def test_resolve_include_to_module_name_add_modules_path_subdir_level2():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    assert (
        resolver.resolve_include_to_module_name('subdir/subdir2/simple.h', True)
        == 'subdir.subdir2.simple'
    )
    assert (
        resolver.resolve_include_to_module_name('subdir/subdir2/simple.h', False)
        is None
    )
    resolver.options.add_modules_path('TestModule', 'subdir/subdir2')
    assert (
        resolver.resolve_include_to_module_name('subdir/subdir2/simple.h', True)
        == 'TestModule.simple'
    )
    assert (
        resolver.resolve_include_to_module_name('subdir/subdir2/simple.h', False)
        == 'TestModule.simple'
    )


def test_resolve_include_to_module_name_add_modules_path_subdir_level2_in_subdir():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('subdir/simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    # make `simple.h` available in subdir
    resolver.parent_resolver.files_map.add_files_map_dict(
        {
            'subdir': {
                'subdir2': {
                    'simple.h': FileEntryType.FILE,
                },
            },
        }
    )
    assert (
        resolver.resolve_include_to_module_name('subdir2/simple.h', True)
        == 'subdir.subdir2.simple'
    )
    assert resolver.resolve_include_to_module_name('subdir2/simple.h', False) is None
    resolver.options.add_modules_path('TestModule', 'subdir/subdir2')
    assert (
        resolver.resolve_include_to_module_name('subdir2/simple.h', True)
        == 'TestModule.simple'
    )
    assert (
        resolver.resolve_include_to_module_name('subdir/subdir2/simple.h', True)
        == 'TestModule.simple'
    )
    assert resolver.resolve_include_to_module_name('subdir2/simple.h', False) is None
    assert (
        resolver.resolve_include_to_module_name('subdir/subdir2/simple.h', False)
        == 'TestModule.simple'
    )


def test_resolve_include_to_module_name_std():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    assert resolver.resolve_include_to_module_name('vector', False) is None
    resolver.options.add_std_module()
    assert resolver.resolve_include_to_module_name('vector', False) == 'std'


def test_resolve_include_to_module_name_std_compat():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    assert resolver.resolve_include_to_module_name('vector', False) is None
    resolver.options.add_std_compat_module()
    assert resolver.resolve_include_to_module_name('vector', False) == 'std.compat'


def test_resolve_include_to_module_name_std_w_root_name():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    assert resolver.resolve_include_to_module_name('vector', False) is None
    resolver.options.add_std_module()
    resolver.options.set_root_dir_module_name('TestModule')
    assert resolver.resolve_include_to_module_name('vector', False) == 'std'


def test_resolver_convert_filename_to_module_name():
    converter = Converter(ConvertAction.MODULES)
    assert (
        converter.resolver.convert_filename_to_module_name(PurePosixPath('simple.cpp'))
        == 'simple'
    )
    assert (
        converter.resolver.convert_filename_to_module_name(
            PurePosixPath('subdir/simple.cpp')
        )
        == 'subdir.simple'
    )


def test_FilesMap_add_filesystem_directory():
    files_map = FilesMap()
    files_map.add_filesystem_directory(Path('test_data/subdirs/input'))
    assert files_map.value == {
        'simple1.h': FileEntryType.FILE,
        'subdir1': {
            'simple1.h': FileEntryType.FILE,
            'simple2.h': FileEntryType.FILE,
            'subdir2': {
                'simple1.h': FileEntryType.FILE,
                'simple2.h': FileEntryType.FILE,
            },
        },
    }
    files_map.add_filesystem_directory(Path('test_data/other/input'))
    assert files_map.value == {
        'other.txt': FileEntryType.FILE,
        'simple1.h': FileEntryType.FILE,
        'subdir1': {
            'simple1.h': FileEntryType.FILE,
            'simple2.h': FileEntryType.FILE,
            'subdir2': {
                'simple1.h': FileEntryType.FILE,
                'simple2.h': FileEntryType.FILE,
            },
        },
    }


def test_FilesMap_add_map():
    files_map = FilesMap()
    files_map.add_files_map_dict(
        {
            'simple1.h': FileEntryType.FILE,
        }
    )
    assert files_map.value == {
        'simple1.h': FileEntryType.FILE,
    }
    files_map.add_files_map_dict(
        {
            'subdir1': {
                'simple2.h': FileEntryType.FILE,
            },
        }
    )
    assert files_map.value == {
        'simple1.h': FileEntryType.FILE,
        'subdir1': {
            'simple2.h': FileEntryType.FILE,
        },
    }


def test_FilesResolver_resolve_in_search_path_empty_map():
    options = Options()
    files_resolver = FilesResolver(options)
    assert files_resolver.resolve_in_search_path(
        Path(''), 'test', 'root.h', True
    ) == PurePosixPath('root.h')
    assert (
        files_resolver.resolve_in_search_path(Path(''), 'test', 'root.h', False) is None
    )
    assert files_resolver.resolve_in_search_path(
        Path('subdir1'), 'test', 'simple1.h', True
    ) == PurePosixPath('simple1.h')
    assert (
        files_resolver.resolve_in_search_path(
            Path('subdir1'), 'test', 'simple1.h', False
        )
        is None
    )


def test_ModuleFilesResolver_resolve_in_search_path():
    options = Options()
    files_resolver = FilesResolver(options)
    modules_resolver = ModuleFilesResolver(files_resolver, options)
    files_map = files_resolver.files_map
    files_map.add_files_map_dict(
        {
            'root.h': FileEntryType.FILE,
            'subdir1': {
                'simple1.h': FileEntryType.FILE,
                'subdir2': {
                    'simple2.h': FileEntryType.FILE,
                },
            },
            'dir2': {
                'simple1.h': FileEntryType.FILE,
                'subdir2': {
                    'simple2.h': FileEntryType.FILE,
                    'simple3.h': FileEntryType.FILE,
                },
            },
        }
    )
    modules_resolver.set_filename(Path('subdir1/test'))
    # check existing file from root
    assert modules_resolver.resolve_include(
        'subdir1/subdir2/simple2.h', True
    ) == PurePosixPath('subdir1/subdir2/simple2.h')
    assert modules_resolver.resolve_include(
        'subdir1/subdir2/simple2.h', False
    ) == PurePosixPath('subdir1/subdir2/simple2.h')
    # check existing file in relative subdir
    assert modules_resolver.resolve_include('subdir2/simple2.h', True) == PurePosixPath(
        'subdir1/subdir2/simple2.h'
    )
    assert modules_resolver.resolve_include('subdir2/simple2.h', False) is None
    # check missing file
    assert modules_resolver.resolve_include('subdir2/simple3.h', True) == PurePosixPath(
        'subdir2/simple3.h'
    )
    assert modules_resolver.resolve_include('subdir2/simple3.h', False) is None
    # add search path in another dir
    options.search_path.append('dir2')
    # check file existing in relative subdir and search path
    assert modules_resolver.resolve_include('subdir2/simple2.h', True) == PurePosixPath(
        'subdir1/subdir2/simple2.h'
    )
    assert modules_resolver.resolve_include(
        'subdir2/simple2.h', False
    ) == PurePosixPath('dir2/subdir2/simple2.h')
    # check file existing in search path but missing in relative subdir
    assert modules_resolver.resolve_include('subdir2/simple3.h', True) == PurePosixPath(
        'dir2/subdir2/simple3.h'
    )
    assert modules_resolver.resolve_include(
        'subdir2/simple3.h', False
    ) == PurePosixPath('dir2/subdir2/simple3.h')
    # check file missing in relative subdir and search path
    assert modules_resolver.resolve_include('subdir2/simple4.h', True) == PurePosixPath(
        'subdir2/simple4.h'
    )
    assert modules_resolver.resolve_include('subdir2/simple4.h', False) is None


def test_FilesResolver_convert_filename_to_module_name():
    options = Options()
    files_resolver = FilesResolver(options)
    files_map = files_resolver.files_map
    files_map.add_files_map_dict(
        {
            'root.h': FileEntryType.FILE,
            'subdir1': {
                'simple1.h': FileEntryType.FILE,
                'subdir2': {
                    'simple2.h': FileEntryType.FILE,
                },
            },
            'dir2': {
                'simple1.h': FileEntryType.FILE,
                'subdir2': {
                    'simple2.h': FileEntryType.FILE,
                    'simple3.h': FileEntryType.FILE,
                },
            },
        }
    )
    assert (
        files_resolver.convert_filename_to_module_name(PurePosixPath('root.h'))
        == 'root'
    )
    assert (
        files_resolver.convert_filename_to_module_name(
            PurePosixPath('subdir1/simple1.h')
        )
        == 'subdir1.simple1'
    )
    assert (
        files_resolver.convert_filename_to_module_name(PurePosixPath('missing.h'))
        == 'missing'
    )
    options.set_root_dir_module_name('org')
    assert (
        files_resolver.convert_filename_to_module_name(PurePosixPath('root.h'))
        == 'org.root'
    )
    assert (
        files_resolver.convert_filename_to_module_name(
            PurePosixPath('subdir1/simple1.h')
        )
        == 'org.subdir1.simple1'
    )
    assert (
        files_resolver.convert_filename_to_module_name(PurePosixPath('missing.h'))
        == 'missing'
    )


def test_FilesResolver_get_source_content_type():
    options = Options()
    files_resolver = FilesResolver(options)
    assert (
        files_resolver.get_source_content_type(ConvertAction.MODULES, Path('test.h'))
        == ContentType.HEADER
    )
    assert (
        files_resolver.get_source_content_type(ConvertAction.MODULES, Path('test.hpp'))
        == ContentType.OTHER
    )
    assert (
        files_resolver.get_source_content_type(ConvertAction.MODULES, Path('test.cpp'))
        == ContentType.CXX
    )
    assert (
        files_resolver.get_source_content_type(ConvertAction.MODULES, Path('test.cxx'))
        == ContentType.OTHER
    )
    # first use -- replace default
    options.add_module_action_ext_type(".hpp", ContentType.HEADER)
    assert (
        files_resolver.get_source_content_type(ConvertAction.MODULES, Path('test.h'))
        == ContentType.OTHER
    )
    assert (
        files_resolver.get_source_content_type(ConvertAction.MODULES, Path('test.hpp'))
        == ContentType.HEADER
    )
    # subsequent use -- append (+ no dot)
    options.add_module_action_ext_type("h", ContentType.HEADER)
    assert (
        files_resolver.get_source_content_type(ConvertAction.MODULES, Path('test.h'))
        == ContentType.HEADER
    )
    assert (
        files_resolver.get_source_content_type(ConvertAction.MODULES, Path('test.hpp'))
        == ContentType.HEADER
    )
    assert (
        files_resolver.get_source_content_type(ConvertAction.MODULES, Path('test.cpp'))
        == ContentType.CXX
    )
    assert (
        files_resolver.get_source_content_type(ConvertAction.MODULES, Path('test.cxx'))
        == ContentType.OTHER
    )

    # first use -- replace default
    options.add_module_action_ext_type(".cxx", ContentType.CXX)
    assert (
        files_resolver.get_source_content_type(ConvertAction.MODULES, Path('test.cpp'))
        == ContentType.OTHER
    )
    assert (
        files_resolver.get_source_content_type(ConvertAction.MODULES, Path('test.cxx'))
        == ContentType.CXX
    )
    # subsequent use -- append
    options.add_module_action_ext_type(".cpp", ContentType.CXX)
    assert (
        files_resolver.get_source_content_type(ConvertAction.MODULES, Path('test.cpp'))
        == ContentType.CXX
    )
    assert (
        files_resolver.get_source_content_type(ConvertAction.MODULES, Path('test.cxx'))
        == ContentType.CXX
    )
    assert (
        files_resolver.get_source_content_type(ConvertAction.MODULES, Path('test.h'))
        == ContentType.HEADER
    )
    assert (
        files_resolver.get_source_content_type(ConvertAction.MODULES, Path('test.hpp'))
        == ContentType.HEADER
    )


def test_FilesResolver_convert_filename_to_content_type():
    options = Options()
    files_resolver = FilesResolver(options)
    assert (
        files_resolver.convert_filename_to_content_type(
            Path('test.h'), ContentType.MODULE_INTERFACE
        )
        == 'test.cppm'
    )
    assert (
        files_resolver.convert_filename_to_content_type(
            Path('test.cpp'), ContentType.MODULE_IMPL
        )
        == 'test.cpp'
    )
    options.set_output_content_type_to_ext(ContentType.MODULE_INTERFACE, '.ixx')
    options.set_output_content_type_to_ext(ContentType.MODULE_IMPL, 'cxx')
    assert (
        files_resolver.convert_filename_to_content_type(
            Path('test.h'), ContentType.MODULE_INTERFACE
        )
        == 'test.ixx'
    )
    assert (
        files_resolver.convert_filename_to_content_type(
            Path('test.cpp'), ContentType.MODULE_IMPL
        )
        == 'test.cxx'
    )


def test_resolve_include_to_module_name_use_full_name_true():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    resolver.set_module_name('test_module')
    resolver.parent_resolver.files_map.add_files_map_dict(
        {
            'simple.h': FileEntryType.FILE,
        }
    )
    assert resolver.resolve_include_to_module_name('simple.h', False, True) == 'simple'


def test_resolve_include_to_module_name_use_full_name_false_same_external_module():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    resolver.set_module_name('mymodule:partition1')
    resolver.parent_resolver.files_map.add_files_map_dict(
        {
            'simple.h': FileEntryType.FILE,
        }
    )
    resolver.parent_resolver.files_map.add_files_map_dict(
        {
            'subdir': {
                'simple2.h': FileEntryType.FILE,
            }
        }
    )
    resolver.options.add_join_configuration('mymodule', 'subdir/*')
    assert (
        resolver.resolve_include_to_module_name('subdir/simple2.h', False, False)
        == ':simple2'
    )


def test_resolve_include_to_module_name_use_full_name_false_different_external_module():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    resolver.set_module_name('mymodule:partition1')
    resolver.parent_resolver.files_map.add_files_map_dict(
        {
            'simple.h': FileEntryType.FILE,
        }
    )
    resolver.parent_resolver.files_map.add_files_map_dict(
        {
            'otherdir': {
                'simple2.h': FileEntryType.FILE,
            }
        }
    )
    resolver.options.add_join_configuration('othermodule', 'otherdir/*')
    assert (
        resolver.resolve_include_to_module_name('otherdir/simple2.h', False, False)
        == 'othermodule'
    )


def test_resolve_include_to_module_name_use_full_name_false_no_partition():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    resolver.set_module_name('mymodule')
    resolver.parent_resolver.files_map.add_files_map_dict(
        {
            'subdir': {
                'simple.h': FileEntryType.FILE,
            }
        }
    )
    resolver.options.add_join_configuration('mymodule', 'subdir/*')
    assert (
        resolver.resolve_include_to_module_name('subdir/simple.h', False, False)
        == ':simple'
    )


def test_resolve_include_to_module_name_use_full_name_false_no_current_module():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    resolver.parent_resolver.files_map.add_files_map_dict(
        {
            'simple.h': FileEntryType.FILE,
        }
    )
    assert resolver.resolve_include_to_module_name('simple.h', False, False) == 'simple'


def test_resolve_include_to_module_name_use_full_name_false_std_module():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    resolver.set_module_name('mymodule:partition1')
    resolver.options.add_std_module()
    assert resolver.resolve_include_to_module_name('vector', False, False) == 'std'


def test_resolve_include_to_module_name_use_full_name_false_std_compat_module():
    converter = Converter(ConvertAction.MODULES)
    builder = converter.make_builder_to_module('simple.cpp', ContentType.CXX)
    resolver = builder.resolver
    resolver.set_module_name('mymodule:partition1')
    resolver.options.add_std_compat_module()
    assert (
        resolver.resolve_include_to_module_name('vector', False, False) == 'std.compat'
    )


# Tests for cycle detection function
