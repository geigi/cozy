import logging
import os
from enum import Enum, auto
from multiprocessing import Pool, set_start_method
from typing import List

from cozy.architecture.profiler import timing
from cozy.media.media_detector import MediaDetector, NotAnAudioFile
from cozy.report import reporter
from cozy.architecture.event_sender import EventSender
from cozy.control.filesystem_monitor import FilesystemMonitor, StorageNotFound
from cozy.ext import inject
from cozy.model.settings import Settings


log = logging.getLogger("importer")

class ScanStatus(Enum):
    STARTED = auto()
    SUCCESS = auto()
    ABORTED = auto()
    FINISHED_WITH_ERRORS = auto()


class Importer(EventSender):
    _fs_monitor: FilesystemMonitor = inject.attr("FilesystemMonitor")
    _settings = inject.attr(Settings)

    @timing
    def scan(self):
        logging.info("Starting import")
        self.emit_event("scan", ScanStatus.STARTED)

        paths_to_scan = self._get_paths_to_scan()

        paths = []
        for path in paths_to_scan:
            for directory, subdirectories, files in os.walk(path):
                for file in files:
                    paths.append(os.path.join(directory, file))

        set_start_method("spawn")
        with Pool() as pool:
            pool.map(self.import_file, paths)

        logging.info("Import finished")

    def _get_paths_to_scan(self) -> List[str]:
        paths = [storage.path
                 for storage
                 in self._settings.storage_locations
                 if not storage.external]

        for storage in self._settings.external_storage_locations:
            try:
                if self._fs_monitor.is_storage_online(storage):
                    paths.append(storage.path)
            except StorageNotFound:
                paths.append(storage.path)

        return [path for path in paths if os.path.exists(path)]

    def _get_file_count_in_dir(self, dir):
        len([name for name in os.listdir(dir) if os.path.isfile(name)])

    def import_file(self, path: str) -> bool:
        if not os.path.isfile(path):
            return False

        media_detector = MediaDetector(path)
        try:
            media_data = media_detector.get_media_data()
        except NotAnAudioFile as e:
            reporter.exception("importer", e)
