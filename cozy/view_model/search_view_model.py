from cozy.application_settings import ApplicationSettings
from cozy.architecture.observable import Observable
from cozy.control.filesystem_monitor import FilesystemMonitor
from cozy.model.book import Book
from cozy.model.library import Library


class SearchViewModel(Observable):
    def __init__(self, model: Library):
        super().__init__()

        self._model: Library = model
        self._fs_monitor: FilesystemMonitor = FilesystemMonitor()
        self._application_settings: ApplicationSettings = ApplicationSettings()

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

        return sorted(authors)

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

        return sorted(readers)

    def jump_to_book(self, book: Book):
        pass

    def jump_to_author(self, book: Book):
        pass

    def jump_to_reader(self, book: Book):
        pass
