from typing import Callable

import inject
from gi.repository import GLib

from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.control.filesystem_monitor import FilesystemMonitor

<<<<<<< HEAD
from cozy.enums import OpenView
from cozy.extensions.set import split_strings_to_set
from cozy.model.book import Book
from cozy.model.library import Library
from cozy.settings import ApplicationSettings

=======
from cozy.model.book import Book
from cozy.model.library import Library, split_strings_to_set
from cozy.open_view import OpenView

>>>>>>> master


class SearchViewModel(Observable, EventSender):
    _fs_monitor: FilesystemMonitor = inject.attr("FilesystemMonitor")
    _model: Library = inject.attr(Library)
    _application_settings: ApplicationSettings = inject.attr(ApplicationSettings)

    def __init__(self):
        super().__init__()
        super(Observable, self).__init__()

    def _get_available_books(self) -> list[Book]:
        is_book_online = self._fs_monitor.get_book_online

        if self._application_settings.hide_offline:
            return [book for book in self._model.books if is_book_online(book)]
        else:
            return self._model.books

    def search(
        self, search_query: str, callback: Callable[[list[Book], list[str], list[str]], None]
    ) -> None:
        search_query = search_query.lower()

        available_books = self._get_available_books()
        books = {
            book
            for book in available_books
            if search_query in book.name.lower()
            or search_query in book.author.lower()
            or search_query in book.reader.lower()
        }

        available_book_authors = split_strings_to_set({book.author for book in available_books})
        authors = {author for author in available_book_authors if search_query in author.lower()}

        available_book_readers = split_strings_to_set({book.reader for book in available_books})
        readers = {reader for reader in available_book_readers if search_query in reader.lower()}

        GLib.MainContext.default().invoke_full(
            GLib.PRIORITY_DEFAULT,
            callback,
            sorted(books, key=lambda book: book.name.lower()),
            sorted(authors),
            sorted(readers),
        )

    def close(self) -> None:
        self._notify("close")

    def jump_to_book(self, book: Book) -> None:
        self.emit_event(OpenView.BOOK, book)
        self.close()

    def jump_to_author(self, author: str) -> None:
        self.emit_event(OpenView.AUTHOR, author)
        self.close()

    def jump_to_reader(self, reader: str) -> None:
        self.emit_event(OpenView.READER, reader)
        self.close()
