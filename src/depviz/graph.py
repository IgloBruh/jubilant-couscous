"""Построение графа зависимостей обходом в глубину без рекурсии."""

import math
from dataclasses import dataclass, field

ROOT_DEPTH = 0


@dataclass
class DependencyGraph:
    """Граф зависимостей пакета.

    ``edges`` -- словарь «пакет -> список прямых зависимостей» в порядке
    обнаружения пакетов; ``cycles`` -- рёбра, замыкающие цикл;
    ``truncated`` -- пакеты, не раскрытые из-за ограничения глубины;
    ``filtered`` -- пакеты, исключённые фильтром; ``missing`` --
    зависимости, отсутствующие в репозитории.
    """

    root: str
    edges: dict = field(default_factory=dict)
    cycles: list = field(default_factory=list)
    truncated: set = field(default_factory=set)
    filtered: set = field(default_factory=set)
    missing: set = field(default_factory=set)

    @property
    def nodes(self):
        """Список пакетов графа в порядке обнаружения."""
        return list(self.edges)

    def edge_count(self):
        """Число рёбер графа."""
        return sum(len(children) for children in self.edges.values())

    def add_cycle(self, source, target):
        """Запомнить ребро, замыкающее цикл, без повторов."""
        if (source, target) not in self.cycles:
            self.cycles.append((source, target))


class GraphBuilder:
    """Построитель графа зависимостей по индексу репозитория.

    Обход выполняется в глубину с явным стеком вместо рекурсии. Глубина
    корневого пакета равна 0; пакеты на глубине ``max_depth`` попадают
    в граф, но их зависимости не раскрываются. Пакеты, имя которых
    содержит ``filter_substring``, в анализ не включаются (корневой
    пакет не фильтруется).
    """

    def __init__(self, index, max_depth, filter_substring=""):
        """Сохранить индекс репозитория и параметры анализа."""
        self.index = index
        self.max_depth = max_depth
        self.filter_substring = filter_substring

    def build(self, root):
        """Построить граф зависимостей пакета ``root``.

        Каждый элемент стека -- (пакет, глубина, итератор по ещё не
        просмотренным зависимостям). Множество ``on_path`` хранит пакеты
        текущего пути от корня: ребро в такой пакет замыкает цикл.
        Пакет, найденный повторно на меньшей глубине, раскрывается
        заново, чтобы ограничение глубины не зависело от порядка обхода.
        """
        self.index.get(root)
        graph = DependencyGraph(root)
        best_depth = {root: ROOT_DEPTH}
        on_path = {root}
        stack = [self._open(graph, root, ROOT_DEPTH)]
        while stack:
            node, depth, children = stack[-1]
            child = next(children, None)
            if child is None:
                stack.pop()
                on_path.discard(node)
            elif child in on_path:
                graph.add_cycle(node, child)
            elif depth + 1 < best_depth.get(child, math.inf):
                best_depth[child] = depth + 1
                on_path.add(child)
                stack.append(self._open(graph, child, depth + 1))
        return graph

    def _open(self, graph, node, depth):
        """Добавить пакет в граф и вернуть элемент стека для обхода."""
        graph.edges.setdefault(node, [])
        nothing = iter(())
        if node not in self.index.packages:
            graph.missing.add(node)
            return node, depth, nothing
        if depth >= self.max_depth:
            if self.index.get(node).depends:
                graph.truncated.add(node)
            return node, depth, nothing
        graph.truncated.discard(node)
        children = self._children(graph, node)
        graph.edges[node] = children
        return node, depth, iter(children)

    def _children(self, graph, node):
        """Вернуть имена прямых зависимостей пакета с учётом фильтра."""
        children = []
        for dependency in self.index.direct_dependencies(node):
            name = dependency.name
            if self.filter_substring and self.filter_substring in name:
                graph.filtered.add(name)
            elif name not in children:
                children.append(name)
        return children


def build_graph(index, config):
    """Построить граф зависимостей согласно конфигурации."""
    builder = GraphBuilder(index, config.max_depth, config.filter_substring)
    return builder.build(config.package_name)
