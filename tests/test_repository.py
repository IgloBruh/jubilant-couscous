"""Тесты загрузки индекса из репозитория и тестового файла."""

import io
import tarfile
import unittest
import urllib.error
from unittest import mock

from depviz.repository import (
    RepositoryError,
    extract_index,
    index_url,
    load_remote_index,
    parse_test_repo,
)

REPO_URL = "https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64"
INDEX_TEXT = (
    "P:busybox\nV:1.36\nD:so:libc.musl-x86_64.so.1\n\n"
    "P:musl\np:so:libc.musl-x86_64.so.1=1\n"
)


def make_archive(files):
    """Создать архив tar.gz в памяти из словаря {имя: текст}."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, text in files.items():
            data = text.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def fake_response(data):
    """Создать подмену ответа urlopen с заданным телом."""
    response = mock.MagicMock()
    response.__enter__.return_value.read.return_value = data
    return response


class IndexUrlTests(unittest.TestCase):
    """Построение URL архива индекса."""

    def test_appends_archive(self):
        """К URL каталога добавляется имя архива."""
        expected = f"{REPO_URL}/APKINDEX.tar.gz"
        self.assertEqual(index_url(REPO_URL), expected)
        self.assertEqual(index_url(REPO_URL + "/"), expected)

    def test_keeps_archive_url(self):
        """URL архива не изменяется."""
        url = f"{REPO_URL}/APKINDEX.tar.gz"
        self.assertEqual(index_url(url), url)


class ExtractIndexTests(unittest.TestCase):
    """Извлечение APKINDEX из архива."""

    def test_extract(self):
        """Текст индекса извлекается рядом с другими файлами."""
        archive = make_archive({"DESCRIPTION": "x", "APKINDEX": INDEX_TEXT})
        self.assertEqual(extract_index(archive), INDEX_TEXT)

    def test_missing_member(self):
        """В архиве нет файла APKINDEX."""
        with self.assertRaises(RepositoryError):
            extract_index(make_archive({"DESCRIPTION": "x"}))

    def test_corrupted_archive(self):
        """Данные не являются архивом."""
        with self.assertRaises(RepositoryError):
            extract_index(b"not an archive")


class LoadRemoteIndexTests(unittest.TestCase):
    """Загрузка индекса по сети (с подменой urlopen)."""

    @mock.patch("urllib.request.urlopen")
    def test_success(self, urlopen):
        """Индекс скачивается и разбирается."""
        archive = make_archive({"APKINDEX": INDEX_TEXT})
        urlopen.return_value = fake_response(archive)
        index = load_remote_index(REPO_URL)
        deps = index.direct_dependencies("busybox")
        self.assertEqual([dep.name for dep in deps], ["musl"])
        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/APKINDEX.tar.gz"))

    @mock.patch("urllib.request.urlopen")
    def test_http_error(self, urlopen):
        """Ответ сервера с кодом ошибки."""
        urlopen.side_effect = urllib.error.HTTPError(
            REPO_URL, 404, "Not Found", None, None
        )
        with self.assertRaisesRegex(RepositoryError, "404"):
            load_remote_index(REPO_URL)

    @mock.patch("urllib.request.urlopen")
    def test_connection_error(self, urlopen):
        """Сервер недоступен."""
        urlopen.side_effect = urllib.error.URLError("no route")
        with self.assertRaisesRegex(RepositoryError, "подключиться"):
            load_remote_index(REPO_URL)


class TestRepoTests(unittest.TestCase):
    """Разбор файла тестового репозитория."""

    def test_parse(self):
        """Пакеты и зависимости считываются, пустые строки пропускаются."""
        index = parse_test_repo("A: B C\n\nB:\nC: B\n")
        deps = index.direct_dependencies("A")
        self.assertEqual([dep.name for dep in deps], ["B", "C"])
        self.assertEqual(index.direct_dependencies("B"), [])

    def test_undefined_dependency(self):
        """Зависимость без описания помечается как не найденная."""
        deps = parse_test_repo("A: B\n").direct_dependencies("A")
        self.assertFalse(deps[0].found)

    def test_errors(self):
        """Ошибки формата: нет двоеточия, плохое имя, повтор пакета."""
        for text in ("A B\n", "A: b\n", "a: B\n", "A: B\nA: C\n"):
            with self.subTest(text=text):
                with self.assertRaises(RepositoryError):
                    parse_test_repo(text)


if __name__ == "__main__":
    unittest.main()
