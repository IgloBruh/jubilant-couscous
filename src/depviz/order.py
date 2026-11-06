"""Порядок загрузки зависимостей пакета."""


def load_order(graph):
    """Вернуть порядок загрузки пакетов графа.

    Каждый пакет идёт после всех своих зависимостей, корневой пакет --
    последним. Порядок -- обратный обход в глубину (postorder) от корня
    без рекурсии; зависимости перебираются в порядке их указания.
    Рёбра, замыкающие цикл, пропускаются: внутри цикла первым
    загружается пакет, до которого обход дошёл последним. Пакеты,
    отсутствующие в репозитории, в порядок не включаются.
    """
    order = []
    done = set()
    on_path = {graph.root}
    stack = [(graph.root, iter(graph.edges[graph.root]))]
    while stack:
        node, children = stack[-1]
        child = next(children, None)
        if child is None:
            stack.pop()
            on_path.discard(node)
            done.add(node)
            if node not in graph.missing:
                order.append(node)
        elif child not in done and child not in on_path:
            on_path.add(child)
            stack.append((child, iter(graph.edges[child])))
    return order
