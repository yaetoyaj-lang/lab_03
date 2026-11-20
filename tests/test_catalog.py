import json
from dataclasses import FrozenInstanceError, asdict, replace

import pytest

from bookcatalog import Book, Catalog
from bookcatalog.errors import (
    CatalogError,
    CorruptFileError,
    DuplicateIdError,
    InvalidItemError,
    ItemNotFoundError,
    UnsupportedVersionError,
)


@pytest.fixture
def book():
    return Book("b-20", "Мастер и Маргарита", "Роман", 1967, "Михаил Булгаков", 480)


def test_book(book):
    assert book.item_id == "b-20"
    assert book.pages == 480
    assert str(book) == "«Мастер и Маргарита», Михаил Булгаков, 1967 г."


@pytest.mark.parametrize(
    "fields",
    [
        {"item_id": " "},
        {"name": ""},
        {"category": ""},
        {"author": ""},
        {"year": 0},
        {"year": "1967"},
        {"pages": -1},
        {"pages": True},
    ],
)
def test_invalid_book(book, fields):
    with pytest.raises(InvalidItemError):
        replace(book, **fields)


def test_add_get_and_remove(book):
    catalog = Catalog()
    catalog.add(book)
    assert len(catalog) == 1
    assert book.item_id in catalog
    assert catalog.get(book.item_id) == book

    assert catalog.remove(book.item_id) == book
    assert len(catalog) == 0
    assert book.item_id not in catalog
    with pytest.raises(ItemNotFoundError, match="книга с ID 'b-20' не найдена"):
        catalog.get(book.item_id)
    with pytest.raises(ItemNotFoundError):
        catalog.remove(book.item_id)


def test_add_invalid_item():
    catalog = Catalog()
    with pytest.raises(InvalidItemError):
        catalog.add({"item_id": "b-1"})
    assert len(catalog) == 0


def test_duplicate_id(book):
    catalog = Catalog()
    catalog.add(book)
    with pytest.raises(DuplicateIdError, match="уже есть в каталоге"):
        catalog.add(replace(book, category="Другая категория"))
    assert list(catalog) == [book]
    assert catalog.find_by_category("Другая категория") == []


def test_search_and_category_index(book):
    second = replace(book, item_id="b-10", name="Отцы и дети")
    third = replace(book, item_id="b-30", name="Дама с собачкой", category="Рассказ")
    catalog = Catalog()
    for item in (book, second, third):
        catalog.add(item)

    assert catalog.find_by_name("МАСТЕР") == [book]
    assert catalog.find_by_name("поэма") == []
    assert catalog.find_by_category("Роман") == [book, second]
    assert catalog.find_by_category("Рассказ") == [third]

    catalog.find_by_category("Роман").clear()
    catalog.find_by_name("МАСТЕР").clear()
    assert catalog.find_by_category("Роман") == [book, second]
    assert catalog.find_by_name("МАСТЕР") == [book]

    catalog.remove(book.item_id)
    assert catalog.find_by_category("Роман") == [second]
    catalog.remove(second.item_id)
    assert catalog.find_by_category("Роман") == []


def test_iteration_order(book):
    catalog = Catalog()
    second = replace(book, item_id="b-10")
    catalog.add(book)
    catalog.add(second)
    assert list(catalog) == [book, second]

    catalog.remove(book.item_id)
    catalog.add(book)
    assert list(catalog) == [second, book]
    assert catalog.find_by_category(book.category) == [second, book]


def test_json_round_trip(book, tmp_path):
    second = replace(book, item_id="b-10", category="Рассказ")
    catalog = Catalog()
    catalog.add(book)
    catalog.add(second)
    path = tmp_path / "books.json"
    catalog.save_json(path)

    text = path.read_text(encoding="utf-8")
    assert json.loads(text)["format_version"] == 1
    assert "Мастер и Маргарита" in text

    loaded = Catalog()
    loaded.add(replace(book, item_id="old", category="Старая категория"))
    loaded.load_json(path)
    assert list(loaded) == [book, second]
    assert loaded.find_by_category("Рассказ") == [second]
    assert loaded.find_by_category("Старая категория") == []


@pytest.mark.parametrize(
    ("text", "error", "message"),
    [
        ("{", CorruptFileError, "не удалось разобрать JSON"),
        ('{"format_version": 42, "items": []}', UnsupportedVersionError, "не поддерживается"),
        ('{"format_version": true, "items": []}', CorruptFileError, "должно быть целым числом"),
        ('{"format_version": 1, "items": {}}', CorruptFileError, "должно быть списком"),
        ('{"format_version": 1, "items": [{"item_id": "bad"}]}', CorruptFileError, "набор полей"),
    ],
)
def test_unreadable_json(book, tmp_path, text, error, message):
    path = tmp_path / "books.json"
    path.write_text(text, encoding="utf-8")
    catalog = Catalog()
    catalog.add(book)
    with pytest.raises(error, match=message):
        catalog.load_json(path)
    assert list(catalog) == [book]


def test_cannot_save_json(tmp_path):
    with pytest.raises(CatalogError, match="не удалось записать файл"):
        Catalog().save_json(tmp_path / "missing" / "books.json")


@pytest.mark.parametrize("bad_fields", [{"pages": 0}, {"item_id": "new"}])
def test_load_does_not_apply_partial_data(book, tmp_path, bad_fields):
    path = tmp_path / "books.json"
    good = asdict(replace(book, item_id="new", category="Новая категория"))
    data = {"format_version": 1, "items": [good, dict(good, **bad_fields)]}
    path.write_text(json.dumps(data), encoding="utf-8")

    catalog = Catalog()
    catalog.add(book)
    with pytest.raises(CorruptFileError):
        catalog.load_json(path)
    assert list(catalog) == [book]
    assert catalog.find_by_category(book.category) == [book]
    assert catalog.find_by_category("Новая категория") == []


def test_read_only_view_is_a_snapshot(book):
    catalog = Catalog()
    catalog.add(book)
    snapshot = catalog.read_only_view()

    with pytest.raises(TypeError):
        snapshot[book.item_id] = replace(book, pages=200)
    with pytest.raises(FrozenInstanceError):
        snapshot[book.item_id].pages = 200

    catalog.remove(book.item_id)
    assert dict(snapshot) == {book.item_id: book}


def test_transaction_keeps_changes_on_success(book):
    catalog = Catalog()
    with catalog.transaction() as editing:
        editing.add(book)
    assert list(catalog) == [book]
    assert catalog.find_by_category(book.category) == [book]


def test_transaction_rolls_back_on_error(book, tmp_path):
    catalog = Catalog()
    second = replace(book, item_id="b-10")
    catalog.add(book)
    catalog.add(second)
    path = tmp_path / "broken.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(CorruptFileError), catalog.transaction():
        catalog.remove(book.item_id)
        catalog.add(replace(book, item_id="new", category="Новая категория"))
        catalog.load_json(path)

    assert list(catalog) == [book, second]
    assert catalog.find_by_category(book.category) == [book, second]
    assert catalog.find_by_category("Новая категория") == []
