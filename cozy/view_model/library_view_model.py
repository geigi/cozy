import logging
import os
from enum import Enum, auto
from typing import Optional

import inject

from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.control.filesystem_monitor import FilesystemMonitor
from cozy.enums import OpenView
from cozy.extensions.set import split_strings_to_set
from cozy.media.importer import Importer, ScanStatus
from cozy.media.player import Player
from cozy.model.book import Book
from cozy.model.library import Library
from cozy.report import reporter
from cozy.settings import ApplicationSettings
from cozy.ui.import_failed_dialog import ImportFailedDialog
from cozy.ui.widgets.book_card import BookCard
from cozy.view_model.storages_view_model import StoragesViewModel

log = logging.getLogger("library_view_model")


class LibraryViewMode(Enum):
    CURRENT = auto()
    AUTHOR = auto()
    READER = auto()


class LibraryViewModel(Observable, EventSender):
    _application_settings: ApplicationSettings = inject.attr(ApplicationSettings)
    _fs_monitor: FilesystemMonitor = inject.attr("FilesystemMonitor")
    _model = inject.attr(Library)
    _importer: Importer = inject.attr(Importer)
    _player: Player = inject.attr(Player)
    _storages: StoragesViewModel = inject.attr(StoragesViewModel)

    def __init__(self):
        super().__init__()
        super(Observable, self).__init__()

        self._library_view_mode: LibraryViewMode = LibraryViewMode.CURRENT
        self._selected_filter: str = _("All")

        self._connect()

    def _connect(self):
        self._fs_monitor.add_listener(self._on_fs_monitor_event)
        self._application_settings.add_listener(self._on_application_setting_changed)
        self._importer.add_listener(self._on_importer_event)
        self._player.add_listener(self._on_player_event)
        self._model.add_listener(self._on_model_event)
        self._storages.add_listener(self._on_storages_event)

    @property
    def books(self):
        return self._model.books

    @property
    def library_view_mode(self):
        return self._library_view_mode

    @library_view_mode.setter
    def library_view_mode(self, value):
        self._library_view_mode = value
        self._notify("library_view_mode")
        self.emit_event(OpenView.LIBRARY, None)

    @property
    def selected_filter(self):
        return self._selected_filter

    @selected_filter.setter
    def selected_filter(self, value):
        self._selected_filter = value
        self._notify("selected_filter")

    @property
    def is_any_book_recent(self) -> bool:
        return any(book.last_played > 0 for book in self.books)

    @property
    def authors(self):
        is_book_online = self._fs_monitor.get_book_online
        show_offline_books = not self._application_settings.hide_offline

        authors = {
            book.author
            for book in self._model.books
            if is_book_online(book) or show_offline_books or book.downloaded
        }

        return sorted(split_strings_to_set(authors))

    @property
    def readers(self):
        is_book_online = self._fs_monitor.get_book_online
        show_offline_books = not self._application_settings.hide_offline

        readers = {
            book.reader
            for book in self._model.books
            if is_book_online(book) or show_offline_books or book.downloaded
        }

        return sorted(split_strings_to_set(readers))

    @property
    def current_book_in_playback(self) -> Optional[Book]:
        return self._player.loaded_book

    @property
    def playing(self) -> bool:
        return self._player.playing

    def remove_book(self, book: Book):
        book.remove()
        self._model.invalidate()
        self._notify("authors")
        self._notify("readers")
        self._notify("books")
        self._notify("books-filter")

    def display_book_filter(self, book_element: BookCard):
        book = book_element.book

        hide_offline_books = self._application_settings.hide_offline
        book_is_online = self._fs_monitor.get_book_online(book)


        if hide_offline_books and not book_is_online and not book.downloaded:
            return False

        if self.library_view_mode == LibraryViewMode.CURRENT:
            return book.last_played > 0

        if self.selected_filter == _("All"):
            return True
        elif self.library_view_mode == LibraryViewMode.AUTHOR:
            return self.selected_filter in book.author
        elif self.library_view_mode == LibraryViewMode.READER:
            return self.selected_filter in book.reader

    def display_book_sort(self, book_element1, book_element2):
        if self._library_view_mode == LibraryViewMode.CURRENT:
            return book_element1.book.last_played < book_element2.book.last_played
        else:
            return book_element1.book.name.lower() > book_element2.book.name.lower()

    def open_library(self):
        self._notify("library_view_mode")

    def book_files_exist(self, book: Book) -> bool:
        return any(os.path.isfile(chapter.file) for chapter in book.chapters)

    def _on_fs_monitor_event(self, event, _):
        if event in {"storage-online", "storage-offline"}:
            self._notify("authors")
            self._notify("readers")
            self._notify("books-filter")

    def _on_application_setting_changed(self, event, _):
        if event == "hide-offline":
            self._notify("authors")
            self._notify("readers")
            self._notify("books-filter")
        elif event == "swap-author-reader":
            self._notify("authors")
            self._notify("readers")
            self._notify("books")
            self._notify("books-filter")
        elif event == "prefer-external-cover":
            self._notify("books")

    def _on_importer_event(self, event, message):
        if event == "scan" and message == ScanStatus.SUCCESS:
            self._notify("authors")
            self._notify("readers")
            self._notify("books")
            self._notify("books-filter")
            self._notify("library_view_mode")
        elif event == "import-failed":
            ImportFailedDialog(message).show()

    def _on_player_event(self, event, message):
        if event == "play" and message:
            self._notify("current_book_in_playback")
            self._notify("playing")
            self._notify("books-filter")
        elif event == "pause":
            self._notify("playing")
        elif event == "chapter-changed":
            self._notify("current_book_in_playback")
            self._notify("playing")
        elif event == "stop":
            self._notify("playing")
            self._notify("current_book_in_playback")
        elif event in {"position", "book-finished"}:
            self._notify("book-progress")

    def _on_storages_event(self, event: str, message):
        if event == "storage-removed":
            for property in (
                "authors",
                "readers",
                "books",
                "books-filter",
                "current_book_in_playback",
                "playing",
            ):
                self._notify(property)

    def _on_model_event(self, event: str, message):
        if event == "rebase-finished":
            self.emit_event("work-done")

    def open_book_detail(self, book: Book):
        self.emit_event(OpenView.BOOK, book)

    def delete_book_files(self, book: Book):
        for chapter in book.chapters:
            try:
                os.remove(chapter.file)
            except Exception as e:
                log.error("Failed to delete file: %s", chapter.file)
                log.debug(e)
                reporter.warning("library_view_model", "Failed to delete a file.")
            else:
                log.info("Deleted file: %s", chapter.file)

    def play_book(self, book: Book):
        self._player.play_pause_book(book)
