import os
from enum import Enum, auto
from multiprocessing import Pool
from typing import List

from cozy.architecture.event_sender import EventSender
from cozy.control.filesystem_monitor import FilesystemMonitor, StorageNotFound
from cozy.ext import inject
from cozy.model.library import Library
from cozy.model.settings import Settings


class ScanStatus(Enum):
    STARTED = auto()
    SUCCESS = auto()
    ABORTED = auto()
    FINISHED_WITH_ERRORS = auto()


class Importer(EventSender):
    _fs_monitor = inject.attr(FilesystemMonitor)
    _settings = inject.attr(Settings)

    def scan(self):
        self.emit_event("scan", ScanStatus.STARTED)

        paths_to_scan = self._get_paths_to_scan()

        for path in paths_to_scan:
            with os.scandir(path) as it:
                with Pool as pool:
                    pool.map(self.import_file, it)

    def _get_paths_to_scan(self) -> List[str]:
        paths = [storage.path for storage in self._settings.storage_locations if not storage.external]

        for storage in self._settings.external_storage_locations:
            try:
                if self._fs_monitor.is_storage_online(storage):
                    paths.append(storage.path)
            except StorageNotFound:
                if os.path.exists(storage.path):
                    paths.append(storage.path)

        return paths

    def _get_file_count_in_dir(self, dir):
        len([name for name in os.listdir(dir) if os.path.isfile(name)])

    def import_file(self, path: os.DirEntry) -> bool:
        if not path.is_file():
            return False

        if not path.name.lower().endswith(('.mp3', '.ogg', '.flac', '.m4a', '.wav', '.opus')):
            return False
