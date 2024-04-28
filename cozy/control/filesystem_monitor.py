import logging

from gi.repository import Gio

import cozy.ext.inject as inject
from cozy.architecture.event_sender import EventSender
from cozy.model.book import Book
from cozy.model.settings import Settings
from cozy.model.storage import Storage
from cozy.report import reporter

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
    external_storage: list[ExternalStorage] = []
    _settings: Settings = inject.attr(Settings)

    def __init__(self):
        super().__init__()
        self.volume_monitor: Gio.VolumeMonitor = Gio.VolumeMonitor.get()
        self.volume_monitor.connect("mount-added", self.__on_mount_added)
        self.volume_monitor.connect("mount-removed", self.__on_mount_removed)

        self.init_offline_mode()

        from cozy.view_model.settings_view_model import SettingsViewModel
        self._settings_view_model = inject.instance(SettingsViewModel)
        self._settings_view_model.add_listener(self.__on_settings_changed)

    def init_offline_mode(self):
        mounts = self.volume_monitor.get_mounts()
        # go through all audiobook locations and test if they can be found in the mounts list

        for storage in self._settings.external_storage_locations:
            online = any(
                mount.get_root().get_path() and mount.get_root().get_path() in storage.path
                for mount in mounts
            )
            self.external_storage.append(ExternalStorage(storage=storage, online=online))

    def close(self):
        """
        Free all references.
        """
        # self.volume_monitor.unref()

    def get_book_online(self, book: Book):
        try:
            return next(
                (storage.online for storage in self.external_storage if storage.storage.path in book.chapters[0].file),
                True)
        except IndexError:
            return True

    def is_track_online(self, track):
        return next((storage.online for storage in self.external_storage if storage.storage.path in track.file), True)

    def get_offline_storages(self):
        return [i.storage.path for i in self.external_storage if not i.online]

    def is_storage_online(self, storage: Storage) -> bool:
        storage = next((storage for storage in self.external_storage if storage.storage == storage), None)

        if not storage:
            raise StorageNotFound

        return storage.online

    def is_external(self, directory: str) -> bool:
        mounts: list[Gio.Mount] = self.volume_monitor.get_mounts()

        for mount in mounts:
            root = mount.get_root()
            if not root:
                log.error("Failed to test for external drive. Mountpoint has no root object.")
                reporter.error("fs_monitor", "Failed to test for external drive. Mountpoint has no root object.")
                return False

            path = root.get_path()
            if not path:
                log.error("Failed to test for external drive. Root object has no path.")
                reporter.error("fs_monitor", "Failed to test for external drive. Root object has no path.")
                return False

            if path in directory and mount.can_unmount():
                log.info("Storage location %s is external", directory)
                return True

        log.info("Storage location %s is not external", directory)
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

        log.debug("Volume mounted: %s", mount_path)

        storage = next((s for s in self.external_storage if mount_path in s.storage.path), None)
        if storage:
            log.info("Storage online: %s", mount_path)
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

        log.debug("Volume unmounted: %s", mount_path)

        storage = next((s for s in self.external_storage if mount_path in s.storage.path), None)
        if storage:
            log.info("Storage offline: %s", mount_path)
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
            self.external_storage = [item for item in self.external_storage if item.storage.path not in message.path]
