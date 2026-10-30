"""Интерфейс командной строки."""

import argparse
import sys

from depviz.apkindex import PackageNotFoundError
from depviz.config import ConfigError, load_config
from depviz.repository import RepositoryError, open_repository

DEFAULT_CONFIG = "config.xml"
EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_REPOSITORY_ERROR = 2
EXIT_PACKAGE_NOT_FOUND = 3
NAME_COLUMN_WIDTH = 24


def build_parser():
    """Создать парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="depviz",
        description="Визуализация графа зависимостей пакетов Alpine Linux.",
    )
    parser.add_argument(
        "-c",
        "--config",
        default=DEFAULT_CONFIG,
        help=f"путь к XML-файлу конфигурации (по умолчанию {DEFAULT_CONFIG})",
    )
    return parser


def format_dependency(dependency):
    """Представить одну прямую зависимость строкой вывода."""
    if not dependency.found:
        return f"  {dependency.name}  (не найден в репозитории)"
    requirements = ", ".join(dependency.requirements)
    if requirements == dependency.name:
        return f"  {dependency.name}"
    return f"  {dependency.name:<{NAME_COLUMN_WIDTH}} {requirements}"


def format_dependencies(package, dependencies):
    """Сформировать текст со списком прямых зависимостей пакета."""
    title = f"{package.name} {package.version}".rstrip()
    lines = [f"Пакет: {title}"]
    if not dependencies:
        lines.append("Прямые зависимости отсутствуют")
        return "\n".join(lines)
    lines.append(f"Прямые зависимости ({len(dependencies)}):")
    lines.extend(format_dependency(dep) for dep in dependencies)
    return "\n".join(lines)


def report_error(title, messages):
    """Вывести сообщения об ошибке в stderr."""
    print(f"{title}:", file=sys.stderr)
    for message in messages:
        print(f"  - {message}", file=sys.stderr)


def main(argv=None):
    """Запустить приложение и вернуть код завершения."""
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        index = open_repository(config)
        package = index.get(config.package_name)
        dependencies = index.direct_dependencies(config.package_name)
    except ConfigError as exc:
        report_error("Ошибка конфигурации", exc.errors)
        return EXIT_CONFIG_ERROR
    except RepositoryError as exc:
        report_error("Ошибка репозитория", [str(exc)])
        return EXIT_REPOSITORY_ERROR
    except PackageNotFoundError as exc:
        report_error("Ошибка", [str(exc)])
        return EXIT_PACKAGE_NOT_FOUND
    print(format_dependencies(package, dependencies))
    return EXIT_OK
