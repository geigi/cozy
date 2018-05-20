import logging
from gi.repository import Gio

log = logging.getLogger("fs_monitor")

class FilesystemMonitor:
    """
    This class handles all filesystem monitoring operations.
    """
    def __init__(self):
        self.volume_monitor = Gio.VolumeMonitor.get()
        self.volume_monitor.connect("mount-added", self.__on_mount_added)
        self.volume_monitor.connect("mount-removed", self.__on_mount_added)

        self.init_offline_mode()

    def init_offline_mode(self):
        mounts = self.volume_monitor.get_mounts()
        # go through all audiobook locations and test if they can be found in the mounts list


    def close(self):
        """
        Free all references.
        """
        self.volume_monitor.unref()

    def __on_mount_added(self, monitor, mount):
        """
        A volume was mounted.
        Disable offline mode for this volume.
        """
        log.info("Volume mounted: " + mount.get_root().get_path())

    def __on_mount_removed(self, monitor, mount):
        """
        A volume was unmounted.
        Enable offline mode for this volume.
        """
        log.info("Volume unmounted: " + mount.get_root().get_path())
        # switch to offline version if currently playing