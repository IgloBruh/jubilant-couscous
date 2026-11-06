"""Тесты вывода зависимостей в виде ASCII-дерева."""

import unittest

from depviz.apkindex import ApkIndex, Package
from depviz.graph import GraphBuilder
from depviz.repository import parse_test_repo
from depviz.tree import ascii_tree

UNLIMITED = 1000


def tree(text, root="A", max_depth=UNLIMITED, filter_substring=""):
    """Построить граф тестового репозитория и вернуть дерево."""
    index = parse_test_repo(text)
    graph = GraphBuilder(index, max_depth, filter_substring).build(root)
    return ascii_tree(graph, max_depth)


class AsciiTreeTests(unittest.TestCase):
    """Форма дерева и пометки."""

    def test_single(self):
        """Дерево из одного пакета."""
        self.assertEqual(tree("A:\n"), "A")

    def test_shape(self):
        """Ветви и отступы рисуются псевдографикой."""
        expected = "\n".join([
            "A",
            "├── B",
            "│   └── D",
            "└── C",
            "    └── E",
        ])
        self.assertEqual(tree("A: B C\nB: D\nC: E\nD:\nE:\n"), expected)

    def test_repeat_marked(self):
        """Повторно встреченное поддерево не раскрывается."""
        expected = "\n".join([
            "A",
            "├── B",
            "│   └── D",
            "│       └── E",
            "└── C",
            "    └── D (*)",
        ])
        self.assertEqual(tree("A: B C\nB: D\nC: D\nD: E\nE:\n"), expected)

    def test_repeated_leaf_not_marked(self):
        """Повторно встреченный лист выводится без пометки."""
        lines = tree("A: B C\nB: D\nC: D\nD:\n").splitlines()
        self.assertEqual(lines[-1], "    └── D")

    def test_cycle(self):
        """Ребро в пакет на текущем пути помечается как цикл."""
        expected = "\n".join(["A", "└── B", "    └── A (цикл)"])
        self.assertEqual(tree("A: B\nB: A\n"), expected)

    def test_self_loop(self):
        """Зависимость от самого себя."""
        self.assertIn("└── A (цикл)", tree("A: A\n"))

    def test_missing(self):
        """Отсутствующий пакет помечается."""
        self.assertIn("X (нет в репозитории)", tree("A: X\n"))

    def test_depth_limit(self):
        """Пакеты на предельной глубине не раскрываются."""
        expected = "\n".join(["A", "└── B", "    └── C (...)"])
        self.assertEqual(tree("A: B\nB: C\nC: D\nD:\n", max_depth=2),
                         expected)

    def test_shorter_path_expanded(self):
        """Пакет раскрывается там, где позволяет глубина."""
        text = "A: B D\nB: C\nC: D\nD: E\nE:\n"
        lines = tree(text, max_depth=3).splitlines()
        self.assertIn("│       └── D (...)", lines)
        self.assertEqual(lines[-2:], ["└── D", "    └── E"])

    def test_no_recursion_limit(self):
        """Глубокое дерево строится без рекурсии."""
        length = 3000
        packages = [
            Package(f"P{i}", depends=(f"P{i + 1}",)) for i in range(length)
        ]
        packages.append(Package(f"P{length}"))
        graph = GraphBuilder(ApkIndex(packages), length + 1).build("P0")
        lines = ascii_tree(graph, length + 1).splitlines()
        self.assertEqual(len(lines), length + 1)


if __name__ == "__main__":
    unittest.main()
