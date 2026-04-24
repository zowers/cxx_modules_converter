#!/bin/bash -ex

# Скрипт сборки аналогично CMakePresets.json
# Поддерживаемые компиляторы: clang++-20, clang++-21, g++-14, g++-15

# Функция для отображения помощи
show_help() {
    echo "Использование: $0 <preset>"
    echo ""
    echo "Доступные пресеты:"
    echo "  test-clang-20    Сборка с использованием clang++-20"
    echo "  test-clang-21    Сборка с использованием clang++-21"
    echo "  test-gcc-15      Сборка с использованием g++-15"
    echo ""
    echo "Примеры:"
    echo "  $0 test-clang-20          # Сборка с clang++-20"
    echo "  $0 test-clang-21          # Сборка с clang++-21"
    echo "  $0 test-gcc-15            # Сборка с g++-15"
}

# Проверка наличия необходимых инструментов
check_compiler() {
    local compiler=$1
    if command -v "$compiler" &> /dev/null; then
        echo "Найден компилятор: $compiler"
        return 0
    else
        echo "Ошибка: компилятор $compiler не найден"
        return 1
    fi
}

# Функция для сборки проекта
build_project() {
    local preset=$1
    local compiler=""
    local module_compile_flag=""
    local module_output_ext="pcm"
    local module_path_flag=""
    local source_compile_flags=""
    local module_output_dir="build"
    
    # Выбираем компилятор и специфичные опции в зависимости от пресета
    case $preset in
        test-clang-20)
            compiler="clang++-20"
            module_compile_flag="--precompile"
            module_output_ext="pcm"
            module_path_flag="-fprebuilt-module-path=build"
            source_compile_flags="-fprebuilt-module-path=build -c"
            module_output_dir="build"
            ;;
        test-clang-21)
            compiler="clang++-21"
            module_compile_flag="--precompile"
            module_output_ext="pcm"
            module_path_flag="-fprebuilt-module-path=build"
            source_compile_flags="-fprebuilt-module-path=build -c"
            module_output_dir="build"
            ;;
        test-gcc-15)
            compiler="g++-15"
            module_compile_flag="-fmodules -c"
            module_output_ext="o"
            module_path_flag=""
            source_compile_flags="-fmodules -c"
            module_output_dir="build"
            ;;
        *)
            echo "Ошибка: Неизвестный пресет '$preset'"
            show_help
            exit 1
            ;;
    esac
    
    # Проверяем наличие компилятора
    if ! check_compiler "$compiler"; then
        exit 1
    fi
    
    echo "Сборка проекта с пресетом: $preset"
    echo "  Компилятор: $compiler"
    echo "  Флаг модулей: $module_compile_flag"
    echo "  Расширение вывода: $module_output_ext"
    
    # Создаем директорию сборки
    rm -rf build gcm.cache && mkdir -p build $module_output_dir
    
    # Компилируем партиции модуля
    echo "Компиляция партиций модуля..."
    $compiler -std=gnu++23 $module_compile_flag mymodule/part1.cppm -o $module_output_dir/mymodule-part1.$module_output_ext
    if [ $? -ne 0 ]; then
        echo "Ошибка компиляции партиции mymodule:part1"
        exit 1
    fi
    
    $compiler -std=gnu++23 $module_compile_flag mymodule/part2.cppm -o $module_output_dir/mymodule-part2.$module_output_ext
    if [ $? -ne 0 ]; then
        echo "Ошибка компиляции партиции mymodule:part2"
        exit 1
    fi
    
    # Компилируем основной модуль с указанием пути к партициям
    echo "Компиляция основного модуля..."
    $compiler -std=gnu++23 $module_path_flag $module_compile_flag mymodule.cppm -o $module_output_dir/mymodule.$module_output_ext
    if [ $? -ne 0 ]; then
        echo "Ошибка компиляции основного модуля mymodule"
        exit 1
    fi
    
    # Компилируем исходные файлы с использованием модулей
    echo "Компиляция исходных файлов..."
    $compiler -std=gnu++23 $source_compile_flags mymodule/part1.cpp -o build/part1.o
    if [ $? -ne 0 ]; then
        echo "Ошибка компиляции part1.cpp"
        exit 1
    fi
    
    $compiler -std=gnu++23 $source_compile_flags mymodule/part2.cpp -o build/part2.o
    if [ $? -ne 0 ]; then
        echo "Ошибка компиляции part2.cpp"
        exit 1
    fi
    
    $compiler -std=gnu++23 $source_compile_flags main.cpp -o build/main.o
    if [ $? -ne 0 ]; then
        echo "Ошибка компиляции main.cpp"
        exit 1
    fi
    
    # Линкуем объектные файлы
    echo "Линковка..."
    $compiler -std=gnu++23 -o build/test_mod build/main.o build/part1.o build/part2.o
    if [ $? -eq 0 ]; then
        echo "Сборка завершена успешно"
        echo "Исполняемый файл: build/test_mod"
    else
        echo "Ошибка линковки"
        exit 1
    fi
}

# Основная логика скрипта
main() {
    # Проверяем количество аргументов
    if [ $# -ne 1 ]; then
        echo "Ошибка: Необходимо указать один пресет"
        show_help
        exit 1
    fi
    
    local preset=$1
    
    # Обработка аргументов командной строки
    case $preset in
        -h|--help)
            show_help
            exit 0
            ;;
        test-clang-20|test-clang-21|test-gcc-15)
            build_project "$preset"
            ;;
        *)
            echo "Ошибка: Неизвестный аргумент '$preset'"
            show_help
            exit 1
            ;;
    esac
}

# Запуск основной логики
main "$@"