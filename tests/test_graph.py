"""Тесты построения графа зависимостей."""

import unittest

from depviz.apkindex import ApkIndex, Package, PackageNotFoundError
from depviz.graph import GraphBuilder
from depviz.repository import parse_test_repo

UNLIMITED = 1000


def build(text, root="A", max_depth=UNLIMITED, filter_substring=""):
    """Построить граф по описанию тестового репозитория."""
    index = parse_test_repo(text)
    return GraphBuilder(index, max_depth, filter_substring).build(root)


class BasicGraphTests(unittest.TestCase):
    """Построение графа без циклов и ограничений."""

    def test_single_package(self):
        """Пакет без зависимостей."""
        graph = build("A:\n")
        self.assertEqual(graph.edges, {"A": []})
        self.assertEqual(graph.edge_count(), 0)

    def test_transitive(self):
        """Транзитивные зависимости попадают в граф."""
        graph = build("A: B\nB: C\nC:\n")
        self.assertEqual(graph.edges, {"A": ["B"], "B": ["C"], "C": []})

    def test_diamond(self):
        """Общая зависимость появляется в графе один раз."""
        graph = build("A: B C\nB: D\nC: D\nD:\n")
        self.assertEqual(graph.nodes, ["A", "B", "D", "C"])
        self.assertEqual(graph.edges["C"], ["D"])
        self.assertEqual(graph.cycles, [])

    def test_unknown_root(self):
        """Корневой пакет отсутствует в репозитории."""
        with self.assertRaises(PackageNotFoundError):
            build("A:\n", root="Z")

    def test_missing_dependency(self):
        """Отсутствующая зависимость -- лист графа."""
        graph = build("A: B X\nB:\n")
        self.assertEqual(graph.missing, {"X"})
        self.assertEqual(graph.edges["X"], [])

    def test_no_recursion_limit(self):
        """Длинная цепочка не упирается в предел глубины рекурсии."""
        length = 5000
        packages = [
            Package(f"P{i}", depends=(f"P{i + 1}",)) for i in range(length)
        ]
        packages.append(Package(f"P{length}"))
        graph = GraphBuilder(ApkIndex(packages), length + 1).build("P0")
        self.assertEqual(len(graph.nodes), length + 1)


class CycleTests(unittest.TestCase):
    """Обработка циклических зависимостей."""

    def test_cycle(self):
        """Цикл A -> B -> C -> A обнаруживается, обход завершается."""
        graph = build("A: B\nB: C\nC: A D\nD:\n")
        self.assertEqual(graph.cycles, [("C", "A")])
        self.assertEqual(set(graph.nodes), {"A", "B", "C", "D"})

    def test_self_loop(self):
        """Пакет, зависящий сам от себя."""
        graph = build("A: A B\nB:\n")
        self.assertEqual(graph.cycles, [("A", "A")])

    def test_several_cycles(self):
        """Несколько циклов в одном графе."""
        text = "A: B C\nB: D E\nC: E F\nD: G\nE: G H\nF: H\nG: A\nH: C\n"
        graph = build(text)
        self.assertEqual(
            graph.cycles, [("G", "A"), ("C", "E"), ("F", "H")]
        )
        self.assertEqual(len(graph.nodes), 8)

    def test_cross_edge_is_not_cycle(self):
        """Повторное посещение готовой вершины -- не цикл."""
        graph = build("A: B C\nB: C\nC:\n")
        self.assertEqual(graph.cycles, [])


class DepthTests(unittest.TestCase):
    """Ограничение глубины анализа."""

    CHAIN = "A: B\nB: C\nC: D\nD: E\nE:\n"

    def test_limit(self):
        """Пакеты глубже максимальной не попадают в граф."""
        graph = build(self.CHAIN, max_depth=2)
        self.assertEqual(graph.nodes, ["A", "B", "C"])
        self.assertEqual(graph.truncated, {"C"})

    def test_minimal_depth(self):
        """Глубина 1 -- только прямые зависимости."""
        graph = build(self.CHAIN, max_depth=1)
        self.assertEqual(graph.edges, {"A": ["B"], "B": []})

    def test_leaf_is_not_truncated(self):
        """Лист на предельной глубине не считается нераскрытым."""
        graph = build(self.CHAIN, max_depth=4)
        self.assertEqual(graph.truncated, set())

    def test_shorter_path_found_later(self):
        """Пакет, найденный позже по короткому пути, раскрывается."""
        graph = build("A: B D\nB: C\nC: D\nD: E\nE:\n", max_depth=3)
        self.assertEqual(graph.edges["D"], ["E"])
        self.assertIn("E", graph.nodes)
        self.assertEqual(graph.truncated, set())


class FilterTests(unittest.TestCase):
    """Фильтрация пакетов по подстроке."""

    TEXT = (
        "APP: LIBA TESTKIT\nLIBA: CORE TESTLIB\nTESTKIT: CORE\n"
        "TESTLIB: CORE\nCORE:\n"
    )

    def test_filtered_packages_excluded(self):
        """Пакеты с подстрокой и их зависимости не анализируются."""
        graph = build(self.TEXT, root="APP", filter_substring="TEST")
        self.assertEqual(graph.nodes, ["APP", "LIBA", "CORE"])
        self.assertEqual(graph.filtered, {"TESTKIT", "TESTLIB"})

    def test_empty_filter(self):
        """Пустая подстрока ничего не исключает."""
        graph = build(self.TEXT, root="APP")
        self.assertEqual(len(graph.nodes), 5)
        self.assertEqual(graph.filtered, set())

    def test_root_not_filtered(self):
        """Корневой пакет не исключается фильтром."""
        graph = build(self.TEXT, root="TESTKIT", filter_substring="TEST")
        self.assertEqual(graph.nodes, ["TESTKIT", "CORE"])

    def test_filter_breaks_cycle(self):
        """Фильтр может разорвать цикл."""
        graph = build("A: B\nB: C\nC: A\n", filter_substring="C")
        self.assertEqual(graph.cycles, [])
        self.assertEqual(graph.filtered, {"C"})


if __name__ == "__main__":
    unittest.main()
