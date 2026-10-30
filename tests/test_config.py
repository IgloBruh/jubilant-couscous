"""Тесты загрузки и проверки XML-конфигурации."""

import tempfile
import unittest
from pathlib import Path

from depviz.config import ConfigError, load_config

VALID_URL = "https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64"
EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def make_xml(**fields):
    """Собрать текст XML-конфигурации из именованных параметров."""
    body = "".join(f"<{key}>{value}</{key}>" for key, value in fields.items())
    return f"<config>{body}</config>"


def valid_fields(**overrides):
    """Вернуть корректный набор параметров с заменой части значений."""
    fields = {
        "package_name": "busybox",
        "repository": VALID_URL,
        "test_repo_mode": "false",
        "ascii_tree": "true",
        "max_depth": "3",
        "filter_substring": "doc",
    }
    fields.update(overrides)
    return fields


class ConfigTestCase(unittest.TestCase):
    """Базовый класс с временным каталогом для файлов конфигурации."""

    def setUp(self):
        """Создать временный каталог."""
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        """Удалить временный каталог."""
        self.tmp.cleanup()

    def write(self, text, name="config.xml"):
        """Записать текст в файл во временном каталоге и вернуть путь."""
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def assert_errors(self, text, *fragments):
        """Проверить, что загрузка падает и ошибки содержат фрагменты."""
        with self.assertRaises(ConfigError) as ctx:
            load_config(self.write(text))
        message = str(ctx.exception)
        for fragment in fragments:
            self.assertIn(fragment, message)
        return ctx.exception.errors


class ValidConfigTests(ConfigTestCase):
    """Корректные конфигурации."""

    def test_all_fields(self):
        """Все параметры считываются и приводятся к нужным типам."""
        config = load_config(self.write(make_xml(**valid_fields())))
        self.assertEqual(config.package_name, "busybox")
        self.assertEqual(config.repository, VALID_URL)
        self.assertFalse(config.test_repo_mode)
        self.assertTrue(config.ascii_tree)
        self.assertEqual(config.max_depth, 3)
        self.assertEqual(config.filter_substring, "doc")

    def test_filter_is_optional(self):
        """Подстрока фильтрации необязательна и по умолчанию пуста."""
        fields = valid_fields()
        del fields["filter_substring"]
        config = load_config(self.write(make_xml(**fields)))
        self.assertEqual(config.filter_substring, "")

    def test_test_mode_relative_path(self):
        """Путь к тестовому репозиторию отсчитывается от конфигурации."""
        repo = self.write("A: B\n", name="repo.txt")
        fields = valid_fields(repository="repo.txt", test_repo_mode="yes")
        config = load_config(self.write(make_xml(**fields)))
        self.assertEqual(Path(config.repository), repo)

    def test_as_pairs(self):
        """Логические значения выводятся как true/false."""
        config = load_config(self.write(make_xml(**valid_fields())))
        pairs = dict(config.as_pairs())
        self.assertEqual(pairs["ascii_tree"], "true")
        self.assertEqual(pairs["test_repo_mode"], "false")
        self.assertEqual(pairs["max_depth"], "3")

    def test_example_test_mode(self):
        """Пример конфигурации тестового режима корректен."""
        config = load_config(EXAMPLES_DIR / "test_mode.xml")
        self.assertTrue(config.test_repo_mode)


class FileErrorTests(ConfigTestCase):
    """Ошибки чтения файла и структуры XML."""

    def test_missing_file(self):
        """Отсутствующий файл конфигурации."""
        with self.assertRaises(ConfigError) as ctx:
            load_config(self.dir / "absent.xml")
        self.assertIn("не найден", str(ctx.exception))

    def test_malformed_xml(self):
        """Синтаксически некорректный XML."""
        self.assert_errors("<config><a></config>", "некорректный XML")

    def test_wrong_root(self):
        """Неверный корневой элемент."""
        self.assert_errors("<settings/>", "корневой элемент")

    def test_unknown_duplicate_nested(self):
        """Неизвестный, повторный и составной параметры."""
        text = (
            "<config><package_name>a</package_name>"
            "<package_name>b</package_name><colour>red</colour>"
            "<max_depth><v>3</v></max_depth></config>"
        )
        self.assert_errors(
            text,
            "неизвестный параметр <colour>",
            "более одного раза",
            "вложенных тегов",
            "отсутствует обязательный параметр <repository>",
        )


class FieldErrorTests(ConfigTestCase):
    """Ошибки значений отдельных параметров."""

    def check_field(self, name, value, fragment):
        """Проверить ошибку для одного неверного параметра."""
        text = make_xml(**valid_fields(**{name: value}))
        errors = self.assert_errors(text, fragment)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith(name))

    def test_package_name(self):
        """Пустое или недопустимое имя пакета."""
        self.check_field("package_name", "", "недопустимое имя")
        self.check_field("package_name", "a b", "недопустимое имя")

    def test_repository(self):
        """Пустой адрес и некорректный URL."""
        self.check_field("repository", "", "не может быть пустым")
        self.check_field("repository", "ftp://x.org", "некорректный URL")
        self.check_field("repository", "not a url", "некорректный URL")

    def test_missing_test_repo_file(self):
        """Файл тестового репозитория не существует."""
        fields = valid_fields(repository="nope.txt", test_repo_mode="true")
        self.assert_errors(make_xml(**fields), "не найден")

    def test_bool_fields(self):
        """Некорректные логические значения."""
        self.check_field("test_repo_mode", "maybe", "логическое")
        self.check_field("ascii_tree", "2", "логическое")

    def test_max_depth(self):
        """Нечисловая глубина и глубина вне диапазона."""
        self.check_field("max_depth", "abc", "целое число")
        self.check_field("max_depth", "0", "диапазоне")
        self.check_field("max_depth", "1000", "диапазоне")

    def test_filter_substring(self):
        """Подстрока с пробелами."""
        self.check_field("filter_substring", "a b", "пробельных")

    def test_all_errors_reported(self):
        """Сообщаются ошибки по всем параметрам сразу."""
        errors = self.assert_errors(
            (EXAMPLES_DIR / "errors" / "bad_values.xml").read_text("utf-8")
        )
        self.assertEqual(len(errors), len(valid_fields()))


if __name__ == "__main__":
    unittest.main()
