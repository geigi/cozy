from gi.repository import Gio

import cozy.ext.inject as inject
from peewee import SqliteDatabase

from cozy.media.files import Files
from cozy.report import reporter
from cozy.application_settings import ApplicationSettings
from cozy.architecture.singleton import Singleton
from cozy.control.db import get_db
from cozy.control.filesystem_monitor import FilesystemMonitor
from cozy.model.book import Book
from cozy.model.library import Library
from cozy.model.settings import Settings
from cozy.model.storage_block_list import StorageBlockList
from cozy.open_view import OpenView
from cozy.ui.library_view import LibraryView
from cozy.ui.main_view import CozyUI
from cozy.ui.search_view import SearchView
from cozy.ui.widgets.whats_new_window import WhatsNewWindow
from cozy.view_model.library_view_model import LibraryViewModel, LibraryViewMode
from cozy.view_model.search_view_model import SearchViewModel
from cozy.ui.settings import Settings as UISettings


class AppController(metaclass=Singleton):
    def __init__(self, main_window_builder, main_window):
        inject.configure_once(self.configure_inject)

        reporter.info("main", "startup")

        self.main_window: CozyUI = main_window
        self.main_window_builder = main_window_builder

        self.whats_new_window: WhatsNewWindow = WhatsNewWindow()

        self.library_view: LibraryView = LibraryView(main_window_builder)
        self.search_view: SearchView = SearchView(main_window_builder)

        self.library_view_model = inject.instance(LibraryViewModel)
        self.search_view_model = inject.instance(SearchViewModel)

        self.search_view_model.add_listener(self._on_open_view)
        self.library_view_model.add_listener(self._on_library_view_event)

    @staticmethod
    def configure_inject(binder):
        binder.bind_to_provider(SqliteDatabase, get_db)
        binder.bind_to_constructor(Gio.Settings, lambda: Gio.Settings("com.github.geigi.cozy"))
        binder.bind_to_constructor(ApplicationSettings, lambda: ApplicationSettings())
        binder.bind_to_constructor(Settings, lambda: Settings())
        binder.bind_to_constructor("FilesystemMonitor", lambda: FilesystemMonitor())
        binder.bind_to_constructor(Library, lambda: Library())
        binder.bind_to_constructor(LibraryViewModel, lambda: LibraryViewModel())
        binder.bind_to_constructor(SearchViewModel, lambda: SearchViewModel())
        binder.bind_to_constructor(UISettings, lambda: UISettings())
        binder.bind_to_constructor(StorageBlockList, lambda: StorageBlockList())
        binder.bind_to_constructor(Files, lambda: Files())

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

    def _on_library_view_event(self, event: str, data):
        if event == "work-done":
            self.main_window.switch_to_playing()
