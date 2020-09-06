from gettext import gettext

import gi
import cozy.ext.inject as inject

from cozy.control.filesystem_monitor import FilesystemMonitor

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class Warnings():
    _fs_monitor: FilesystemMonitor = inject.attr(FilesystemMonitor)

    def __init__(self, button: Gtk.MenuButton):
        self.button = button

        self.builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/warning_popover.ui")

        self.popover = self.builder.get_object("warning_popover")
        self.warning_container: Gtk.Box = self.builder.get_object("warning_container")

        self._fs_monitor.add_listener(self.__on_storage_changed)

        for storage in self._fs_monitor.get_offline_storages():
            self.append_text(gettext('{storage} is offline.').format(storage=storage))

        self.__hide_show_button()

    def get_popover(self):
        return self.popover

    def append_text(self, text):
        label = Gtk.Label()
        self.warning_container.add(label)
        label.set_visible(True)
        label.set_text(text)

    def __on_storage_changed(self, event, message):
        if event == "storage-offline":
            self.append_text(gettext('{storage} is offline.').format(storage=message))
        if event == "storage-online":
            for label in self.warning_container.get_children():
                if message in label.get_text():
                    self.warning_container.remove(label)

        self.__hide_show_button()

    def __hide_show_button(self):
        if len(self.warning_container.get_children()) > 0:
            self.button.set_visible(True)
        else:
            self.button.set_visible(False)