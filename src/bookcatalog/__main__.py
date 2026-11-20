"""Пример запуска каталога"""

from bookcatalog.catalog import Catalog
from bookcatalog.models import Book


def main() -> None:
    catalog = Catalog()
    book = Book("b-1", "Отцы и дети", "Роман", 1862, "Иван Тургенев", 240)
    catalog.add(book)

    print("Поиск по названию «ОТЦЫ»")
    for found in catalog.find_by_name("ОТЦЫ"):
        print(found)


if __name__ == "__main__":
    main()
