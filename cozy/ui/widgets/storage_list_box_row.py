import logging
from threading import Thread

from cozy.control.filesystem_monitor import FilesystemMonitor
from cozy.model.storage import Storage
from cozy.ext import inject
from cozy.model.library import Library
from cozy.model.settings import Settings
from gi.repository import Gtk, GObject, Gio, GLib

log = logging.getLogger("settings")


class StorageListBoxRow(Gtk.ListBoxRow):
    """
    This class represents a listboxitem for a storage location.
    """

    main_window = inject.attr("MainWindow")

    def __init__(self, model: Storage):
        self._model = model

        super(Gtk.ListBoxRow, self).__init__()
        box = Gtk.Box()
        box.set_orientation(Gtk.Orientation.HORIZONTAL)
        box.set_spacing(3)
        box.set_halign(Gtk.Align.FILL)
        box.set_valign(Gtk.Align.CENTER)
        box.set_margin_start(6)
        box.set_margin_end(6)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

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

    def __on_folder_changed(self, new_path):
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

    def _on_location_chooser_clicked(self, *junk):
        location_chooser = Gtk.FileDialog(title=_("Set Audiobooks Directory"))

        if self._model.path != "":
            folder = Gio.File.new_for_path(self._model.path)
            location_chooser.set_initial_folder(folder)

        location_chooser.select_folder(self.main_window.window, None, self._location_chooser_open_callback)

    def _location_chooser_open_callback(self, dialog, result):
        try:
            file = dialog.select_folder_finish(result)
        except GLib.GError:
            pass
        else:
            if file is not None:
                self.__on_folder_changed(file.get_path())

GObject.signal_new('location-changed', StorageListBoxRow, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))

