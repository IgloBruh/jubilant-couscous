"""Интерфейс командной строки."""

import argparse
import sys

from depviz.apkindex import PackageNotFoundError
from depviz.config import ConfigError, load_config
from depviz.graph import build_graph
from depviz.render import format_graph
from depviz.repository import RepositoryError, open_repository

DEFAULT_CONFIG = "config.xml"
EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_REPOSITORY_ERROR = 2
EXIT_PACKAGE_NOT_FOUND = 3


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
        graph = build_graph(open_repository(config), config)
    except ConfigError as exc:
        report_error("Ошибка конфигурации", exc.errors)
        return EXIT_CONFIG_ERROR
    except RepositoryError as exc:
        report_error("Ошибка репозитория", [str(exc)])
        return EXIT_REPOSITORY_ERROR
    except PackageNotFoundError as exc:
        report_error("Ошибка", [str(exc)])
        return EXIT_PACKAGE_NOT_FOUND
    print(format_graph(graph, config))
    return EXIT_OK
