"""Текстовое представление графа зависимостей."""

EDGE_ARROW = " -> "


def format_edges(graph):
    """Перечислить пакеты графа с их прямыми зависимостями."""
    lines = []
    for node, children in graph.edges.items():
        if children:
            lines.append(f"  {node}{EDGE_ARROW}{', '.join(children)}")
        else:
            lines.append(f"  {node}")
    return lines


def format_section(title, items):
    """Сформировать раздел отчёта; пустой список даёт пустой раздел."""
    if not items:
        return []
    return [f"{title} ({len(items)}):", *(f"  {item}" for item in items)]


def format_graph(graph, config):
    """Сформировать текстовый отчёт о графе зависимостей."""
    filter_text = config.filter_substring or "нет"
    lines = [
        f"Граф зависимостей пакета {graph.root}",
        f"Максимальная глубина: {config.max_depth}; фильтр: {filter_text}",
        f"Пакетов: {len(graph.nodes)}, связей: {graph.edge_count()}",
        "Связи:",
        *format_edges(graph),
    ]
    cycles = [f"{source}{EDGE_ARROW}{target}"
              for source, target in graph.cycles]
    lines += format_section("Циклические зависимости", cycles)
    lines += format_section(
        "Не раскрыты из-за ограничения глубины", sorted(graph.truncated)
    )
    lines += format_section("Исключены фильтром", sorted(graph.filtered))
    lines += format_section("Не найдены в репозитории", sorted(graph.missing))
    return "\n".join(lines)
