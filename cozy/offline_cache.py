import logging
import time
import uuid
import os

from cozy.event_sender import EventSender
from cozy.singleton import Singleton
import cozy.db
import cozy.tools as tools
import cozy.ui

from gi.repository import Gio, Gdk, GLib

log = logging.getLogger("offline_cache")

class OfflineCache(EventSender, metaclass=Singleton):
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
        self.ui = cozy.ui.CozyUI()

        self.cache_dir = os.path.join(tools.get_cache_dir(), "offline")
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        self._start_processing()

        cozy.settings.Settings().add_listener(self.__on_settings_changed)

    def add(self, book):
        """
        Add all tracks of a book to the offline cache and start copying.
        """
        tracks = []
        for track in cozy.db.tracks(book):
            file = str(uuid.uuid4())
            tracks.append((track, file))
        chunks = [tracks[x:x+500] for x in range(0, len(tracks), 500)]
        for chunk in chunks:
            query = cozy.db.OfflineCache.insert_many(chunk, fields=[cozy.db.OfflineCache.track, cozy.db.OfflineCache.file])
            self.total_batch_count += len(chunk)
            query.execute()
            
        self._start_processing()

    def remove(self, book):
        """
        Remove all tracks of the given book from the cache.
        """
        #self._stop_processing()
        tracks = cozy.db.tracks(book)
        ids = [t.id for t in tracks]
        offline_elements = cozy.db.OfflineCache.select().where(cozy.db.OfflineCache.track << ids)

        for element in offline_elements:
            file_path = os.path.join(self.cache_dir, element.file)
            if file_path == self.cache_dir:
                continue

            file = Gio.File.new_for_path(file_path)
            if file.query_exists():
                file.delete()

            for item in self.queue:
                if self.current and item.id == self.current.id:
                    self.filecopy_cancel.cancel()

        cozy.db.OfflineCache.delete().where(cozy.db.OfflineCache.track in ids).execute()

        if len(self.queue) > 0:
            self._start_processing()
    
    def remove_all_for_storage(self, storage_path):
        """
        """
        for element in cozy.db.OfflineCache.select().join(cozy.db.Track).where(storage_path in cozy.db.Track.file):
            file_path = os.path.join(self.cache_dir, element.file)
            if file_path == self.cache_dir:
                continue
            
            file = Gio.File.new_for_path(file_path)
            if file.query_exists():
                file.delete()
            
            if element.track.book.offline == True:
                element.track.book.update(offline=False, downloaded=False).execute()
            
        cozy.db.OfflineCache.delete().where(storage_path in cozy.db.OfflineCache.track.file).execute()

    
    def get_cached_path(self, track):
        """
        """
        query = cozy.db.OfflineCache.select().where(cozy.db.OfflineCache.track == track.id, cozy.db.OfflineCache.copied == True)
        if query.count() > 0:
            return os.path.join(self.cache_dir, query.get().file)
        else:
            return None

    def update_cache(self, paths):
        """
        Update the cached version of the given files.
        """
        if cozy.db.OfflineCache.select().count() > 0:
            cozy.db.OfflineCache.update(copied=False).where(cozy.db.OfflineCache.track.file in paths).execute()
            #tracks = cozy.db.OfflineCache.select(cozy.db.Track, cozy.db.OfflineCache).join(cozy.db.Track).where(cozy.db.Track.file in paths)
            self._fill_queue_from_db()

    def delete_cache(self):
        """
        Deletes the entire offline cache files.
        Doesn't delete anything from the cozy.db.
        """
        cache_dir = os.path.join(tools.get_cache_dir(), "offline")

        import shutil
        shutil.rmtree(cache_dir)


    def _stop_processing(self):
        """
        """
        if not self._is_processing() or not self.thread:
            return

        self.thread.stop()
        self.filecopy_cancel.cancel()
    
    def _start_processing(self):
        """
        """
        if self._is_processing():
            return

        self.thread = tools.StoppableThread(target=self._process_queue)
        self.thread.start()
    
    def _process_queue(self):
        log.info("Startet processing queue")
        self.filecopy_cancel = Gio.Cancellable()
        
        self._fill_queue_from_db()
        self.total_batch_count = len(self.queue)
        self.current_batch_count = 0
        if len(self.queue) > 0:
            self.current_book_processing = self.queue[0].track.book.id

        while len(self.queue) > 0:
            log.info("Processing item")
            self.current_batch_count += 1
            item = self.queue[0]
            if self.thread.stopped():
                break
            
            new_item = cozy.db.OfflineCache.get(cozy.db.OfflineCache.id == item.id)

            if self.current_book_processing != new_item.track.book.id:
                self.update_book_download_status(cozy.db.Book.get(cozy.db.Book.id == self.current_book_processing))
                self.current_book_processing = new_item.track.book.id

            if not new_item.copied and os.path.exists(new_item.track.file):
                log.info("Copying item")
                Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, self.ui.switch_to_working, _("Copying") + " " + tools.shorten_string(new_item.track.book.name, 30), False, False)
                self.current = new_item
                
                destination = Gio.File.new_for_path(os.path.join(self.cache_dir, new_item.file))
                source = Gio.File.new_for_path(new_item.track.file)
                flags = Gio.FileCopyFlags.OVERWRITE
                try:
                    copied = source.copy(destination, flags, self.filecopy_cancel, self.__update_copy_status, None)
                except Exception as e:
                    if e.code == Gio.IOErrorEnum.CANCELLED:
                        log.info("Download of book was cancelled.")
                        self.thread.stop()
                        break
                    log.error("Could not copy file to offline cache: " + new_item.track.file)
                    log.error(e)
                    self.queue.remove(item)
                    continue

                if copied:
                    cozy.db.OfflineCache.update(copied=True).where(cozy.db.OfflineCache.id == new_item.id).execute()
                
            self.queue.remove(item)

        if self.current_book_processing:
            self.update_book_download_status(cozy.db.Book.get(cozy.db.Book.id == self.current_book_processing))

        self.current = None
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, self.ui.switch_to_playing)

    def update_book_download_status(self, book):
        """
        Updates the downloaded status of a book.
        """
        downloaded = True
        tracks = cozy.db.tracks(book)
        offline_tracks = cozy.db.OfflineCache.select().where(cozy.db.OfflineCache.track in tracks)

        if offline_tracks.count() < 1:
            downloaded = False
        else:
            for track in offline_tracks:
                if not track.copied:
                    downloaded = False
        
        cozy.db.Book.update(downloaded=downloaded).where(cozy.db.Book.id == book.id).execute()
        if downloaded:
            self.emit_event("book-offline", book)
        else:
            self.emit_event("book-offline-removed", book)


    def _is_processing(self):
        """
        """
        if self.thread:
            return self.thread.is_alive()
        else:
            return False

    def _fill_queue_from_db(self):
        for item in cozy.db.OfflineCache.select().where(cozy.db.OfflineCache.copied == False):
            if not any(item.id == queued.id for queued in self.queue):
                self.queue.append(item)
                self.total_batch_count += 1

    def __update_copy_status(self, current_num_bytes, total_num_bytes, user_data):
        progress =  ((self.current_batch_count - 1) / self.total_batch_count) + ((current_num_bytes / total_num_bytes) / self.total_batch_count)
        Gdk.threads_add_idle(GLib.PRIORITY_HIGH_IDLE ,
                             self.ui.titlebar.update_progress_bar.set_fraction, progress)

    def _fill_queue_from_db(self):
        for item in cozy.db.OfflineCache.select().where(cozy.db.OfflineCache.copied == False):
            if not any(item.id == queued.id for queued in self.queue):
                self.queue.append(item)
                self.total_batch_count += 1

    def __update_copy_status(self, current_num_bytes, total_num_bytes, user_data):
        progress =  ((self.current_batch_count - 1) / self.total_batch_count) + ((current_num_bytes / total_num_bytes) / self.total_batch_count)
        Gdk.threads_add_idle(GLib.PRIORITY_HIGH_IDLE ,
                             self.ui.titlebar.update_progress_bar.set_fraction, progress)

    def __on_settings_changed(self, event, message):
        """
        This method reacts to storage settings changes.
        """
        if event == "storage-removed" or event == "external-storage-removed":
            self.remove_all_for_storage(message)
