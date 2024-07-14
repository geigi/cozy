import logging
from threading import Thread

from peewee import SqliteDatabase

from cozy.application_settings import ApplicationSettings
from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.control.filesystem_monitor import FilesystemMonitor
from cozy.ext import inject
from cozy.media.importer import Importer
from cozy.model.library import Library
from cozy.model.settings import Settings
from cozy.model.storage import Storage

log = logging.getLogger("storages_view_model")


class StoragesViewModel(Observable, EventSender):
    _library: Library = inject.attr(Library)
    _importer: Importer = inject.attr(Importer)
    _model: Settings = inject.attr(Settings)
    _app_settings: ApplicationSettings = inject.attr(ApplicationSettings)
    _db = inject.attr(SqliteDatabase)
    _fs_monitor = inject.attr(FilesystemMonitor)

    def __init__(self) -> None:
        super().__init__()
        super(Observable, self).__init__()

        self._selected_storage = None

    def _scan_new_storage(self, model: Storage) -> None:
        self.emit_event("storage-added", model)
        log.info("New audiobook location added. Starting import scan.")
        Thread(target=self._importer.scan, name="ImportThread").start()

    def _rebase_storage_location(self, model: Storage, old_path: str) -> None:
        self.emit_event("storage-changed", model)
        log.info("Audiobook location changed, rebasing the location in Cozy.")
        Thread(
            target=self._library.rebase_path,
            args=(old_path, model.path),
            name="RebaseStorageLocationThread",
        ).start()

    def add_storage_location(self, path: str | None) -> None:
        if path is None:
            return

        model = Storage.new(self._db, path)
        model.external = self._fs_monitor.is_external(path)

        self._model.invalidate()
        self._notify("storage_locations")

        self._scan_new_storage(model)

    def add_first_storage_location(self, path: str) -> None:
        storage = self.storages[0]
        storage.path = path
        storage.external = self._fs_monitor.is_external(path)
        assert storage.default

        self._model.invalidate()
        self._notify("storage_locations")

    def change_storage_location(self, model: Storage, new_path: str) -> None:
        old_path = model.path
        model.path = new_path
        model.external = self._fs_monitor.is_external(new_path)

        self._rebase_storage_location(model, old_path)
        self._notify("storage_attributes")

    @property
    def storages(self) -> list[Storage]:
        return self._model.storage_locations

    @property
    def default(self) -> Storage | None:
        for item in self.storages:
            if item.default:
                return item

    @property
    def selected_storage(self) -> Storage | None:
        return self._selected_storage

    @selected_storage.setter
    def selected_storage(self, value) -> None:
        self._selected_storage = value

    def remove(self, model: Storage) -> None:
        if model.default:
            return

        storage_path = model.path
        chapters_to_remove = []

        for book in self._library.books:
            chapters_to_remove.extend([c for c in book.chapters if c.file.startswith(storage_path)])

        for chapter in set(chapters_to_remove):
            chapter.delete()

        model.delete()
        self._model.invalidate()

        self.emit_event("storage-removed", model)
        self._notify("storage_locations")

    def set_default(self, model: Storage) -> None:
        if model.default:
            return

        for storage in self.storages:
            storage.default = False

        model.default = True

        self._notify("storage_attributes")

    def set_external(self, model: Storage, external: bool) -> None:
        model.external = external

        if external:
            self.emit_event("external-storage-added", model)
        else:
            self.emit_event("external-storage-removed", model)

        self._notify("storage_attributes")
