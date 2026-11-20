from dataclasses import dataclass
from bookcatalog.errors import InvalidItemError


@dataclass(frozen=True)
class Book:
    """Книга с неизменяемыми полями"""

    item_id: str
    name: str
    category: str
    year: int
    author: str
    pages: int

    def __post_init__(self) -> None:
        for field_name in ("item_id", "name", "category", "author"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise InvalidItemError(f"поле {field_name} должно быть непустой строкой")

        if type(self.year) is not int or self.year <= 0:
            raise InvalidItemError("год издания должен быть положительным целым числом")

        if type(self.pages) is not int or self.pages <= 0:
            raise InvalidItemError("число страниц должно быть положительным целым числом")

    def __str__(self) -> str:
        return f"«{self.name}», {self.author}, {self.year} г."
