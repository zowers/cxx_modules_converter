from pathlib import PurePosixPath
from cxx_modules_converter_lib import (
    Converter,
    ConvertAction,
    FileEntryType,
    Options,
    FilesResolver,
    )


def test_add_join_configuration():
    options = Options()
    options.add_join_configuration('mymodule', 'subdir/*')
    assert(options.join_configurations == {'subdir/*': 'mymodule'})

def test_add_join_configuration_star():
    options = Options()
    options.add_join_configuration('mymodule', '*')
    assert(options.join_configurations == {'*': 'mymodule'})

    files_resolver = FilesResolver(options)
    result = files_resolver.filename_to_module_name(PurePosixPath('test.h'), None)
    assert(result == 'mymodule:test')

    result = files_resolver.filename_to_module_name(PurePosixPath('subdir/test.h'), None)
    assert(result == 'mymodule:subdir.test')

def test_filename_to_module_name_with_join_configuration():
    options = Options()
    files_resolver = FilesResolver(options)
    result = files_resolver.filename_to_module_name(PurePosixPath('subdir/test.h'), None)
    assert(result == 'subdir.test')

    options.join_configurations = {'subdir/*': 'mymodule'}
    files_resolver = FilesResolver(options)
    result = files_resolver.filename_to_module_name(PurePosixPath('subdir/test.h'), None)
    assert(result == 'mymodule:test')

    result = files_resolver.filename_to_module_name(PurePosixPath('other/test.h'), None)
    assert(result == 'other.test')

def test_set_root_dir_module_name_and_add_join_configuration():
    converter = Converter(ConvertAction.MODULES)
    converter.options.set_root_dir_module_name('org')
    converter.options.add_join_configuration('org.mymodule', 'subdir/*')
    converter.resolver.files_map.add_files_map_dict({
        'subdir': {
            'test.h': FileEntryType.FILE,
        },
        'other': {
            'test.h': FileEntryType.FILE,
        },
    })
    
    result1 = converter.resolver.convert_filename_to_module_name(PurePosixPath('subdir/test.h'))
    assert(result1 == 'org.mymodule:test')
    
    result2 = converter.resolver.convert_filename_to_module_name(PurePosixPath('other/test.h'))
    assert(result2 == 'org.other.test')

