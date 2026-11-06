"""Тесты порядка загрузки зависимостей."""

import unittest

from depviz.apkindex import ApkIndex, Package
from depviz.graph import GraphBuilder
from depviz.order import load_order
from depviz.repository import parse_test_repo

UNLIMITED = 1000


def order_for(text, root="A", max_depth=UNLIMITED, filter_substring=""):
    """Построить граф тестового репозитория и вернуть порядок загрузки."""
    index = parse_test_repo(text)
    graph = GraphBuilder(index, max_depth, filter_substring).build(root)
    return load_order(graph)


class LoadOrderTests(unittest.TestCase):
    """Порядок загрузки для разных графов."""

    def assert_dependencies_first(self, text, order):
        """Каждый пакет идёт после своих зависимостей (кроме циклов)."""
        position = {name: i for i, name in enumerate(order)}
        index = parse_test_repo(text)
        for name in order:
            for dep in index.direct_dependencies(name):
                if dep.name in position and dep.found:
                    self.assertLess(position[dep.name], position[name])

    def test_single(self):
        """Пакет без зависимостей."""
        self.assertEqual(order_for("A:\n"), ["A"])

    def test_chain(self):
        """Цепочка загружается с конца."""
        self.assertEqual(order_for("A: B\nB: C\nC:\n"), ["C", "B", "A"])

    def test_diamond(self):
        """Общая зависимость загружается один раз и раньше всех."""
        text = "A: B C\nB: D\nC: D\nD:\n"
        order = order_for(text)
        self.assertEqual(order, ["D", "B", "C", "A"])
        self.assert_dependencies_first(text, order)

    def test_application(self):
        """Порядок учитывает все связи в разветвлённом графе."""
        text = (
            "APP: LOG NET UI\nNET: TLS ZLIB\nTLS: CRYPTO\nUI: FONT ZLIB\n"
            "FONT: ZLIB\nLOG:\nCRYPTO:\nZLIB:\n"
        )
        order = order_for(text, root="APP")
        self.assertEqual(order[-1], "APP")
        self.assertEqual(len(order), 8)
        self.assert_dependencies_first(text, order)

    def test_cycle(self):
        """Цикл разрывается, каждый пакет встречается один раз."""
        order = order_for("A: B\nB: C\nC: A D\nD:\n")
        self.assertEqual(order, ["D", "C", "B", "A"])

    def test_self_loop(self):
        """Зависимость пакета от самого себя не мешает порядку."""
        self.assertEqual(order_for("A: A B\nB: B\n"), ["B", "A"])

    def test_missing_excluded(self):
        """Отсутствующие пакеты не попадают в порядок."""
        self.assertEqual(order_for("A: B X\nB:\n"), ["B", "A"])

    def test_depth_and_filter(self):
        """Порядок строится по графу с учётом глубины и фильтра."""
        text = "A: B\nB: C\nC: D\nD:\n"
        self.assertEqual(order_for(text, max_depth=1), ["B", "A"])
        self.assertEqual(order_for(text, filter_substring="C"), ["B", "A"])

    def test_no_recursion_limit(self):
        """Длинная цепочка не упирается в предел рекурсии."""
        length = 5000
        packages = [
            Package(f"P{i}", depends=(f"P{i + 1}",)) for i in range(length)
        ]
        packages.append(Package(f"P{length}"))
        graph = GraphBuilder(ApkIndex(packages), length + 1).build("P0")
        order = load_order(graph)
        self.assertEqual(order[0], f"P{length}")
        self.assertEqual(order[-1], "P0")


if __name__ == "__main__":
    unittest.main()
