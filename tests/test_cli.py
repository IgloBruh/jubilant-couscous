"""Тесты интерфейса командной строки."""

import contextlib
import io
import unittest
from pathlib import Path

from depviz.cli import EXIT_CONFIG_ERROR, EXIT_OK, main

ROOT_DIR = Path(__file__).resolve().parent.parent


def run_cli(*args):
    """Запустить CLI и вернуть код завершения, stdout и stderr."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(args))
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    """Проверка вывода и кодов завершения."""

    def test_prints_key_value(self):
        """Корректная конфигурация выводится как ключ=значение."""
        code, out, err = run_cli("-c", str(ROOT_DIR / "config.xml"))
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(err, "")
        lines = out.splitlines()
        self.assertIn("package_name=busybox", lines)
        self.assertIn("ascii_tree=true", lines)
        self.assertIn("max_depth=3", lines)
        self.assertTrue(all("=" in line for line in lines))

    def test_error_exit_code(self):
        """Ошибки выводятся в stderr, код завершения ненулевой."""
        path = ROOT_DIR / "examples" / "errors" / "bad_values.xml"
        code, out, err = run_cli("-c", str(path))
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertEqual(out, "")
        self.assertIn("Ошибка конфигурации", err)


if __name__ == "__main__":
    unittest.main()
