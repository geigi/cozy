import logging
import uuid
import os

from cozy.singleton import Singleton
import cozy.db as db
import cozy.tools as tools
import cozy.ui

from gi.repository import Gio, Gdk, GLib

log = logging.getLogger("offline_cache")

class OfflineCache(metaclass=Singleton):
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

    def __init__(self):
        self.ui = cozy.ui.CozyUI()

        self.cache_dir = os.path.join(tools.get_cache_dir(), "offline")
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        self._start_processing()

    def add(self, book):
        """
        Add all tracks of a book to the offline cache and start copying.
        """
        for track in db.tracks(book):
            file = str(uuid.uuid4())
            db_track = db.OfflineCache.create(track=track, file=file)
            self.queue.append(db_track)
            self.total_batch_count += 1

        self._start_processing()

    def remove(self, book):
        """
        Remove all tracks of the given book from the cache.
        """
        #self._stop_processing()

        for track in db.tracks(book):
            q = db.OfflineCache.select().where(db.OfflineCache.track == track.id)
            if q.count() > 0:
                cache = q.get()
            else:
                continue
                
            file = Gio.File.new_for_path(os.path.join(self.cache_dir, cache.file))
            if file.query_exists():
                file.delete()
            cache.delete_instance()

            for item in self.queue:
                if self.current and item.id == self.current.id:
                    self.filecopy_cancel.cancel()

                if item.id == track.id:
                    self.queue.remove(item)

        if len(self.queue) > 0:
            self._start_processing()
    
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

        while len(self.queue) > 0:
            log.info("Processing item")
            self.current_batch_count += 1
            item = self.queue[0]
            if self.thread.stopped():
                break
            
            new_item = db.OfflineCache.get_by_id(item.id)

            if not new_item.copied and os.path.exists(new_item.track.file):
                log.info("Copying item")
                Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, self.ui.switch_to_working, _("Downloading ") + new_item.track.book.name, False)
                self.current = new_item
                
                destination = Gio.File.new_for_path(os.path.join(self.cache_dir, new_item.file))
                source = Gio.File.new_for_path(new_item.track.file)
                flags = Gio.FileCopyFlags.OVERWRITE
                try:
                    copied = source.copy(destination, flags, self.filecopy_cancel, self.__update_copy_status, None)
                except:
                    self.queue.remove(item)
                    continue

                if copied:
                    db.OfflineCache.update(copied=True).where(db.OfflineCache.id == new_item.id).execute()
                
            self.queue.remove(item)

        self.current = None
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, self.ui.switch_to_playing)

    def _is_processing(self):
        """
        """
        if self.thread:
            return self.thread.is_alive()
        else:
            return False

    def _fill_queue_from_db(self):
        for item in db.OfflineCache.select().where(db.OfflineCache.copied == False):
            if not any(item.id == queued.id for queued in self.queue):
                self.queue.append(item)
                self.total_batch_count += 1

    def __update_copy_status(self, current_num_bytes, total_num_bytes, user_data):
        progress =  (self.current_batch_count / self.total_batch_count) + ((current_num_bytes / total_num_bytes) / self.total_batch_count)
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE,
                             self.ui.titlebar.update_progress_bar.set_fraction, progress)