from cozy.architecture.singleton import Singleton
from cozy.control.db import get_db
from cozy.model.library import Library
from cozy.ui.library_view import LibraryView
from cozy.ui.search_view import SearchView
from cozy.view_model.library_view_model import LibraryViewModel
from cozy.view_model.search_view_model import SearchViewModel


class AppController(metaclass=Singleton):
    def __init__(self, main_window_builder):
        self.library_model: Library = Library(get_db())

        self.library_view_model: LibraryViewModel = LibraryViewModel(self.library_model)
        self.search_view_model: SearchViewModel = SearchViewModel(self.library_model)

        self.library_view: LibraryView = LibraryView(main_window_builder, self.library_view_model)
        self.search_view: SearchView = SearchView(main_window_builder, self.search_view_model)
