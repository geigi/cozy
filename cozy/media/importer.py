import itertools
import logging
import os
import time
from enum import Enum, auto
from multiprocessing.pool import Pool as Pool
from typing import List, Set
from urllib.parse import urlparse, unquote

from cozy.architecture.event_sender import EventSender
from cozy.architecture.profiler import timing
from cozy.control.filesystem_monitor import FilesystemMonitor, StorageNotFound
from cozy.ext import inject
from cozy.media.media_detector import MediaDetector, NotAnAudioFile, AudioFileCouldNotBeDiscovered
from cozy.media.media_file import MediaFile
from cozy.model.database_importer import DatabaseImporter
from cozy.model.library import Library
from cozy.model.settings import Settings
from cozy.report import reporter

log = logging.getLogger("importer")

CHUNK_SIZE = 100


class ScanStatus(Enum):
    STARTED = auto()
    SUCCESS = auto()
    ABORTED = auto()
    FINISHED_WITH_ERRORS = auto()


def import_file(path: str):
    if not os.path.isfile(path):
        return None

    try:
        media_detector = MediaDetector(path)
        media_data = media_detector.get_media_data()
    except NotAnAudioFile as e:
        return None
    except AudioFileCouldNotBeDiscovered as e:
        return unquote(urlparse(str(e)).path)
    except Exception as e:
        log.error(e)
        reporter.exception("media_detector", e)
        return None

    return media_data


class Importer(EventSender):
    _fs_monitor: FilesystemMonitor = inject.attr("FilesystemMonitor")
    _settings = inject.attr(Settings)
    _library = inject.attr(Library)
    _database_importer = inject.attr(DatabaseImporter)

    def __init__(self):
        super().__init__()

        self._files_count: int = 0
        self._progress: int = 0

    @timing
    def scan(self):
        logging.info("Starting import")
        self.emit_event_main_thread("scan", ScanStatus.STARTED)

        files_to_scan = self._get_files_to_scan()

        self.emit_event_main_thread("scan-progress", 0.025)
        new_or_changed_files, undetected_files = self._execute_import(files_to_scan)
        self._library.invalidate()

        self.emit_event_main_thread("scan-progress", 1)

        logging.info("Import finished")
        self.emit_event_main_thread("scan", ScanStatus.SUCCESS)
        self.emit_event_main_thread("new-or-updated-files", new_or_changed_files)

        if len(undetected_files) > 0:
            logging.info("Some files could not be imported:")
            logging.info(undetected_files)
            self.emit_event_main_thread("import-failed", undetected_files)

    def _execute_import(self, files_to_scan: List[str]) -> (Set[str], Set[str]):
        new_or_changed_files = set()
        undetected_files = set()

        self._files_count = self._count_files_to_scan()
        self.emit_event_main_thread("scan-progress", 0.05)
        self._progress = 0

        pool = Pool()
        while True:
            try:
                job = pool.map_async(import_file, itertools.islice(files_to_scan, CHUNK_SIZE))
            except StopIteration as e:
                log.warning("importer", e, "_execute_import raised a stop iteration.")
                break

            self._wait_for_job_to_complete(job)
            import_result = job.get()

            undetected_files.update({file for file in import_result if isinstance(file, str)})
            media_files = {file for file in import_result if isinstance(file, MediaFile)}
            new_or_changed_files.update((file.path for file in media_files))

            self._progress += CHUNK_SIZE

            if len(media_files) != 0:
                self._database_importer.insert_many(media_files)
            if self._progress >= self._files_count:
                break
        pool.close()

        return new_or_changed_files, undetected_files

    def _wait_for_job_to_complete(self, job):
        while not job.ready():
            jobs_finished = max(0, CHUNK_SIZE - job._number_left * job._chunksize)
            progress = 0.05 + ((self._progress + jobs_finished) / self._files_count) * 0.9
            self.emit_event_main_thread("scan-progress", progress)
            time.sleep(0.1)

    @timing
    def _count_files_to_scan(self) -> int:
        files_to_scan = self._get_files_to_scan()

        try:
            return max(1, len(list(files_to_scan)))
        except StopIteration as e:
            reporter.exception("importer", e, "_count_files_to_scan raised a stop iteration.")
            return 1

    def _get_files_to_scan(self) -> List[str]:
        paths_to_scan = self._get_configured_storage_paths()
        files_in_media_folders = self._walk_paths_to_scan(paths_to_scan)
        files_to_scan = self._filter_unchanged_files(files_in_media_folders)

        return files_to_scan

    def _get_configured_storage_paths(self) -> List[str]:
        """From all storage path configured by the user,
        we only want to scan those paths that are currently online and exist."""
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

    def _walk_paths_to_scan(self, paths: List[str]) -> List[str]:
        """Get all files recursive inside a directory. Returns absolute paths."""
        for path in paths:
            for directory, subdirectories, files in os.walk(path):
                for file in files:
                    filepath = os.path.join(directory, file)
                    yield filepath

    def _filter_unchanged_files(self, files: List[str]) -> List[str]:
        """Filter all files that are already imported and that have not changed from a list of paths."""
        imported_files = self._library.files

        for file in files:
            if file in imported_files:
                chapter = next(chapter
                               for chapter
                               in self._library.chapters
                               if chapter.file == file)

                if int(os.path.getmtime(file)) > chapter.modified:
                    yield file

                continue

            yield file

    def _get_file_count_in_dir(self, dir):
        len([name for name in os.listdir(dir) if os.path.isfile(name)])
