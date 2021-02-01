import logging
from typing import List

import cozy.ext.inject as inject
from gi.repository import Gio

from cozy.architecture.event_sender import EventSender
from cozy.control.db import get_tracks
from cozy.model.book import Book
from cozy.model.settings import Settings
from cozy.model.storage import Storage

log = logging.getLogger("fs_monitor")


class StorageNotFound(Exception):
    pass


class ExternalStorage:
    storage: Storage
    online: bool

    def __init__(self, storage: Storage, online: bool):
        self.storage = storage
        self.online = online


class FilesystemMonitor(EventSender):
    external_storage: List[ExternalStorage] = []
    _settings: Settings = inject.attr(Settings)

    def __init__(self):
        super().__init__()
        self.volume_monitor: Gio.VolumeMonitor = Gio.VolumeMonitor.get()
        self.volume_monitor.connect("mount-added", self.__on_mount_added)
        self.volume_monitor.connect("mount-removed", self.__on_mount_removed)

        self.init_offline_mode()

        from cozy.ui.settings import Settings as UISettings
        self._ui_settings = inject.instance(UISettings)
        self._ui_settings.add_listener(self.__on_settings_changed)

    def init_offline_mode(self):
        external_storage = []
        mounts = self.volume_monitor.get_mounts()
        # go through all audiobook locations and test if they can be found in the mounts list

        for storage in self._settings.external_storage_locations:
            online = False
            if any(mount.get_root().get_path() in storage.path for mount in mounts):
                online = True
            self.external_storage.append(ExternalStorage(storage=storage, online=online))

    def close(self):
        """
        Free all references.
        """
        # self.volume_monitor.unref()
        pass

    def get_book_online(self, book: Book):
        result = next((storage.online for storage in self.external_storage if storage.storage.path in book.chapters[0].file),
                      True)
        return result

    def is_book_online(self, book):
        """
        """
        result = next(
            (storage.online for storage in self.external_storage if storage.storage.path in get_tracks(book).first().file), True)
        return (result)

    def is_path_online(self, path: str) -> bool:
        result = next((storage.online for storage in self.external_storage if storage.storage.path in path), True)
        return result

    def is_track_online(self, track):
        """
        """
        result = next((storage.online for storage in self.external_storage if storage.storage.path in track.file), True)
        return (result)

    def get_offline_storages(self):
        return [i.storage.path for i in self.external_storage if not i.online]

    def is_storage_online(self, storage: Storage) -> bool:
        storage = next((storage for storage in self.external_storage if storage.storage == storage), None)

        if not storage:
            raise StorageNotFound

        return storage.online

    def is_external(self, directory: str) -> bool:
        mounts: List[Gio.Mount] = self.volume_monitor.get_mounts()
        for mount in mounts:
            if mount.get_root().get_path() in directory:
                if mount.can_unmount():
                    return True

        return False

    def __on_mount_added(self, monitor, mount):
        """
        A volume was mounted.
        Disable offline mode for this volume.
        """
        mount_path = mount.get_root().get_path()

        if not mount_path:
            log.warning("Mount added but no mount_path is present. Skipping...")
            return

        log.debug("Volume mounted: " + mount_path)

        storage = next((s for s in self.external_storage if mount_path in s.storage.path), None)
        if storage:
            log.info("Storage online: " + mount_path)
            storage.online = True
            self.emit_event("storage-online", storage.storage.path)

    def __on_mount_removed(self, monitor, mount):
        """
        A volume was unmounted.
        Enable offline mode for this volume.
        """
        mount_path = mount.get_root().get_path()

        if not mount_path:
            log.warning("Mount removed but no mount_path is present. Skipping...")
            return

        log.debug("Volume unmounted: " + mount_path)

        storage = next((s for s in self.external_storage if mount_path in s.storage.path), None)
        if storage:
            log.info("Storage offline: " + mount_path)
            storage.online = False
            self.emit_event("storage-offline", storage.storage.path)

            # switch to offline version if currently playing

    def __on_settings_changed(self, event, message):
        """
        This method reacts to storage settings changes.
        """
        if event == "external-storage-added" or event == "storage-changed" or (
                event == "storage-added" and message != ""):
            self.init_offline_mode()
        elif event == "storage-removed" or event == "external-storage-removed":
            self.external_storage = [item for item in self.external_storage if item.storage.path not in message]
