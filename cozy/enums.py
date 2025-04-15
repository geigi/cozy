from enum import Enum, auto


class OpenView(Enum):
    AUTHOR = auto()
    READER = auto()
    BOOK = auto()
    LIBRARY = auto()
    BACK = auto()


class View(Enum):
    EMPTY_STATE = auto()
    PREPARING_LIBRARY = auto()
    LIBRARY = auto()
    LIBRARY_FILTER = auto()
    LIBRARY_BOOKS = auto()
    BOOK_DETAIL = auto()
    NO_MEDIA = auto()
