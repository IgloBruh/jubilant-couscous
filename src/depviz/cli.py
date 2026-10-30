"""Интерфейс командной строки."""

import argparse
import sys

from depviz.config import ConfigError, load_config

DEFAULT_CONFIG = "config.xml"
EXIT_OK = 0
EXIT_CONFIG_ERROR = 1


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


def format_config(config):
    """Представить конфигурацию строками вида ``ключ=значение``."""
    return "\n".join(f"{key}={value}" for key, value in config.as_pairs())


def main(argv=None):
    """Запустить приложение и вернуть код завершения."""
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print("Ошибка конфигурации:", file=sys.stderr)
        for error in exc.errors:
            print(f"  - {error}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    print(format_config(config))
    return EXIT_OK
