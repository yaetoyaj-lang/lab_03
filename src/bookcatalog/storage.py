import json
from collections.abc import Iterable
from dataclasses import asdict, fields
from pathlib import Path

from bookcatalog.constants import FORMAT_VERSION
from bookcatalog.errors import (
    CatalogError,
    CorruptFileError,
    InvalidItemError,
    UnsupportedVersionError,
)
from bookcatalog.models import Book

"""Запись книг в JSON"""
def write_books(path: str | Path, books: Iterable[Book]) -> None:
    data = {
        "format_version": FORMAT_VERSION,
        "items": [asdict(book) for book in books],
    }
    text = json.dumps(data, ensure_ascii=False, indent=2)
    try:
        Path(path).write_text(text + "\n", encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise CatalogError(f"не удалось записать файл {path!s}") from error

"""Чтение книг из JSON"""
def read_books(path: str | Path) -> list[Book]:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise CorruptFileError(f"не удалось прочитать файл {path!s} в UTF-8") from error

    try:
        data = json.loads(text)
    except (ValueError, RecursionError) as error:
        raise CorruptFileError("не удалось разобрать JSON") from error

    if not isinstance(data, dict):
        raise CorruptFileError("в корне JSON должен быть объект")

    version = data.get("format_version")
    if type(version) is not int:
        raise CorruptFileError("поле format_version должно быть целым числом")
    if version != FORMAT_VERSION:
        raise UnsupportedVersionError(f"версия формата {version} не поддерживается")

    items = data.get("items")
    if not isinstance(items, list):
        raise CorruptFileError("поле items должно быть списком")

    books = []
    field_names = {field.name for field in fields(Book)}
    for number, record in enumerate(items, start=1):
        if not isinstance(record, dict):
            raise CorruptFileError(f"запись {number} должна быть объектом")
        if record.keys() != field_names:
            raise CorruptFileError(f"в записи {number} неверный набор полей")
        try:
            book = Book(**record)
        except InvalidItemError as error:
            raise CorruptFileError(f"ошибка в записи {number} — {error}") from error
        books.append(book)
    return books
