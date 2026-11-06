"""Тесты представления графа на языке D2."""

import unittest
from types import SimpleNamespace

from depviz.d2 import quote, to_d2
from depviz.graph import GraphBuilder
from depviz.repository import parse_test_repo

UNLIMITED = 1000


def render(text, root="A", max_depth=UNLIMITED, filter_substring=""):
    """Построить граф тестового репозитория и вернуть его D2."""
    index = parse_test_repo(text)
    graph = GraphBuilder(index, max_depth, filter_substring).build(root)
    config = SimpleNamespace(
        max_depth=max_depth, filter_substring=filter_substring
    )
    return to_d2(graph, config)


class QuoteTests(unittest.TestCase):
    """Экранирование имён."""

    def test_plain(self):
        """Имя со спецсимволами D2 берётся в кавычки."""
        self.assertEqual(quote("libstdc++.so"), '"libstdc++.so"')

    def test_escape(self):
        """Кавычки и обратные косые черты экранируются."""
        self.assertEqual(quote('a"b\\c'), '"a\\"b\\\\c"')


class ToD2Tests(unittest.TestCase):
    """Формирование описания графа."""

    def test_nodes_and_edges(self):
        """Все пакеты объявлены, все связи перечислены."""
        out = render("A: B C\nB: C\nC:\n")
        lines = out.splitlines()
        self.assertIn("direction: down", lines)
        for node in ('"B"', '"C"'):
            self.assertIn(node, lines)
        for edge in ('"A" -> "B"', '"A" -> "C"', '"B" -> "C"'):
            self.assertIn(edge, lines)

    def test_root_highlighted(self):
        """Корневой пакет выделен заливкой."""
        out = render("A: B\nB:\n")
        self.assertIn('"A": {\n  style.fill: "#dbeafe"', out)

    def test_single_package(self):
        """Граф из одного пакета без связей."""
        out = render("A:\n")
        self.assertIn('"A": {', out)
        self.assertNotIn("->", out)

    def test_cycle_edge_styled(self):
        """Ребро цикла выделено красной пунктирной линией."""
        out = render("A: B\nB: A\n")
        self.assertIn(
            '"B" -> "A": {\n  style.stroke: "#dc2626"\n'
            "  style.stroke-dash: 5\n}",
            out,
        )
        self.assertIn('"A" -> "B"\n', out)

    def test_missing_and_truncated(self):
        """Отсутствующие и нераскрытые пакеты подписаны."""
        out = render("A: B X\nB: C\nC:\n", max_depth=1)
        self.assertIn('label: "X (нет в репозитории)"', out)
        self.assertIn('label: "B (не раскрыт)"', out)
        self.assertIn("style.stroke-dash: 3", out)

    def test_filter_comment(self):
        """Исключённые фильтром пакеты указаны в комментарии."""
        out = render("A: B TEST\nB:\nTEST:\n", filter_substring="TEST")
        self.assertIn("# Исключены фильтром: TEST", out)
        self.assertNotIn('"TEST"', out)


if __name__ == "__main__":
    unittest.main()
