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

    def test_prints_graph(self):
        """Выводится граф зависимостей тестового репозитория."""
        code, out, err = run_cli(EXAMPLES_DIR / "test_mode.xml")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(err, "")
        lines = [line.strip() for line in out.splitlines()]
        self.assertEqual(lines[0], "Граф зависимостей пакета A")
        self.assertIn("Пакетов: 5, связей: 6", lines)
        self.assertIn("C -> D, E", lines)
        self.assertIn("Циклические зависимости (1):", lines)
        self.assertEqual(lines[-1], "E -> A")

    def test_load_order(self):
        """В режиме load_order выводится порядок загрузки."""
        code, out, _ = run_cli(EXAMPLES_DIR / "order" / "diamond.xml")
        self.assertEqual(code, EXIT_OK)
        lines = [line.strip() for line in out.splitlines()]
        start = lines.index("Порядок загрузки пакета A (4):") + 1
        self.assertEqual(
            lines[start:], ["1. D", "2. B", "3. C", "4. A"]
        )

    def test_no_load_order_by_default(self):
        """Без параметра load_order порядок не выводится."""
        _, out, _ = run_cli(EXAMPLES_DIR / "cases" / "diamond.xml")
        self.assertNotIn("Порядок загрузки", out)

    def test_all_cases(self):
        """Все демонстрационные конфигурации выполняются успешно."""
        for path in sorted((EXAMPLES_DIR / "cases").glob("*.xml")):
            with self.subTest(case=path.name):
                code, out, _ = run_cli(path)
                self.assertEqual(code, EXIT_OK)
                self.assertIn("Граф зависимостей", out)

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
