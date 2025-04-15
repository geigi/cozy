import itertools
import logging
import os
import time
from enum import Enum, auto
from multiprocessing.pool import Pool as Pool
from pathlib import Path
from urllib.parse import unquote, urlparse

import inject

from cozy.architecture.event_sender import EventSender
from cozy.architecture.profiler import timing
from cozy.control.filesystem_monitor import FilesystemMonitor, StorageNotFound
from cozy.media.media_detector import AudioFileCouldNotBeDiscovered, MediaDetector, NotAnAudioFile
from cozy.media.media_file import MediaFile
from cozy.model.database_importer import DatabaseImporter
from cozy.model.library import Library
from cozy.model.settings import Settings
from cozy.report import reporter
from cozy.ui.toaster import ToastNotifier

log = logging.getLogger("importer")

CHUNK_SIZE = 100

AUDIO_EXTENSIONS = {".mp3", ".ogg", ".flac", ".m4a", ".m4b", ".mp4", ".wav", ".opus"}


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
    except NotAnAudioFile:
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
    _toast: ToastNotifier = inject.attr(ToastNotifier)

    def __init__(self):
        super().__init__()

        self._files_count: int = 0
        self._progress: int = 0

    @timing
    def scan(self):
        log.info("Starting import")
        self.emit_event_main_thread("scan", ScanStatus.STARTED)

        files_to_scan = self._get_files_to_scan()

        self.emit_event_main_thread("scan-progress", 0.025)
        new_or_changed_files, undetected_files = self._execute_import(files_to_scan)
        self._library.invalidate()

        self.emit_event_main_thread("scan-progress", 1)

        log.info("Import finished")
        self.emit_event_main_thread("scan", ScanStatus.SUCCESS)
        self.emit_event_main_thread("new-or-updated-files", new_or_changed_files)

        if len(undetected_files) > 0:
            log.info("Some files could not be imported:")
            log.info(undetected_files)
            self.emit_event_main_thread("import-failed", undetected_files)

    def _execute_import(self, files_to_scan: list[str]) -> tuple[set[str], set[str]]:
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
            new_or_changed_files.update(file.path for file in media_files)

            self._progress += CHUNK_SIZE

            if media_files:
                try:
                    self._database_importer.insert_many(media_files)
                except Exception as e:
                    log.exception("Error while inserting new tracks to the database")
                    reporter.exception("importer", e)
                    self._toast.show(
                        "{}: {}".format(_("Error while importing new files"), str(e.__class__))
                    )

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

    def _get_files_to_scan(self) -> list[str]:
        paths_to_scan = self._get_configured_storage_paths()
        files_in_media_folders = self._walk_paths_to_scan(paths_to_scan)
        files_to_scan = self._filter_unchanged_files(files_in_media_folders)

        return files_to_scan

    def _get_configured_storage_paths(self) -> list[str]:
        """From all storage path configured by the user,
        we only want to scan those paths that are currently online and exist."""
        paths = [
            storage.path for storage in self._settings.storage_locations if not storage.external
        ]

        for storage in self._settings.external_storage_locations:
            try:
                if self._fs_monitor.is_storage_online(storage):
                    paths.append(storage.path)
            except StorageNotFound:
                paths.append(storage.path)

        return [path for path in paths if os.path.exists(path)]

    def _walk_paths_to_scan(self, directories: list[str]) -> list[str]:
        """Get all files recursive inside a directory. Returns absolute paths."""
        for dir in directories:
            for path in Path(dir).rglob("**/*"):
                if path.suffix.lower() in AUDIO_EXTENSIONS:
                    yield str(path)

    def _filter_unchanged_files(self, files: list[str]) -> list[str]:
        """Filter all files that are already imported and that have not changed from a list of paths."""
        imported_files = self._library.files

        for file in files:
            if file in imported_files:
                try:
                    chapter = next(
                        chapter for chapter in self._library.chapters if chapter.file == file
                    )
                except StopIteration as e:
                    log.warning("_filter_unchanged_files raised a stop iteration.")
                    log.debug(e)
                    yield file
                    continue

                try:
                    mtime = os.path.getmtime(file)
                    if mtime > chapter.modified:
                        yield file
                except Exception as e:
                    log.debug(e)
                    log.info("Could not get modified timestamp for file %s", file)
                    continue

                continue

            yield file
