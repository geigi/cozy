import logging
from threading import Thread

from gi.repository import Gtk

import cozy.ui
from cozy.db.storage import Storage
from cozy.ext import inject
from cozy.model.library import Library
from cozy.model.storage_block_list import StorageBlockList

log = logging.getLogger("settings")


class StorageListBoxRow(Gtk.ListBoxRow):
    """
    This class represents a listboxitem for a storage location.
    """
    _library: Library = inject.attr(Library)
    _block_list: StorageBlockList = inject.attr(StorageBlockList)

    def __init__(self, parent, db_id, path, external, default=False):
        super(Gtk.ListBoxRow, self).__init__()
        self.ui = cozy.ui.main_view.CozyUI()
        self.db_id = db_id
        self.path = path
        self.default = default
        self.external = external
        self.parent = parent

        box = Gtk.Box()
        box.set_orientation(Gtk.Orientation.HORIZONTAL)
        box.set_spacing(3)
        box.set_halign(Gtk.Align.FILL)
        box.set_valign(Gtk.Align.CENTER)
        box.set_margin_left(4)
        box.set_margin_right(4)
        box.set_margin_top(5)
        box.set_margin_bottom(5)

        self.default_image = Gtk.Image()
        self.default_image.set_from_icon_name("emblem-default-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        self.default_image.set_margin_right(5)

        self.type_image = self.__get_type_image()

        self.location_chooser = Gtk.FileChooserButton()
        self.location_chooser.set_local_only(False)
        self.location_chooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        if path != "":
            self.location_chooser.set_current_folder(path)
        self.location_chooser.set_halign(Gtk.Align.START)
        self.location_chooser.props.hexpand = True
        self.location_chooser.connect("file-set", self.__on_folder_changed)

        box.add(self.type_image)
        box.add(self.location_chooser)
        box.add(self.default_image)
        self.add(box)
        self.show_all()
        self.default_image.set_visible(default)

    def set_default(self, default):
        """
        Set this storage location as the default
        :param default: Boolean
        """
        self.default = default
        self.default_image.set_visible(default)
        Storage.update(default=default).where(Storage.id == self.db_id).execute()

    def get_default(self):
        """
        Is this storage location the default one?
        """
        return self.default

    def set_selected(self, selected):
        """
        Set UI colors for the default img.
        :param selected: Boolean
        """
        if selected:
            self.default_image.get_style_context().add_class("selected")
        else:
            self.default_image.get_style_context().remove_class("selected")

    def set_external(self, external):
        """
        Set this entry as external/internal storage.
        This method also writes the setting to the cozy.
        """
        self.external = external
        if external:
            self.type_image.set_from_icon_name("network-server-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
            self.type_image.set_tooltip_text(_("External drive"))
        else:
            self.type_image.set_from_icon_name("drive-harddisk-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
            self.type_image.set_tooltip_text(_("Internal drive"))

        Storage.update(external=external).where(Storage.id == self.db_id).execute()

    def __on_folder_changed(self, widget):
        """
        Update the location in the database.
        Start an import scan or a rebase operation.
        """
        new_path = self.location_chooser.get_file().get_path()
        # First test if the new location is already in the database
        if Storage.select().where(Storage.path == new_path).count() > 0:
            return

        # If not, add it to the database
        old_path = Storage.select().where(Storage.id == self.db_id).get().path
        self.path = new_path
        Storage.update(path=new_path).where(Storage.id == self.db_id).execute()

        # Run a reimport or rebase
        if old_path == "":
            self.parent.emit_event("storage-added", self.path)
            log.info("New audiobook location added. Starting import scan.")
            self.ui.scan(None, None)
        else:
            self.parent.emit_event("storage-changed", self.path)
            log.info("Audio book location changed, rebasing the location in cozy.")
            self.ui.switch_to_working(_("Changing audio book location…"), False)
            self._block_list.rebase_path(old_path, new_path)
            thread = Thread(target=self._library.rebase_path, args=(old_path, new_path), name="RebaseStorageLocationThread")
            thread.start()

    def __get_type_image(self):
        """
        Returns the matching drive icon for this storage location.
        :return: External or internal drive gtk image.
        """
        type_image = Gtk.Image()
        if self.external:
            icon_name = "network-server-symbolic"
            type_image.set_tooltip_text(_("External drive"))
        else:
            icon_name = "drive-harddisk-symbolic"
            type_image.set_tooltip_text(_("Internal drive"))
        type_image.set_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
        type_image.set_margin_right(5)

        return type_image