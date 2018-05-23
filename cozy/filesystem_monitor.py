import logging
from gi.repository import Gio

from cozy.event_sender import EventSender
from cozy.settings import Settings
import cozy.db as db

log = logging.getLogger("fs_monitor")

class FilesystemMonitor(EventSender):
    external_storage = []
    """
    This class handles all filesystem monitoring operations.
    """
    def __init__(self):
        self.volume_monitor = Gio.VolumeMonitor.get()
        self.volume_monitor.connect("mount-added", self.__on_mount_added)
        self.volume_monitor.connect("mount-removed", self.__on_mount_added)

        self.init_offline_mode()

        Settings().add_listener(self.__on_settings_changed)

    def init_offline_mode(self):
        mounts = self.volume_monitor.get_mounts()
        # go through all audiobook locations and test if they can be found in the mounts list

        for dir in db.get_external_storage_locations():
            online = False
            if any(mount.get_root().get_path() in dir.path for mount in mounts):
                online = True
            self.external_storage.append([dir.path, online])

    def close(self):
        """
        Free all references.
        """
        #self.volume_monitor.unref()
        pass

    def __on_mount_added(self, monitor, mount):
        """
        A volume was mounted.
        Disable offline mode for this volume.
        """
        log.info("Volume mounted: " + mount.get_root().get_path())

        storage = next((s for s in self.external_storage if mount in s[0]), None)
        if storage:
            self.emit_event("mount-added", mount.get_root().get_path())
            storage[1] = True

    def __on_mount_removed(self, monitor, mount):
        """
        A volume was unmounted.
        Enable offline mode for this volume.
        """
        log.info("Volume unmounted: " + mount.get_root().get_path())
        
        storage = next((s for s in self.external_storage if mount in s[0]), None)
        if storage:
            self.emit_event("mount-removed", mount.get_root().get_path())
            storage[1] = False

            # switch to offline version if currently playing

    def __on_settings_changed(self, event, message):
        print(event)