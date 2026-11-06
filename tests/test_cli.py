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

    def test_prints_d2_and_tree(self):
        """Выводится описание на D2 и, если включено, ASCII-дерево."""
        code, out, err = run_cli(EXAMPLES_DIR / "test_mode.xml")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(err, "")
        d2_part, _, tree_part = out.rstrip().rpartition("\n\n")
        self.assertIn("# Граф зависимостей пакета A", d2_part)
        self.assertIn('"C" -> "E"', d2_part)
        self.assertIn('"E" -> "A": {', d2_part)
        self.assertEqual(tree_part.splitlines()[0], "A")
        self.assertIn("A (цикл)", tree_part)

    def test_no_tree_by_default(self):
        """При ascii_tree=false дерево не выводится."""
        _, out, _ = run_cli(EXAMPLES_DIR / "cases" / "diamond.xml")
        self.assertNotIn("└──", out)
        self.assertIn('"A" -> "B"', out)

    def test_all_cases(self):
        """Все демонстрационные конфигурации выполняются успешно."""
        for path in sorted((EXAMPLES_DIR / "cases").glob("*.xml")):
            with self.subTest(case=path.name):
                code, out, _ = run_cli(path)
                self.assertEqual(code, EXIT_OK)
                self.assertIn("direction: down", out)

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
