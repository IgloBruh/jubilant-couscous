"""Текстовое представление графа зависимостей на языке диаграмм D2.

Особые случаи выделяются стилями: корневой пакет -- заливкой,
отсутствующие в репозитории пакеты -- красной рамкой и подписью,
нераскрытые из-за ограничения глубины -- пунктирной рамкой, рёбра,
замыкающие цикл, -- красной пунктирной линией.
"""

DIRECTION = "down"
ROOT_FILL = "#dbeafe"
MISSING_FILL = "#fee2e2"
WARNING_STROKE = "#dc2626"
TRUNCATED_DASH = 3
CYCLE_DASH = 5
INDENT = "  "


def quote(name):
    """Записать имя пакета строкой D2 в двойных кавычках."""
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def block(key, attributes):
    """Сформировать объявление D2 с атрибутами или без них."""
    if not attributes:
        return [key]
    lines = [f"{key}: {{"]
    lines += [f"{INDENT}{name}: {value}" for name, value in attributes]
    lines.append("}")
    return lines


def node_attributes(graph, node):
    """Вернуть атрибуты D2 для пакета в зависимости от его роли."""
    attributes = []
    if node == graph.root:
        attributes += [("style.fill", quote(ROOT_FILL)), ("style.bold", "true")]
    if node in graph.missing:
        attributes += [
            ("label", quote(f"{node} (нет в репозитории)")),
            ("style.fill", quote(MISSING_FILL)),
            ("style.stroke", quote(WARNING_STROKE)),
        ]
    if node in graph.truncated:
        attributes += [
            ("label", quote(f"{node} (не раскрыт)")),
            ("style.stroke-dash", str(TRUNCATED_DASH)),
        ]
    return attributes


def edge_attributes(graph, source, target):
    """Вернуть атрибуты D2 для ребра; цикл выделяется."""
    if (source, target) not in graph.cycles:
        return []
    return [
        ("style.stroke", quote(WARNING_STROKE)),
        ("style.stroke-dash", str(CYCLE_DASH)),
    ]


def header_lines(graph, config):
    """Сформировать комментарии D2 с параметрами анализа."""
    filter_text = config.filter_substring or "нет"
    lines = [
        f"# Граф зависимостей пакета {graph.root}",
        f"# Максимальная глубина: {config.max_depth}; фильтр: {filter_text}",
        f"# Пакетов: {len(graph.nodes)}, связей: {graph.edge_count()}",
    ]
    if graph.filtered:
        filtered = ", ".join(sorted(graph.filtered))
        lines.append(f"# Исключены фильтром: {filtered}")
    return lines


def to_d2(graph, config):
    """Вернуть описание графа на языке D2."""
    lines = header_lines(graph, config)
    lines.append(f"direction: {DIRECTION}")
    lines.append("")
    for node in graph.nodes:
        lines += block(quote(node), node_attributes(graph, node))
    lines.append("")
    for source, targets in graph.edges.items():
        for target in targets:
            key = f"{quote(source)} -> {quote(target)}"
            lines += block(key, edge_attributes(graph, source, target))
    return "\n".join(lines)
