import logging
from threading import Thread

from cozy.control.filesystem_monitor import FilesystemMonitor
from cozy.model.storage import Storage
from cozy.ext import inject
from cozy.model.library import Library
from cozy.model.settings import Settings
from gi.repository import Gtk, GObject

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
        box.set_margin_left(5)
        box.set_margin_right(6)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        self.default_image = Gtk.Image()
        self.default_image.set_from_icon_name("emblem-default-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        self.default_image.set_margin_right(5)

        self.type_image = Gtk.Image()
        self._set_drive_icon()
        self.location_chooser = Gtk.FileChooserButton()
        self.location_chooser.set_local_only(False)
        self.location_chooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        if self._model.path != "":
            self.location_chooser.set_current_folder(self._model.path)
        self.location_chooser.set_halign(Gtk.Align.FILL)
        self.location_chooser.props.hexpand = True
        self.location_chooser.connect("file-set", self.__on_folder_changed)
        self.location_chooser.set_margin_right(6)

        box.add(self.type_image)
        box.add(self.location_chooser)
        box.add(self.default_image)
        self.add(box)
        self._set_default_icon()

    @property
    def model(self) -> Storage:
        return self._model

    def refresh(self):
        self._set_drive_icon()
        self._set_default_icon()

    def __on_folder_changed(self, widget):
        new_path = self.location_chooser.get_file().get_path()
        self.emit("location-changed", new_path)

    def _set_drive_icon(self):
        if self._model.external:
            icon_name = "network-server-symbolic"
            self.type_image.set_tooltip_text(_("External drive"))
        else:
            icon_name = "drive-harddisk-symbolic"
            self.type_image.set_tooltip_text(_("Internal drive"))
        
        self.type_image.set_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
        self.type_image.set_margin_right(5)

    def _set_default_icon(self):
        self.default_image.set_visible(self._model.default)

GObject.signal_new('location-changed', StorageListBoxRow, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))
