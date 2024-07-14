import logging
import os
from pathlib import Path

import inject
from gi.repository import Gio

from cozy.architecture.event_sender import EventSender
from cozy.media.importer import Importer
from cozy.model.settings import Settings
from cozy.report import reporter
from cozy.ui.toaster import ToastNotifier

log = logging.getLogger("files")


class Files(EventSender):
    _settings = inject.attr(Settings)
    _importer = inject.attr(Importer)
    _toast: ToastNotifier = inject.attr(ToastNotifier)

    _file_count = 0
    _file_progess = 0

    def __init__(self):
        super().__init__()

    def copy(self, selection):
        log.info("Start of copying files")
        self.emit_event_main_thread("start-copy", None)

        paths = [f.get_path() for f in selection]
        storage_location = self._settings.default_location.path

        self._file_count = 0
        self._file_progess = 0

        self._count_all_files(paths)
        self._copy_all(paths, storage_location)

        log.info("Copying of files finished")
        self._importer.scan()

    def _copy_all(self, sources, destination: str):
        for path in sources:
            if os.path.isdir(path):
                self._copy_directory(path, destination)
            else:
                filename = os.path.basename(path)
                file_copy_destination = os.path.join(destination, filename)
                self._copy_file(path, file_copy_destination)

    def _copy_file(self, source_path: str, dest_path: str):
        log.info("Copy file %s to %s", source_path, dest_path)

        source = Gio.File.new_for_path(source_path)
        destination = Gio.File.new_for_path(dest_path)
        flags = Gio.FileCopyFlags.OVERWRITE
        self.filecopy_cancel = Gio.Cancellable()
        try:
            source.copy(destination, flags, self.filecopy_cancel, self._update_copy_status, None)
        except Exception as e:
            if e.code == Gio.IOErrorEnum.CANCELLED:
                pass
            elif e.code == Gio.IOErrorEnum.READ_ONLY:
                self._toast.show(_("Cannot copy: Audiobook directory is read only"))
            elif e.code == Gio.IOErrorEnum.NO_SPACE:
                self._toast.show(_("Cannot copy: Disk is full"))
            elif e.code == Gio.IOErrorEnum.PERMISSION_DENIED:
                self._toast.show(_("Cannot copy: Permission denied"))
            else:
                reporter.exception("files", e)

            log.error("Failed to copy file: %s", e)
        self._file_progess += 1

    def _copy_directory(self, path, destination):
        main_source_path = os.path.split(path)[0]
        for dirpath, _, filenames in os.walk(path):
            dirname = os.path.relpath(dirpath, main_source_path)
            destination_dir = os.path.join(destination, dirname)
            try:
                Path(destination_dir).mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                log.error(e)
                self._toast.show(_("Cannot copy: Permission denied"))
                return

            for file in filenames:
                source = os.path.join(dirpath, file)
                file_copy_destination = os.path.join(destination, dirname, file)
                self._copy_file(source, file_copy_destination)

    def _count_all_files(self, paths: list[str]) -> None:
        for path in paths:
            if os.path.isdir(path):
                self._file_count += self._count_files_in_folder(path)
            else:
                self._file_count += 1

    def _update_copy_status(self, current_num_bytes, total_num_bytes, _):
        if total_num_bytes == 0:
            total_num_bytes = 1

        if self._file_count == 0:
            progress = 1.0
        else:
            progress = (self._file_progess / self._file_count) + (
                    (current_num_bytes / total_num_bytes) / self._file_count)
        self.emit_event_main_thread("copy-progress", progress)

    def _count_files_in_folder(self, path: str) -> int:
        return sum([len(files) for r, d, files in os.walk(path)])
