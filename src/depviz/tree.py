"""Вывод зависимостей пакета в виде ASCII-дерева."""

BRANCH = "├── "
LAST_BRANCH = "└── "
PIPE = "│   "
SPACE = "    "
CYCLE_MARK = " (цикл)"
REPEAT_MARK = " (*)"
TRUNCATED_MARK = " (...)"
MISSING_MARK = " (нет в репозитории)"


class TreePrinter:
    """Построитель ASCII-дерева по графу зависимостей.

    Обход в глубину выполняется без рекурсии. Поддерево каждого пакета
    раскрывается один раз -- при первом появлении; повторные появления
    помечаются ``(*)``. Ребро, ведущее в пакет на текущем пути от
    корня, помечается ``(цикл)``. Пакеты на глубине ``max_depth`` не
    раскрываются и при наличии зависимостей помечаются ``(...)``.
    """

    def __init__(self, graph, max_depth):
        """Сохранить граф и максимальную глубину дерева."""
        self.graph = graph
        self.max_depth = max_depth

    def render(self):
        """Вернуть ASCII-дерево зависимостей корневого пакета."""
        root = self.graph.root
        lines = [root]
        expanded = {root}
        stack = self._children_items(root, "", (root,))
        while stack:
            name, prefix, is_last, path = stack.pop()
            connector = LAST_BRANCH if is_last else BRANCH
            mark = self._mark(name, path, expanded)
            lines.append(f"{prefix}{connector}{name}{mark}")
            if mark or name in expanded or len(path) >= self.max_depth:
                continue
            expanded.add(name)
            child_prefix = prefix + (SPACE if is_last else PIPE)
            stack += self._children_items(name, child_prefix, path + (name,))
        return "\n".join(lines)

    def _children_items(self, node, prefix, path):
        """Вернуть элементы стека для зависимостей пакета.

        Элементы идут в обратном порядке, чтобы со стека они снимались
        в порядке указания зависимостей.
        """
        children = self.graph.edges.get(node, [])
        items = [
            (child, prefix, index == len(children) - 1, path)
            for index, child in enumerate(children)
        ]
        return items[::-1]

    def _mark(self, name, path, expanded):
        """Вернуть пометку пакета в дереве или пустую строку."""
        if name in path:
            return CYCLE_MARK
        if name in self.graph.missing:
            return MISSING_MARK
        has_children = bool(self.graph.edges.get(name))
        too_deep = len(path) >= self.max_depth
        if name in self.graph.truncated or (too_deep and has_children):
            return TRUNCATED_MARK
        if name in expanded and has_children:
            return REPEAT_MARK
        return ""


def ascii_tree(graph, max_depth):
    """Вернуть ASCII-дерево зависимостей корневого пакета графа."""
    return TreePrinter(graph, max_depth).render()
