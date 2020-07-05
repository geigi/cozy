from cozy.architecture.singleton import Singleton
from cozy.control.db import get_db
from cozy.model.book import Book
from cozy.model.library import Library
from cozy.open_view import OpenView
from cozy.ui.library_view import LibraryView
from cozy.ui.main_view import CozyUI
from cozy.ui.search_view import SearchView
from cozy.view_model.library_view_model import LibraryViewModel, LibraryViewMode
from cozy.view_model.search_view_model import SearchViewModel


class AppController(metaclass=Singleton):
    def __init__(self, main_window_builder, main_window):
        self.main_window: CozyUI = main_window
        self.library_model: Library = Library(get_db())

        self.library_view_model: LibraryViewModel = LibraryViewModel(self.library_model)
        self.search_view_model: SearchViewModel = SearchViewModel(self.library_model)

        self.library_view: LibraryView = LibraryView(main_window_builder, self.library_view_model)
        self.search_view: SearchView = SearchView(main_window_builder, self.search_view_model)

        self.search_view_model.add_listener(self._on_open_view)

    def open_author(self, author: str):
        self.library_view_model.library_view_mode = LibraryViewMode.AUTHOR
        self.library_view_model.selected_filter = author

    def open_reader(self, reader: str):
        self.library_view_model.library_view_mode = LibraryViewMode.READER
        self.library_view_model.selected_filter = reader

    def open_book(self, book: Book):
        self.main_window.jump_to_book(book.db_object)

    def _on_open_view(self, event, data):
        if event == OpenView.AUTHOR:
            self.open_author(data)
        elif event == OpenView.READER:
            self.open_reader(data)
        elif event == OpenView.BOOK:
            self.open_book(data)
