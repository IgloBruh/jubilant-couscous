"""Загрузка и проверка пользовательской конфигурации из XML-файла."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

ROOT_TAG = "config"
MIN_DEPTH = 1
MAX_DEPTH = 100
TRUE_VALUES = frozenset({"true", "yes", "1", "on"})
FALSE_VALUES = frozenset({"false", "no", "0", "off"})
URL_SCHEMES = frozenset({"http", "https"})
PACKAGE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
REQUIRED = object()


class ConfigError(Exception):
    """Ошибка конфигурации, хранящая список всех найденных проблем."""

    def __init__(self, errors):
        """Сохранить список сообщений об ошибках."""
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


@dataclass(frozen=True)
class Config:
    """Проверенные параметры, настраиваемые пользователем."""

    package_name: str
    repository: str
    test_repo_mode: bool
    ascii_tree: bool
    max_depth: int
    filter_substring: str


def parse_package_name(raw):
    """Проверить имя анализируемого пакета."""
    if not PACKAGE_NAME_RE.match(raw):
        raise ValueError(f"недопустимое имя пакета: {raw!r}")
    return raw


def parse_repository(raw):
    """Проверить, что адрес репозитория не пуст.

    Содержательная проверка зависит от режима работы и выполняется
    в :func:`check_repository`.
    """
    if not raw:
        raise ValueError("адрес репозитория не может быть пустым")
    return raw


def parse_bool(raw):
    """Преобразовать строку в логическое значение."""
    value = raw.lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    allowed = ", ".join(sorted(TRUE_VALUES | FALSE_VALUES))
    raise ValueError(
        f"ожидалось логическое значение ({allowed}), получено {raw!r}"
    )


def parse_max_depth(raw):
    """Преобразовать строку в максимальную глубину анализа."""
    try:
        depth = int(raw)
    except ValueError:
        raise ValueError(f"ожидалось целое число, получено {raw!r}") from None
    if depth < MIN_DEPTH or depth > MAX_DEPTH:
        raise ValueError(
            f"глубина должна быть в диапазоне [{MIN_DEPTH}; {MAX_DEPTH}], "
            f"получено {depth}"
        )
    return depth


def parse_filter_substring(raw):
    """Проверить подстроку для фильтрации пакетов."""
    if any(char.isspace() for char in raw):
        raise ValueError(
            f"подстрока не должна содержать пробельных символов: {raw!r}"
        )
    return raw


FIELDS = {
    "package_name": (parse_package_name, REQUIRED),
    "repository": (parse_repository, REQUIRED),
    "test_repo_mode": (parse_bool, REQUIRED),
    "ascii_tree": (parse_bool, REQUIRED),
    "max_depth": (parse_max_depth, REQUIRED),
    "filter_substring": (parse_filter_substring, ""),
}


def check_repository(repository, test_mode, base_dir):
    """Проверить репозиторий с учётом режима работы.

    В тестовом режиме репозиторий -- путь к существующему файлу
    (относительный путь отсчитывается от каталога конфигурации).
    В обычном режиме -- URL-адрес со схемой http или https.
    """
    if test_mode:
        path = Path(repository)
        if not path.is_absolute():
            path = base_dir / path
        if not path.is_file():
            raise ValueError(f"файл тестового репозитория не найден: {path}")
        return str(path)
    parsed = urlparse(repository)
    if parsed.scheme not in URL_SCHEMES or not parsed.netloc:
        raise ValueError(
            f"некорректный URL репозитория: {repository!r} "
            "(ожидается http:// или https://)"
        )
    return repository


def read_root(path):
    """Прочитать XML-файл и вернуть его корневой элемент."""
    try:
        root = ET.parse(path).getroot()
    except FileNotFoundError:
        raise ConfigError([f"файл конфигурации не найден: {path}"]) from None
    except (IsADirectoryError, PermissionError) as exc:
        raise ConfigError(
            [f"не удалось прочитать файл конфигурации {path}: {exc}"]
        ) from None
    except ET.ParseError as exc:
        raise ConfigError([f"некорректный XML в файле {path}: {exc}"]) from None
    if root.tag != ROOT_TAG:
        raise ConfigError(
            [f"корневой элемент должен быть <{ROOT_TAG}>, а не <{root.tag}>"]
        )
    return root


def collect_raw_values(root):
    """Собрать текстовые значения параметров из XML-элементов.

    Возвращает словарь значений и список ошибок структуры: неизвестные,
    повторяющиеся и составные (с вложенными элементами) параметры.
    """
    values = {}
    errors = []
    for element in root:
        name = element.tag
        if name not in FIELDS:
            errors.append(f"неизвестный параметр <{name}>")
        elif name in values:
            errors.append(f"параметр <{name}> задан более одного раза")
        elif len(element):
            errors.append(f"параметр <{name}> не должен иметь вложенных тегов")
        else:
            values[name] = (element.text or "").strip()
    return values, errors


def parse_fields(raw_values):
    """Разобрать все параметры, собрав ошибки по каждому из них."""
    values = {}
    errors = []
    for name, (parser, default) in FIELDS.items():
        if name not in raw_values:
            if default is REQUIRED:
                errors.append(f"отсутствует обязательный параметр <{name}>")
            else:
                values[name] = default
            continue
        try:
            values[name] = parser(raw_values[name])
        except ValueError as exc:
            errors.append(f"{name}: {exc}")
    return values, errors


def load_config(path):
    """Загрузить и проверить конфигурацию из XML-файла.

    При любых ошибках выбрасывает :class:`ConfigError` со списком
    всех найденных проблем, а не только первой.
    """
    path = Path(path)
    raw_values, errors = collect_raw_values(read_root(path))
    values, field_errors = parse_fields(raw_values)
    errors.extend(field_errors)
    if "repository" in values and "test_repo_mode" in values:
        try:
            values["repository"] = check_repository(
                values["repository"], values["test_repo_mode"], path.parent
            )
        except ValueError as exc:
            errors.append(f"repository: {exc}")
    if errors:
        raise ConfigError(errors)
    return Config(**values)
