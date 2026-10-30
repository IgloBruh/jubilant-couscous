"""Разбор индекса репозитория Alpine Linux (файл APKINDEX).

Индекс состоит из записей, разделённых пустыми строками. Каждая строка
записи имеет вид ``X:значение``, где ``X`` -- однобуквенный код поля.
"""

import re
from dataclasses import dataclass

NAME_FIELD = "P"
VERSION_FIELD = "V"
DEPENDS_FIELD = "D"
PROVIDES_FIELD = "p"
PRIORITY_FIELD = "k"
FIELD_SEPARATOR = ":"
CONFLICT_PREFIX = "!"
DEFAULT_PRIORITY = 0
CONSTRAINT_RE = re.compile(r"[<>=~]")


class PackageNotFoundError(Exception):
    """Пакет отсутствует в репозитории."""


@dataclass(frozen=True)
class Package:
    """Описание пакета из индекса репозитория."""

    name: str
    version: str = ""
    depends: tuple = ()
    provides: tuple = ()
    priority: int = DEFAULT_PRIORITY


@dataclass(frozen=True)
class Dependency:
    """Прямая зависимость пакета.

    ``name`` -- имя пакета, удовлетворяющего зависимости (или исходное
    требование, если подходящий пакет не найден), ``requirements`` --
    исходные записи из поля ``D``, которые он удовлетворяет.
    """

    name: str
    requirements: tuple
    found: bool


def strip_constraint(token):
    """Отбросить ограничение версии: ``musl>=1.2`` -> ``musl``."""
    return CONSTRAINT_RE.split(token, maxsplit=1)[0]


def parse_record(lines):
    """Построить :class:`Package` по строкам одной записи индекса.

    Возвращает ``None``, если в записи нет имени пакета.
    """
    fields = {}
    for line in lines:
        key, sep, value = line.partition(FIELD_SEPARATOR)
        if sep:
            fields[key] = value.strip()
    if not fields.get(NAME_FIELD):
        return None
    depends = tuple(
        token for token in fields.get(DEPENDS_FIELD, "").split()
        if not token.startswith(CONFLICT_PREFIX)
    )
    provides = tuple(
        strip_constraint(token)
        for token in fields.get(PROVIDES_FIELD, "").split()
    )
    try:
        priority = int(fields.get(PRIORITY_FIELD, DEFAULT_PRIORITY))
    except ValueError:
        priority = DEFAULT_PRIORITY
    return Package(
        name=fields[NAME_FIELD],
        version=fields.get(VERSION_FIELD, ""),
        depends=depends,
        provides=provides,
        priority=priority,
    )


def split_records(text):
    """Разбить текст индекса на списки строк отдельных записей."""
    records = []
    current = []
    for line in text.splitlines():
        if line.strip():
            current.append(line)
        elif current:
            records.append(current)
            current = []
    if current:
        records.append(current)
    return records


def parse_index(text):
    """Разобрать текст APKINDEX и вернуть :class:`ApkIndex`."""
    packages = []
    for lines in split_records(text):
        package = parse_record(lines)
        if package is not None:
            packages.append(package)
    return ApkIndex(packages)


class ApkIndex:
    """Набор пакетов репозитория с поиском поставщиков зависимостей."""

    def __init__(self, packages):
        """Проиндексировать пакеты по именам и предоставляемым именам.

        Если пакет с одним именем встречается несколько раз, используется
        первая запись.
        """
        self.packages = {}
        self.providers = {}
        for package in packages:
            if package.name in self.packages:
                continue
            self.packages[package.name] = package
            for provided in package.provides:
                self.providers.setdefault(provided, []).append(package)

    def get(self, name):
        """Вернуть пакет по имени или выбросить PackageNotFoundError."""
        try:
            return self.packages[name]
        except KeyError:
            raise PackageNotFoundError(
                f"пакет {name!r} не найден в репозитории"
            ) from None

    def resolve(self, requirement):
        """Найти имя пакета, удовлетворяющего требованию.

        Сначала ищется пакет с точно таким именем, затем -- среди
        пакетов, предоставляющих это имя (поле ``p``), с наибольшим
        приоритетом (поле ``k``). Возвращает ``None``, если не найден.
        """
        name = strip_constraint(requirement)
        if name in self.packages:
            return name
        candidates = self.providers.get(name)
        if not candidates:
            return None
        best = min(candidates, key=lambda pkg: (-pkg.priority, pkg.name))
        return best.name

    def direct_dependencies(self, name):
        """Вернуть список прямых зависимостей пакета.

        Требования, удовлетворяемые одним и тем же пакетом, объединяются;
        порядок соответствует первому упоминанию в поле ``D``.
        """
        grouped = {}
        for requirement in self.get(name).depends:
            resolved = self.resolve(requirement)
            key = (resolved or strip_constraint(requirement), bool(resolved))
            grouped.setdefault(key, []).append(requirement)
        return [
            Dependency(dep_name, tuple(requirements), found)
            for (dep_name, found), requirements in grouped.items()
        ]
