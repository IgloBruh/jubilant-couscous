"""Тесты интерфейса командной строки."""

import contextlib
import io
import unittest
from pathlib import Path

from depviz.cli import (
    EXIT_CONFIG_ERROR,
    EXIT_OK,
    EXIT_PACKAGE_NOT_FOUND,
    EXIT_REPOSITORY_ERROR,
    main,
)

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def run_cli(config_path):
    """Запустить CLI с конфигурацией и вернуть код, stdout и stderr."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(["-c", str(config_path)])
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    """Проверка вывода и кодов завершения."""

    def test_prints_direct_dependencies(self):
        """Выводятся прямые зависимости пакета из тестового репозитория."""
        code, out, err = run_cli(EXAMPLES_DIR / "test_mode.xml")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(err, "")
        lines = out.splitlines()
        self.assertEqual(lines[0], "Пакет: A")
        self.assertIn("(2)", lines[1])
        self.assertEqual([line.strip() for line in lines[2:]], ["B", "C"])

    def test_config_error(self):
        """Ошибки конфигурации выводятся в stderr."""
        path = EXAMPLES_DIR / "errors" / "bad_values.xml"
        code, out, err = run_cli(path)
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertEqual(out, "")
        self.assertIn("Ошибка конфигурации", err)

    def test_repository_error(self):
        """Ошибка в файле тестового репозитория."""
        path = EXAMPLES_DIR / "errors" / "bad_test_repo.xml"
        code, _, err = run_cli(path)
        self.assertEqual(code, EXIT_REPOSITORY_ERROR)
        self.assertIn("строка 2", err)

    def test_unknown_package(self):
        """Пакет отсутствует в репозитории."""
        path = EXAMPLES_DIR / "errors" / "unknown_package.xml"
        code, _, err = run_cli(path)
        self.assertEqual(code, EXIT_PACKAGE_NOT_FOUND)
        self.assertIn("'Z'", err)


if __name__ == "__main__":
    unittest.main()
