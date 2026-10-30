"""Тесты разбора индекса APKINDEX."""

import unittest

from depviz.apkindex import (
    PackageNotFoundError,
    parse_index,
    strip_constraint,
)

SAMPLE_INDEX = """\
C:Q1abc=
P:curl
V:8.14.1-r2
A:x86_64
D:libcurl=8.14.1-r2 so:libc.musl-x86_64.so.1 so:libcurl.so.4 !curl-old
p:cmd:curl=8.14.1-r2

P:libcurl
V:8.14.1-r2
D:so:libc.musl-x86_64.so.1
p:so:libcurl.so.4=4.8.0

P:musl
V:1.2.5-r1
p:so:libc.musl-x86_64.so.1=1

P:busybox-binsh
V:1.36.1-r31
k:100
p:/bin/sh cmd:sh=1.36.1-r31

P:dash-binsh
V:0.5.12-r3
k:60
p:/bin/sh

P:bash
V:5.2.26-r0
D:/bin/sh so:libc.musl-x86_64.so.1 missing-lib>=2
"""


class StripConstraintTests(unittest.TestCase):
    """Отбрасывание ограничений версии."""

    def test_operators(self):
        """Все операторы сравнения версий."""
        for token in ("musl>=1.2", "musl=1", "musl<2", "musl~1.2", "musl"):
            self.assertEqual(strip_constraint(token), "musl")


class ParseIndexTests(unittest.TestCase):
    """Разбор записей индекса."""

    def setUp(self):
        """Разобрать пример индекса."""
        self.index = parse_index(SAMPLE_INDEX)

    def test_packages(self):
        """Все записи распознаны, поля заполнены."""
        self.assertEqual(len(self.index.packages), 6)
        curl = self.index.get("curl")
        self.assertEqual(curl.version, "8.14.1-r2")
        self.assertNotIn("!curl-old", curl.depends)
        self.assertEqual(self.index.get("busybox-binsh").priority, 100)

    def test_unknown_package(self):
        """Запрос отсутствующего пакета."""
        with self.assertRaises(PackageNotFoundError):
            self.index.get("nope")

    def test_record_without_name_is_skipped(self):
        """Запись без поля P игнорируется."""
        index = parse_index("V:1.0\nD:musl\n\nP:musl\n")
        self.assertEqual(list(index.packages), ["musl"])

    def test_empty_index(self):
        """Пустой индекс."""
        self.assertEqual(parse_index("").packages, {})


class DirectDependenciesTests(unittest.TestCase):
    """Получение прямых зависимостей."""

    def setUp(self):
        """Разобрать пример индекса."""
        self.index = parse_index(SAMPLE_INDEX)

    def test_virtual_dependencies_resolved(self):
        """Зависимости so: разрешаются в пакеты и объединяются."""
        deps = self.index.direct_dependencies("curl")
        self.assertEqual([dep.name for dep in deps], ["libcurl", "musl"])
        self.assertEqual(
            deps[0].requirements, ("libcurl=8.14.1-r2", "so:libcurl.so.4")
        )
        self.assertTrue(all(dep.found for dep in deps))

    def test_provider_priority(self):
        """Из нескольких поставщиков выбирается приоритетный."""
        self.assertEqual(self.index.resolve("/bin/sh"), "busybox-binsh")

    def test_unresolved_dependency(self):
        """Неразрешимая зависимость помечается как не найденная."""
        deps = self.index.direct_dependencies("bash")
        missing = deps[-1]
        self.assertEqual(missing.name, "missing-lib")
        self.assertFalse(missing.found)

    def test_no_dependencies(self):
        """Пакет без зависимостей."""
        self.assertEqual(self.index.direct_dependencies("musl"), [])


if __name__ == "__main__":
    unittest.main()
