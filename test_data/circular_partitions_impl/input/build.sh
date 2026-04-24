#!/bin/bash

# Скрипт сборки аналогично CMakePresets.json
# Поддерживаемые компиляторы: clang++-20, clang++-21, g++-15

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
    
    # Выбираем компилятор в зависимости от пресета
    case $preset in
        test-clang-20)
            compiler="clang++-20"
            ;;
        test-clang-21)
            compiler="clang++-21"
            ;;
        test-gcc-15)
            compiler="g++-15"
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
    
    # Создаем директорию сборки
    mkdir -p build
    
    # Компилируем исходные файлы
    $compiler -std=c++23 -c main.cpp -o build/main.o
    $compiler -std=c++23 -c mymodule/part1.cpp -o build/part1.o
    $compiler -std=c++23 -c mymodule/part2.cpp -o build/part2.o
    
    # Линкуем объектные файлы
    $compiler -std=c++23 -o build/test_mod build/main.o build/part1.o build/part2.o
    
    if [ $? -eq 0 ]; then
        echo "Сборка завершена успешно"
        echo "Исполняемый файл: build/test_mod"
    else
        echo "Ошибка сборки"
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