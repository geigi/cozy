from pathlib import Path
import logging
from typing import List, Tuple

import inject
from gi.repository import Gio

from cozy.architecture.event_sender import EventSender
from cozy.architecture.singleton import Singleton
import cozy.ui.settings
import cozy.ui
from cozy.control.db import get_tracks
from cozy.model.book import Book
from cozy.model.settings import Settings
from cozy.model.storage import Storage

log = logging.getLogger("fs_monitor")

class FilesystemMonitor(EventSender):
    external_storage: List[Tuple[Storage, bool]] = []
    _settings: Settings = inject.attr(Settings)

    def __init__(self):
        self.volume_monitor = Gio.VolumeMonitor.get()
        self.volume_monitor.connect("mount-added", self.__on_mount_added)
        self.volume_monitor.connect("mount-removed", self.__on_mount_removed)

        self.init_offline_mode()

        cozy.ui.settings.Settings().add_listener(self.__on_settings_changed)

    def init_offline_mode(self):
        external_storage = []
        mounts = self.volume_monitor.get_mounts()
        # go through all audiobook locations and test if they can be found in the mounts list

        external_storages = [storage for storage in self._settings.storage_locations if storage.external]

        for storage in external_storages:
            online = False
            if any(mount.get_root().get_path() in storage.path for mount in mounts):
                online = True
            self.external_storage.append([storage, online])

    def close(self):
        """
        Free all references.
        """
        #self.volume_monitor.unref()
        pass

    def get_book_online(self, book: Book):
        result = next((storage[1] for storage in self.external_storage if storage[0].path in book.chapters[0].file),
                      True)
        return result

    def is_book_online(self, book):
        """
        """
        result = next((storage[1] for storage in self.external_storage if storage[0].path in get_tracks(book).first().file), True)
        return (result)

    def is_track_online(self, track):
        """
        """
        result = next((storage[1] for storage in self.external_storage if storage[0].path in track.file), True)
        return (result)
    
    def get_offline_storages(self):
        return [i[0].path for i in self.external_storage if not i[1]]

    def __on_mount_added(self, monitor, mount):
        """
        A volume was mounted.
        Disable offline mode for this volume.
        """
        mount_path = mount.get_root().get_path()
        log.debug("Volume mounted: " + mount_path)

        storage = next((s for s in self.external_storage if mount_path in s[0].path), None)
        if storage:
            log.info("Storage online: " + mount_path)
            storage[1] = True
            self.emit_event("storage-online", storage[0].path)

    def __on_mount_removed(self, monitor, mount):
        """
        A volume was unmounted.
        Enable offline mode for this volume.
        """
        mount_path = mount.get_root().get_path()
        log.debug("Volume unmounted: " + mount_path)
        
        storage = next((s for s in self.external_storage if mount_path in s[0].path), None)
        if storage:
            log.info("Storage offline: " + mount_path)
            storage[1] = False
            self.emit_event("storage-offline", storage[0].path)

            # switch to offline version if currently playing
        
    def __on_settings_changed(self, event, message):
        """
        This method reacts to storage settings changes.
        """
        if event == "external-storage-added" or event == "storage-changed" or (event == "storage-added" and message != ""):
            self.init_offline_mode()
        elif event == "storage-removed" or event == "external-storage-removed":
            self.external_storage = [item for item in self.external_storage if item[0].path not in message]
