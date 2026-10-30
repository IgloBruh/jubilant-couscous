"""Получение индекса пакетов из репозитория Alpine Linux или из файла
тестового репозитория."""

import io
import re
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

from depviz.apkindex import ApkIndex, Package, parse_index

INDEX_ARCHIVE = "APKINDEX.tar.gz"
INDEX_MEMBER = "APKINDEX"
TIMEOUT_SECONDS = 30
USER_AGENT = "depviz/0.2"
TEST_NAME_RE = re.compile(r"^[A-Z]+$")
TEST_SEPARATOR = ":"


class RepositoryError(Exception):
    """Не удалось получить или разобрать данные репозитория."""


def index_url(repository_url):
    """Вернуть URL архива индекса для URL репозитория.

    Если URL уже указывает на ``APKINDEX.tar.gz``, он не изменяется.
    """
    if repository_url.endswith(INDEX_ARCHIVE):
        return repository_url
    return f"{repository_url.rstrip('/')}/{INDEX_ARCHIVE}"


def download(url):
    """Скачать содержимое по URL и вернуть его в виде байтов."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise RepositoryError(
            f"сервер вернул ошибку {exc.code} для {url}"
        ) from None
    except urllib.error.URLError as exc:
        raise RepositoryError(
            f"не удалось подключиться к {url}: {exc.reason}"
        ) from None
    except (TimeoutError, OSError) as exc:
        raise RepositoryError(f"ошибка загрузки {url}: {exc}") from None


def extract_index(archive):
    """Извлечь текст файла APKINDEX из архива ``APKINDEX.tar.gz``."""
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            member = tar.extractfile(INDEX_MEMBER)
            if member is None:
                raise KeyError(INDEX_MEMBER)
            return member.read().decode("utf-8")
    except KeyError:
        raise RepositoryError(
            f"в архиве индекса нет файла {INDEX_MEMBER}"
        ) from None
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise RepositoryError(f"повреждённый архив индекса: {exc}") from None
    except UnicodeDecodeError:
        raise RepositoryError("индекс не в кодировке UTF-8") from None


def load_remote_index(repository_url):
    """Скачать и разобрать индекс репозитория по его URL."""
    return parse_index(extract_index(download(index_url(repository_url))))


def parse_test_line(line, number):
    """Разобрать строку тестового репозитория вида ``A: B C``."""
    name, sep, rest = line.partition(TEST_SEPARATOR)
    if not sep:
        raise RepositoryError(
            f"строка {number}: ожидался формат 'ПАКЕТ: ЗАВИСИМОСТИ'"
        )
    name = name.strip()
    depends = tuple(rest.split())
    for item in (name, *depends):
        if not TEST_NAME_RE.match(item):
            raise RepositoryError(
                f"строка {number}: имя пакета {item!r} должно состоять "
                "из больших латинских букв"
            )
    return Package(name=name, depends=depends)


def parse_test_repo(text):
    """Разобрать описание тестового репозитория.

    Каждая непустая строка описывает пакет и его прямые зависимости:
    ``A: B C``. Имена пакетов -- большие латинские буквы.
    """
    packages = {}
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        package = parse_test_line(line, number)
        if package.name in packages:
            raise RepositoryError(
                f"строка {number}: пакет {package.name} описан повторно"
            )
        packages[package.name] = package
    return ApkIndex(packages.values())


def load_test_repo(path):
    """Прочитать и разобрать файл тестового репозитория."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise RepositoryError(
            f"не удалось прочитать тестовый репозиторий {path}: {exc}"
        ) from None
    return parse_test_repo(text)


def open_repository(config):
    """Загрузить индекс пакетов в соответствии с конфигурацией."""
    if config.test_repo_mode:
        return load_test_repo(config.repository)
    return load_remote_index(config.repository)
