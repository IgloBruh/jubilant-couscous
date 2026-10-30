# depviz — визуализатор графа зависимостей пакетов

## Общее описание

`depviz` — CLI-инструмент для визуализации графа зависимостей пакетов
менеджера пакетов Alpine Linux (`apk`). Готовые менеджеры пакетов и
библиотеки для получения зависимостей не используются.

Практическая работа № 2, вариант 9. Текущее состояние —
**этап 1: минимальный прототип с конфигурацией**. Приложение читает
параметры из XML-файла, проверяет их и выводит в формате `ключ=значение`.

Реализация на Python 3.10+ без сторонних зависимостей.

## Структура репозитория

```
config.xml            конфигурация по умолчанию
examples/             примеры конфигураций и тестовый репозиторий
  test_mode.xml       конфигурация тестового режима
  test_repo.txt       файл описания тестового репозитория
  errors/             конфигурации с ошибками для демонстрации
src/depviz/           исходный код
  cli.py              интерфейс командной строки
  config.py           загрузка и проверка конфигурации
tests/                модульные тесты (unittest)
run.sh, run.bat       скрипты запуска
Makefile              цели run и test
```

## Настройки

Конфигурация задаётся XML-файлом с корневым элементом `<config>`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<config>
    <package_name>busybox</package_name>
    <repository>https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64</repository>
    <test_repo_mode>false</test_repo_mode>
    <ascii_tree>true</ascii_tree>
    <max_depth>3</max_depth>
    <filter_substring>doc</filter_substring>
</config>
```

| Параметр           | Обяз. | Описание и допустимые значения |
|--------------------|-------|--------------------------------|
| `package_name`     | да    | Имя анализируемого пакета: латинские буквы, цифры, `. _ + -`; начинается с буквы или цифры |
| `repository`       | да    | URL репозитория (`http`/`https`) или, в тестовом режиме, путь к файлу тестового репозитория (относительный путь отсчитывается от каталога конфигурации) |
| `test_repo_mode`   | да    | Режим работы с тестовым репозиторием: `true/false`, `yes/no`, `on/off`, `1/0` |
| `ascii_tree`       | да    | Режим вывода зависимостей в виде ASCII-дерева: те же логические значения |
| `max_depth`        | да    | Максимальная глубина анализа — целое число от 1 до 100 |
| `filter_substring` | нет   | Подстрока для фильтрации пакетов, без пробелов; по умолчанию пустая (фильтр выключен) |

### Обработка ошибок

Приложение проверяет все параметры и сообщает **все** найденные ошибки
сразу, после чего завершается с кодом `1`. Обрабатываются:

- отсутствующий или нечитаемый файл конфигурации;
- синтаксически некорректный XML;
- неверный корневой элемент;
- неизвестные, повторяющиеся и составные (с вложенными тегами) параметры;
- отсутствие обязательных параметров;
- некорректные значения каждого параметра (см. таблицу выше);
- некорректный URL или отсутствующий файл тестового репозитория.

## Функции

Модуль `depviz.config`:

- `load_config(path)` — загрузить и проверить конфигурацию, вернуть
  объект `Config` или выбросить `ConfigError` со списком ошибок;
- `read_root(path)` — прочитать XML и вернуть корневой элемент;
- `collect_raw_values(root)` — собрать текстовые значения параметров
  и ошибки структуры;
- `parse_fields(raw_values)` — разобрать значения всех параметров;
- `parse_package_name`, `parse_repository`, `parse_bool`,
  `parse_max_depth`, `parse_filter_substring` — проверка отдельных
  параметров;
- `check_repository(repository, test_mode, base_dir)` — проверка
  репозитория с учётом режима работы;
- `Config.as_pairs()` — параметры в виде пар (ключ, значение).

Модуль `depviz.cli`:

- `build_parser()` — парсер аргументов командной строки;
- `format_config(config)` — форматирование в строки `ключ=значение`;
- `main(argv=None)` — запуск приложения, возвращает код завершения.

## Сборка и запуск

Сборка не требуется, нужен только Python 3.10+.

Запуск с конфигурацией по умолчанию (`config.xml`):

```bash
./run.sh
```

Windows:

```bat
run.bat
```

Указать другой файл конфигурации:

```bash
./run.sh -c examples/test_mode.xml
```

Без скриптов:

```bash
PYTHONPATH=src python -m depviz -c config.xml
```

### Тесты

```bash
python -m unittest discover -s tests -t . -v
```

или `make test`.

## Примеры использования

Корректная конфигурация:

```
$ ./run.sh
package_name=busybox
repository=https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64
test_repo_mode=false
ascii_tree=true
max_depth=3
filter_substring=doc
```

Тестовый режим:

```
$ ./run.sh -c examples/test_mode.xml
package_name=A
repository=examples/test_repo.txt
test_repo_mode=true
ascii_tree=false
max_depth=5
filter_substring=
```

Ошибки во всех параметрах:

```
$ ./run.sh -c examples/errors/bad_values.xml
Ошибка конфигурации:
  - package_name: недопустимое имя пакета: '-bad name'
  - repository: адрес репозитория не может быть пустым
  - test_repo_mode: ожидалось логическое значение (0, 1, false, no, off, on, true, yes), получено 'maybe'
  - ascii_tree: ожидалось логическое значение (0, 1, false, no, off, on, true, yes), получено '2'
  - max_depth: ожидалось целое число, получено 'zero'
  - filter_substring: подстрока не должна содержать пробельных символов: 'a b'
```

Ошибки структуры:

```
$ ./run.sh -c examples/errors/missing_and_unknown.xml
Ошибка конфигурации:
  - параметр <package_name> задан более одного раза
  - неизвестный параметр <colour>
  - параметр <max_depth> не должен иметь вложенных тегов
  - отсутствует обязательный параметр <repository>
  - отсутствует обязательный параметр <test_repo_mode>
  - отсутствует обязательный параметр <ascii_tree>
  - отсутствует обязательный параметр <max_depth>
```

Другие примеры ошибок: `examples/errors/malformed.xml` (некорректный XML),
`wrong_root.xml` (неверный корень), `out_of_range.xml` (глубина вне
диапазона), `missing_test_repo.xml` (нет файла тестового репозитория).

## Лицензия

См. файл [LICENSE](LICENSE).
