class CatalogError(Exception):
    """Базовая ошибка"""


class InvalidItemError(CatalogError):
    """Неверные данные книги"""


class DuplicateIdError(CatalogError):
    """Повторяющийся ID"""


class ItemNotFoundError(CatalogError):
    """Нет ID"""


class UnsupportedVersionError(CatalogError):
    """Неподдерживаемая версия формата"""


class CorruptFileError(CatalogError):
    """Ошибка чтения"""
