import inject

from cozy.extensions.set import split_strings_to_set
from cozy.open_view import OpenView
from cozy.application_settings import ApplicationSettings
from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.control.filesystem_monitor import FilesystemMonitor
from cozy.model.book import Book
from cozy.model.library import Library


class SearchViewModel(Observable, EventSender):
    _fs_monitor: FilesystemMonitor = inject.attr(FilesystemMonitor)

    def __init__(self, model: Library):
        super().__init__()

        self._model: Library = model
        self._application_settings: ApplicationSettings = ApplicationSettings()

        self._search_open: bool = False

    @property
    def books(self):
        return self._model.books

    @property
    def authors(self):
        is_book_online = self._fs_monitor.get_book_online
        show_offline_books = not self._application_settings.hide_offline
        swap_author_reader = self._application_settings.swap_author_reader

        authors = {
            book.author if not swap_author_reader else book.reader
            for book
            in self._model.books
            if is_book_online(book) or show_offline_books
        }

        return sorted(split_strings_to_set(authors))

    @property
    def readers(self):
        is_book_online = self._fs_monitor.get_book_online
        show_offline_books = not self._application_settings.hide_offline
        swap_author_reader = self._application_settings.swap_author_reader

        readers = {
            book.reader if not swap_author_reader else book.author
            for book
            in self._model.books
            if is_book_online(book) or show_offline_books
        }

        return sorted(split_strings_to_set(readers))

    @property
    def search_open(self):
        return self._search_open

    @search_open.setter
    def search_open(self, value):
        self._search_open = value
        self._notify("search_open")

    def jump_to_book(self, book: Book):
        self.emit_event(OpenView.BOOK, book)
        self.search_open = False

    def jump_to_author(self, author: str):
        self.emit_event(OpenView.AUTHOR, author)
        self.search_open = False

    def jump_to_reader(self, reader: str):
        self.emit_event(OpenView.READER, reader)
        self.search_open = False
