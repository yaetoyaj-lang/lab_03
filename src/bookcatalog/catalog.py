"""Хранение и поиск книг"""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from types import MappingProxyType

from bookcatalog.errors import (
    CorruptFileError,
    DuplicateIdError,
    InvalidItemError,
    ItemNotFoundError,
)
from bookcatalog.models import Book
from bookcatalog.storage import read_books, write_books


class Catalog:
    """Каталог книг с итерацией в порядке добавления"""

    def __init__(self) -> None:
        self._books: dict[str, Book] = {}
        self._by_category: dict[str, dict[str, Book]] = {}

    def add(self, item: Book) -> None:
        if type(item) is not Book:
            raise InvalidItemError("в каталог можно добавлять только книги")
        if item.item_id in self:
            raise DuplicateIdError(f"книга с ID {item.item_id!r} уже есть в каталоге")

        self._books[item.item_id] = item
        self._by_category.setdefault(item.category, {})[item.item_id] = item

    def get(self, item_id: str) -> Book:
        try:
            return self._books[item_id]
        except KeyError:
            raise ItemNotFoundError(f"книга с ID {item_id!r} не найдена") from None

    def remove(self, item_id: str) -> Book:
        item = self.get(item_id)
        del self._books[item_id]

        category_books = self._by_category[item.category]
        del category_books[item_id]
        if not category_books:
            del self._by_category[item.category]
        return item

    def find_by_category(self, category: str) -> list[Book]:
        return list(self._by_category.get(category, {}).values())

    def find_by_name(self, query: str) -> list[Book]:
        query = query.casefold()
        return [book for book in self if query in book.name.casefold()]

    def __len__(self) -> int:
        return len(self._books)

    def __iter__(self) -> Iterator[Book]:
        return iter(self._books.values())

    def __contains__(self, item_id: object) -> bool:
        return isinstance(item_id, str) and item_id in self._books

    def read_only_view(self) -> Mapping[str, Book]:
        """Снимок каталога только для чтения"""
        return MappingProxyType(self._books.copy())

    @contextmanager
    def transaction(self) -> Iterator["Catalog"]:
        """Откат изменений при ошибке в блоке with"""
        books_before = self._books.copy()
        categories_before = {
            category: books.copy() for category, books in self._by_category.items()
        }
        try:
            yield self
        except BaseException:
            self._books = books_before
            self._by_category = categories_before
            raise

    def save_json(self, path: str | Path) -> None:
        write_books(path, self)

    def load_json(self, path: str | Path) -> None:
        books = read_books(path)
        loaded = Catalog()
        for number, book in enumerate(books, start=1):
            try:
                loaded.add(book)
            except DuplicateIdError as error:
                raise CorruptFileError(f"ошибка в записи {number} — {error}") from error

        self._books = loaded._books
        self._by_category = loaded._by_category
