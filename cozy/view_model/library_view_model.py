from enum import Enum, auto

from cozy.architecture.observable import Observable


class LibraryViewMode(Enum):
    CURRENT = auto()
    AUTHOR = auto()
    READER = auto()


class LibraryViewModel(Observable, object):

    def __init__(self):
        super().__init__()

        self._library_view_mode: LibraryViewMode = LibraryViewMode.CURRENT
        self._is_any_book_in_progress_val = False
        self._selected_filter: str = _("All")

    @property
    def library_view_mode(self):
        return self._library_view_mode

    @library_view_mode.setter
    def library_view_mode(self, value):
        self._library_view_mode = value
        self._notify("library_view_mode", value)

    @property
    def selected_filter(self):
        return self._selected_filter

    @selected_filter.setter
    def selected_filter(self, value):
        self._selected_filter = value
        self._notify("selected_filter", value)

    @property
    def is_any_book_in_progress(self):
        return self._is_any_book_in_progress

    @property
    def _is_any_book_in_progress(self):
        return self._is_any_book_in_progress_val

    @_is_any_book_in_progress.setter
    def _is_any_book_in_progress(self, value):
        self._is_any_book_in_progress_val = value
        self._notify("is_any_book_in_progress", value)

    def display_book_filter(self, book_element):
        book = book_element.book

        if not book.is_currently_available():
            return False

        if self.selected_filter == _("All"):
            return True

        if self.library_view_mode == LibraryViewMode.CURRENT:
            return True if book.last_played > 0 else False
        elif self.library_view_mode == LibraryViewMode.AUTHOR:
            return True if book.get_author() == self.selected_filter else False
        elif self.library_view_mode == LibraryViewMode.READER:
            return True if book.get_reader() == self.selected_filter else False

    def display_book_sort(self, book_element1, book_element2):
        if self._library_view_mode == LibraryViewMode.CURRENT:
            return book_element1.book.last_played < book_element2.book.last_played
        else:
            return book_element1.book.name.lower() > book_element2.book.name.lower()
