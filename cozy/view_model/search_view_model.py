from typing import Callable

from gi.repository import GLib

import cozy.ext.inject as inject
from cozy.application_settings import ApplicationSettings
from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.control.filesystem_monitor import FilesystemMonitor
from cozy.extensions.set import split_strings_to_set
from cozy.model.book import Book
from cozy.model.library import Library
from cozy.open_view import OpenView


class SearchViewModel(Observable, EventSender):
    _fs_monitor: FilesystemMonitor = inject.attr("FilesystemMonitor")
    _model: Library = inject.attr(Library)
    _application_settings: ApplicationSettings = inject.attr(ApplicationSettings)

    def __init__(self):
        super().__init__()
        super(Observable, self).__init__()

    @property
    def authors(self):
        is_book_online = self._fs_monitor.get_book_online
        show_offline_books = not self._application_settings.hide_offline

        authors = {
            book.author for book in self._model.books if is_book_online(book) or show_offline_books
        }

        return split_strings_to_set(authors)

    @property
    def readers(self):
        is_book_online = self._fs_monitor.get_book_online
        show_offline_books = not self._application_settings.hide_offline

        readers = {
            book.reader for book in self._model.books if is_book_online(book) or show_offline_books
        }

        return split_strings_to_set(readers)

    def search(
        self, search_query: str, callback: Callable[[list[Book], list[str], list[str]], None]
    ) -> None:
        search_query = search_query.lower()

        books = {
            book
            for book in self._model.books
            if search_query in book.name.lower()
            or search_query in book.author.lower()
            or search_query in book.reader.lower()
        }

        authors = {author for author in self.authors if search_query in author.lower()}
        readers = {reader for reader in self.readers if search_query in reader.lower()}

        GLib.MainContext.default().invoke_full(
            GLib.PRIORITY_DEFAULT,
            callback,
            sorted(books, key=lambda book: book.name.lower()),
            sorted(authors),
            sorted(readers),
        )

    def close(self):
        self._notify("close")

    def jump_to_book(self, book: Book):
        self.emit_event(OpenView.BOOK, book)
        self.close()

    def jump_to_author(self, author: str):
        self.emit_event(OpenView.AUTHOR, author)
        self.close()

    def jump_to_reader(self, reader: str):
        self.emit_event(OpenView.READER, reader)
        self.close()
