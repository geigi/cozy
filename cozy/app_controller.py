import inject
from gi.repository import Gio
from peewee import SqliteDatabase

from cozy.application_settings import ApplicationSettings
from cozy.architecture.singleton import Singleton
from cozy.control.db import get_db
from cozy.control.filesystem_monitor import FilesystemMonitor
from cozy.control.offline_cache import OfflineCache
from cozy.media.files import Files
from cozy.media.player import GstPlayer, Player
from cozy.model.book import Book
from cozy.model.database_importer import DatabaseImporter
from cozy.model.library import Library
from cozy.model.settings import Settings
from cozy.open_view import OpenView
from cozy.power_manager import PowerManager
from cozy.report import reporter
from cozy.ui.app_view import AppView
from cozy.ui.headerbar import Headerbar
from cozy.ui.library_view import LibraryView
from cozy.ui.main_view import CozyUI
from cozy.ui.media_controller import MediaController
from cozy.ui.search_view import SearchView
from cozy.ui.toaster import ToastNotifier
from cozy.view import View
from cozy.view_model.app_view_model import AppViewModel
from cozy.view_model.book_detail_view_model import BookDetailViewModel
from cozy.view_model.headerbar_view_model import HeaderbarViewModel
from cozy.view_model.library_view_model import LibraryViewMode, LibraryViewModel
from cozy.view_model.playback_control_view_model import PlaybackControlViewModel
from cozy.view_model.playback_speed_view_model import PlaybackSpeedViewModel
from cozy.view_model.search_view_model import SearchViewModel
from cozy.view_model.settings_view_model import SettingsViewModel
from cozy.view_model.sleep_timer_view_model import SleepTimerViewModel
from cozy.view_model.storages_view_model import StoragesViewModel


class AppController(metaclass=Singleton):
    def __init__(self, gtk_app, main_window_builder, main_window):
        self.gtk_app = gtk_app
        self.main_window: CozyUI = main_window
        self.main_window_builder = main_window_builder

        inject.configure_once(self.configure_inject)

        reporter.info("main", "startup")

        self.library_view: LibraryView = LibraryView(main_window_builder)
        self.app_view: AppView = AppView(main_window_builder)
        self.headerbar: Headerbar = Headerbar(main_window_builder)
        self.media_controller: MediaController = MediaController(main_window_builder)
        self.search_view: SearchView = SearchView(main_window_builder, self.headerbar)

        self.library_view_model = inject.instance(LibraryViewModel)
        self.app_view_model = inject.instance(AppViewModel)
        self.search_view_model = inject.instance(SearchViewModel)
        self.book_detail_view_model = inject.instance(BookDetailViewModel)
        self.playback_control_view_model = inject.instance(PlaybackControlViewModel)
        self.sleep_timer_view_model = inject.instance(SleepTimerViewModel)
        self.headerbar_view_model = inject.instance(HeaderbarViewModel)
        self.settings_view_model = inject.instance(SettingsViewModel)
        self.player = inject.instance(Player)

        self._connect_search_button()

        self.search_view_model.add_listener(self._on_open_view)
        self.book_detail_view_model.add_listener(self._on_open_view)
        self.library_view_model.add_listener(self._on_open_view)
        self.library_view_model.add_listener(self._on_library_view_event)
        self.playback_control_view_model.add_listener(self._on_open_view)
        self.headerbar_view_model.add_listener(self._on_working_event)
        self.app_view_model.add_listener(self._on_app_view_event)

        self.main_window.add_listener(self._on_main_window_event)

        self.power_manager = inject.instance(PowerManager)

    def configure_inject(self, binder):
        binder.bind_to_provider(SqliteDatabase, get_db)
        binder.bind("MainWindow", self.main_window)
        binder.bind("GtkApp", self.gtk_app)
        binder.bind("MainWindowBuilder", self.main_window_builder)
        binder.bind_to_constructor(Gio.Settings, lambda: Gio.Settings("com.github.geigi.cozy"))
        binder.bind_to_constructor(ApplicationSettings, lambda: ApplicationSettings())
        binder.bind_to_constructor(Settings, lambda: Settings())
        binder.bind_to_constructor("FilesystemMonitor", lambda: FilesystemMonitor())
        binder.bind_to_constructor(OfflineCache, lambda: OfflineCache())
        binder.bind_to_constructor(Player, lambda: Player())
        binder.bind_to_constructor(Library, lambda: Library())
        binder.bind_to_constructor(DatabaseImporter, lambda: DatabaseImporter())
        binder.bind_to_constructor(LibraryViewModel, lambda: LibraryViewModel())
        binder.bind_to_constructor(SearchViewModel, lambda: SearchViewModel())
        binder.bind_to_constructor(Files, lambda: Files())
        binder.bind_to_constructor(BookDetailViewModel, lambda: BookDetailViewModel())
        binder.bind_to_constructor(PlaybackControlViewModel, lambda: PlaybackControlViewModel())
        binder.bind_to_constructor(HeaderbarViewModel, lambda: HeaderbarViewModel())
        binder.bind_to_constructor(PlaybackSpeedViewModel, lambda: PlaybackSpeedViewModel())
        binder.bind_to_constructor(SleepTimerViewModel, lambda: SleepTimerViewModel())
        binder.bind_to_constructor(GstPlayer, lambda: GstPlayer())
        binder.bind_to_constructor(PowerManager, lambda: PowerManager())
        binder.bind_to_constructor(ToastNotifier, lambda: ToastNotifier())
        binder.bind_to_constructor(AppViewModel, lambda: AppViewModel())
        binder.bind_to_constructor(SettingsViewModel, lambda: SettingsViewModel())
        binder.bind_to_constructor(StoragesViewModel, lambda: StoragesViewModel())

    def open_author(self, author: str):
        self.library_view_model.library_view_mode = LibraryViewMode.AUTHOR
        self.library_view_model.selected_filter = author

    def open_reader(self, reader: str):
        self.library_view_model.library_view_mode = LibraryViewMode.READER
        self.library_view_model.selected_filter = reader

    def open_book(self, book: Book):
        self.book_detail_view_model.book = book
        self.app_view_model.open_book_detail_view()

    def open_library(self):
        self.library_view_model.open_library()
        self.app_view_model.view = View.LIBRARY_FILTER

    def _connect_search_button(self):
        self.headerbar.search_button.connect(
            "notify::active",
            self.search_view.on_state_changed
        )

    def _on_open_view(self, event, data):
        if event == OpenView.AUTHOR:
            self.open_author(data)
        elif event == OpenView.READER:
            self.open_reader(data)
        elif event == OpenView.BOOK:
            self.open_book(data)
        elif event == OpenView.LIBRARY:
            self.open_library()

    def _on_library_view_event(self, event: str, _):
        if event == "work-done":
            self.main_window.switch_to_playing()

    def _on_app_view_event(self, event: str, data):
        if event == "view":
            self.headerbar_view_model.set_view(data)

    def _on_working_event(self, event: str, data) -> None:
        if event == "working":
            self.book_detail_view_model.lock_ui = data
            self.settings_view_model.lock_ui = data

    def _on_main_window_event(self, event: str, data):
        if event == "open_view":
            self._on_open_view(data, None)

    def quit(self):
        self.sleep_timer_view_model.destroy()
        self.player.destroy()
