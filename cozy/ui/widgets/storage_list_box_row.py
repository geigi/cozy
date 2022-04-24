import logging
from threading import Thread

from cozy.control.filesystem_monitor import FilesystemMonitor
from cozy.model.storage import Storage
from cozy.ext import inject
from cozy.model.library import Library
from cozy.model.settings import Settings
from gi.repository import Gtk, GObject, Gio

log = logging.getLogger("settings")


class StorageListBoxRow(Gtk.ListBoxRow):
    """
    This class represents a listboxitem for a storage location.
    """
    def __init__(self, model: Storage):
        self._model = model

        super(Gtk.ListBoxRow, self).__init__()
        box = Gtk.Box()
        box.set_orientation(Gtk.Orientation.HORIZONTAL)
        box.set_spacing(3)
        box.set_halign(Gtk.Align.FILL)
        box.set_valign(Gtk.Align.CENTER)
        box.set_margin_start(5)
        box.set_margin_end(6)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        self.default_image = Gtk.Image()
        self.default_image.set_from_icon_name("emblem-default-symbolic")
        self.default_image.set_margin_end(5)

        self.type_image = Gtk.Image()
        self._set_drive_icon()
        self.location_chooser = Gtk.Button()
        self.location_label = Gtk.Label()
        self.location_chooser.set_child(self.location_label)
        self.location_chooser.set_margin_end(6)
        self.location_chooser.connect("clicked", self._on_location_chooser_clicked)

        self.location_label.set_text(model.path)

        box.append(self.type_image)
        box.append(self.location_chooser)
        box.append(self.default_image)
        self.set_child(box)
        self._set_default_icon()

    @property
    def model(self) -> Storage:
        return self._model

    def refresh(self):
        self._set_drive_icon()
        self._set_default_icon()

    def __on_folder_changed(self, chooser: Gtk.FileChooserNative, *_):
        new_path = chooser.get_file().get_path()
        self.emit("location-changed", new_path)

    def _set_drive_icon(self):
        if self._model.external:
            icon_name = "network-server-symbolic"
            self.type_image.set_tooltip_text(_("External drive"))
        else:
            icon_name = "drive-harddisk-symbolic"
            self.type_image.set_tooltip_text(_("Internal drive"))
        
        self.type_image.set_from_icon_name(icon_name)
        self.type_image.set_margin_end(5)

    def _set_default_icon(self):
        self.default_image.set_visible(self._model.default)

    def _on_location_chooser_clicked(self, *_):
        file_chooser = Gtk.FileChooserNative()
        file_chooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        if self._model.path != "":
            file = Gio.File.new_for_path(self._model.path)
            file_chooser.set_current_folder(file)

        file_chooser.connect("response", self.__on_folder_changed)
        file_chooser.show()

GObject.signal_new('location-changed', StorageListBoxRow, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))
