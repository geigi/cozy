import logging
import uuid
import os


from cozy.architecture.event_sender import EventSender
from cozy.control.application_directories import get_cache_dir
import cozy.tools as tools

from gi.repository import Gio

from cozy.db.file import File
from cozy.db.offline_cache import OfflineCache as OfflineCacheModel
from cozy.db.track_to_file import TrackToFile
from cozy.ext import inject
from cozy.model.book import Book
from cozy.model.chapter import Chapter
from cozy.report import reporter
from cozy.view_model.settings_view_model import SettingsViewModel

log = logging.getLogger("offline_cache")


class OfflineCache(EventSender):
    """
    This class is responsible for all actions on the offline cache.
    This includes operations like copying to the cache and adding or removing files from
    the cache.
    """
    queue = []
    total_batch_count = 0
    current_batch_count = 0
    current = None
    thread = None
    filecopy_cancel = None
    last_ui_update = 0
    current_book_processing = None

    def __init__(self):
        super().__init__()

        from cozy.media.importer import Importer
        self._importer = inject.instance(Importer)

        from cozy.model.library import Library
        self._library = inject.instance(Library)

        self._importer.add_listener(self._on_importer_event)

        self.cache_dir = os.path.join(get_cache_dir(), "offline")
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        self._start_processing()

        inject.instance(SettingsViewModel).add_listener(self.__on_settings_changed)

    def add(self, book: Book):
        """
        Add all tracks of a book to the offline cache and start copying.
        """
        files_to_cache = []
        file_ids = {chapter.file_id for chapter in book.chapters}
        for file_id in file_ids:
            cached_file_name = str(uuid.uuid4())
            files_to_cache.append((file_id, cached_file_name))
        chunks = [files_to_cache[x:x + 500] for x in range(0, len(files_to_cache), 500)]
        for chunk in chunks:
            query = OfflineCacheModel.insert_many(chunk, fields=[OfflineCacheModel.original_file,
                                                                 OfflineCacheModel.cached_file])
            self.total_batch_count += len(chunk)
            query.execute()

        self._start_processing()

    def remove(self, book: Book):
        """
        Remove all tracks of the given book from the cache.
        """
        self._stop_processing()
        ids = {t.file_id for t in book.chapters}
        offline_elements = OfflineCacheModel.select().join(File).where(OfflineCacheModel.original_file.id << ids)

        for element in offline_elements:
            file_path = os.path.join(self.cache_dir, element.cached_file)
            if file_path == self.cache_dir:
                continue

            file = Gio.File.new_for_path(file_path)
            if file.query_exists():
                file.delete()

            for item in self.queue:
                if self.current and item.id == self.current.id:
                    self.filecopy_cancel.cancel()

        entries_to_delete = OfflineCacheModel.select().join(File).where(OfflineCacheModel.original_file.id << ids)
        ids_to_delete = [t.id for t in entries_to_delete]
        OfflineCacheModel.delete().where(OfflineCacheModel.id << ids_to_delete).execute()
        book.downloaded = False
        self.emit_event("book-offline-removed", book)
        self.queue = []

        self._start_processing()

    def remove_all_for_storage(self, storage):
        for element in OfflineCacheModel.select().join(File).where(
                storage.path in OfflineCacheModel.original_file.path):
            file_path = os.path.join(self.cache_dir, element.cached_file)
            if file_path == self.cache_dir:
                continue

            file = Gio.File.new_for_path(file_path)
            if file.query_exists():
                file.delete()

        OfflineCacheModel.delete().where(storage.path in OfflineCacheModel.original_file.path).execute()

    def get_cached_path(self, chapter: Chapter):
        query = OfflineCacheModel.select().where(OfflineCacheModel.original_file == chapter.file_id,
                                                 OfflineCacheModel.copied == True)
        if query.count() > 0:
            return os.path.join(self.cache_dir, query.get().cached_file)
        else:
            return None

    def update_cache(self, paths):
        """
        Update the cached version of the given files.
        """
        if OfflineCacheModel.select().count() > 0:
            OfflineCacheModel.update(copied=False).where(
                OfflineCacheModel.original_file.path in paths).execute()
            self._fill_queue_from_db()

    def delete_cache(self):
        """
        Deletes the entire offline cache files.
        Doesn't delete anything from the cozy.db.
        """
        cache_dir = os.path.join(get_cache_dir(), "offline")

        import shutil
        shutil.rmtree(cache_dir)

    def _stop_processing(self):
        """
        """
        if not self._is_processing() or not self.thread:
            return

        self.filecopy_cancel.cancel()
        self.thread.stop()

    def _start_processing(self):
        """
        """
        if self._is_processing():
            return

        self.thread = tools.StoppableThread(target=self._process_queue)
        self.thread.start()

    def _process_queue(self):
        log.info("Started processing offline cache queue")
        self.filecopy_cancel = Gio.Cancellable()

        self._fill_queue_from_db()
        self.total_batch_count = len(self.queue)
        self.current_batch_count = 0
        if len(self.queue) > 0:
            self.current_book_processing = self._get_book_to_file(self.queue[0].original_file).id
            self.emit_event_main_thread("start")

        while len(self.queue) > 0:
            self.current_batch_count += 1
            item = self.queue[0]
            if self.thread.stopped():
                break

            log.info("Processing item: %r", item)

            query = OfflineCacheModel.select().where(OfflineCacheModel.id == item.id)
            if not query.exists():
                continue

            new_item = OfflineCacheModel.get(OfflineCacheModel.id == item.id)

            book = self._get_book_to_file(new_item.original_file)
            if self.current_book_processing != book.id:
                self._update_book_download_status(self.current_book_processing)
                self.current_book_processing = book.id

            if not new_item.copied and os.path.exists(new_item.original_file.path):
                log.info("Copying item: %r", new_item)
                self.emit_event_main_thread("message",
                                            _("Copying") + " " + tools.shorten_string(book.name, 30))
                self.current = new_item

                destination = Gio.File.new_for_path(os.path.join(self.cache_dir, new_item.cached_file))
                source = Gio.File.new_for_path(new_item.original_file.path)
                flags = Gio.FileCopyFlags.OVERWRITE
                try:
                    copied = source.copy(destination, flags, self.filecopy_cancel, self.__update_copy_status, None)
                except Exception as e:
                    if e.code == Gio.IOErrorEnum.CANCELLED:
                        log.info("Download of book was cancelled.")
                        self.thread.stop()
                        break
                    reporter.exception("offline_cache", e)
                    log.error("Could not copy file %r to offline cache: %s", new_item.original_file.path, e)
                    self.queue.remove(item)
                    continue

                if copied:
                    OfflineCacheModel.update(copied=True).where(
                        OfflineCacheModel.id == new_item.id).execute()

            self.queue.remove(item)

        if self.current_book_processing:
            self._update_book_download_status(self.current_book_processing)

        self.current = None
        self.emit_event_main_thread("finished")

    def _get_book_to_file(self, file: File):
        track_to_file = TrackToFile.select().join(File).where(TrackToFile.file == file.id).get()
        return track_to_file.track.book

    def _update_book_download_status(self, book_id):
        book = next(book for book in self._library.books if book.id == book_id)
        downloaded = self._is_book_downloaded(book)

        book.downloaded = downloaded

        if downloaded:
            self.emit_event("book-offline", book)
        else:
            self.emit_event("book-offline-removed", book)

    def _is_book_downloaded(self, book: Book):
        file_ids = [chapter.file_id for chapter in book.chapters]
        offline_files = OfflineCacheModel.select().where(OfflineCacheModel.original_file << file_ids)
        offline_file_ids = [file.original_file.id for file in offline_files]

        for chapter in book.chapters:
            if chapter.file_id not in offline_file_ids:
                return False

        return True

    def _is_processing(self):
        """
        """
        if self.thread:
            return self.thread.is_alive()
        else:
            return False

    def _fill_queue_from_db(self):
        for item in OfflineCacheModel.select().where(OfflineCacheModel.copied == False):
            if not any(item.id == queued.id for queued in self.queue):
                self.queue.append(item)
                self.total_batch_count += 1

    def _on_importer_event(self, event: str, message):
        if event == "new-or-updated-files":
            self.update_cache(message)
            self._start_processing()

    def __update_copy_status(self, current_num_bytes, total_num_bytes, _):
        total_batch_count = max(self.total_batch_count, 1)

        finished_files_progress = (self.current_batch_count - 1) / total_batch_count
        current_file_progress = current_num_bytes / max(total_num_bytes, 1)

        progress = finished_files_progress + (current_file_progress / total_batch_count)
        self.emit_event_main_thread("progress", min(progress, 1))

    def __on_settings_changed(self, event, message):
        if event == "storage-removed" or event == "external-storage-removed":
            self.remove_all_for_storage(message)
