"""Точка входа для запуска пакета командой ``python -m depviz``."""

import sys

from depviz.cli import main

if __name__ == "__main__":
    sys.exit(main())
