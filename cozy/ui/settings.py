import logging
import gi

from cozy.db.storage import Storage
from cozy.db.storage_blacklist import StorageBlackList
from cozy.ext import inject
from cozy.model.library import Library
from cozy.ui.widgets.ScrollWrapper import ScrollWrapper
from cozy.ui.widgets.storage_list_box_row import StorageListBoxRow
from cozy.view_model.settings_view_model import SettingsViewModel

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio

from cozy.architecture.event_sender import EventSender

import cozy.ui

log = logging.getLogger("settings")


class Settings(EventSender):
    """
    This class contains all logic for cozys preferences.
    """
    _glib_settings: Gio.Settings = inject.attr(Gio.Settings)

    view_model = None
    ui = None

    def __init__(self):
        super().__init__()
        from cozy.control.artwork_cache import ArtworkCache
        self._artwork_cache: ArtworkCache = inject.instance(ArtworkCache)
        self._library: Library = inject.instance(Library)

        self.view_model = SettingsViewModel()

        self.ui = cozy.ui.main_view.CozyUI()
        self.builder = Gtk.Builder.new_from_resource(
            "/com/github/geigi/cozy/settings.ui")

        # get settings window
        self.window = self.builder.get_object("settings_window")
        self.window.set_modal(self.ui.window)
        self.window.connect("delete-event", self.ui.hide_window)

        self.add_storage_button = self.builder.get_object("add_location_button")
        self.add_storage_button.connect("clicked", self.__on_add_storage_clicked)
        self.remove_storage_button = self.builder.get_object("remove_location_button")
        self.remove_storage_button.connect("clicked", self.__on_remove_storage_clicked)
        self.external_button = self.builder.get_object("external_button")
        self.external_button_handle_id = self.external_button.connect("clicked", self.__on_external_clicked)
        self.default_storage_button = self.builder.get_object("default_location_button")
        self.default_storage_button.connect("clicked", self.__on_default_storage_clicked)
        self.storage_list_box = self.builder.get_object("storage_list_box")
        self.storage_list_box.connect("row-activated", self.__on_storage_box_changed)

        self._init_storage()
        self.__init_bindings()
        self.__on_storage_box_changed(None, None)

    def _init_storage(self):
        """
        Display settings from the database in the ui.
        """
        found_default = False
        self.storage_list_box.remove_all_children()
        for location in Storage.select():
            row = StorageListBoxRow(self, location.id, location.path, location.external, location.default)
            self.storage_list_box.add(row)
            if location.default:
                if found_default:
                    row.set_default(False)
                else:
                    found_default = True
                    self.storage_list_box.select_row(row)

        self.__on_storage_box_changed(None, None)

    def __init_bindings(self):
        """
        Bind Gio.Settings to widgets in settings dialog.
        """
        sl_switch = self.builder.get_object("symlinks_switch")
        self._glib_settings.bind("symlinks", sl_switch, "active",
                                 Gio.SettingsBindFlags.DEFAULT)

        auto_scan_switch = self.builder.get_object("auto_scan_switch")
        self._glib_settings.bind("autoscan", auto_scan_switch,
                                 "active", Gio.SettingsBindFlags.DEFAULT)

        timer_suspend_switch = self.builder.get_object(
            "timer_suspend_switch")
        self._glib_settings.bind("suspend", timer_suspend_switch,
                                 "active", Gio.SettingsBindFlags.DEFAULT)

        replay_switch = self.builder.get_object("replay_switch")
        self._glib_settings.bind("replay", replay_switch, "active",
                                 Gio.SettingsBindFlags.DEFAULT)

        titlebar_remaining_time_switch = self.builder.get_object("titlebar_remaining_time_switch")
        self._glib_settings.bind("titlebar-remaining-time", titlebar_remaining_time_switch, "active",
                                 Gio.SettingsBindFlags.DEFAULT)

        swap_author_reader_switch = self.builder.get_object("swap_author_reader_switch")
        self._glib_settings.bind("swap-author-reader", swap_author_reader_switch, "active",
                                 Gio.SettingsBindFlags.DEFAULT)

    def show(self):
        """
        Show the settings window.
        """
        self.window.show()

    def get_storage_elements_blocked(self):
        """
        Are the location ui elements currently blocked?
        """
        return not self.storage_list_box.get_sensitive()

    def block_ui_elements(self, block):
        """
        Block/unblock UI storage elements.
        """
        sensitive = not block
        self.storage_list_box.set_sensitive(sensitive)
        self.add_storage_button.set_sensitive(sensitive)
        self.external_button.set_sensitive(sensitive)

        row = self.storage_list_box.get_selected_row()
        if row and row.get_default() != True:
            self.remove_storage_button.set_sensitive(sensitive)
            self.default_storage_button.set_sensitive(sensitive)

    def __on_add_storage_clicked(self, widget):
        """
        Add a new storage selector to the ui.
        """
        db_obj = Storage.create(path="")
        self.storage_list_box.add(StorageListBoxRow(self, db_obj.id, "", False, False))

    def __on_remove_storage_clicked(self, widget):
        """
        Remove a storage selector from the ui and database.
        """
        row = self.storage_list_box.get_selected_row()
        Storage.select().where(Storage.path == row.path).get().delete_instance()
        self.storage_list_box.remove(row)
        self.emit_event("storage-removed", row.path)
        self.__on_storage_box_changed(None, None)

    def __on_default_storage_clicked(self, widget):
        """
        Select a location as default storage.
        """
        for row in self.storage_list_box.get_children():
            row.set_default(False)

        self.storage_list_box.get_selected_row().set_default(True)

        self.__on_storage_box_changed(None, None)

    def __on_storage_box_changed(self, widget, row):
        """
        Disable/enable toolbar buttons
        """
        row = self.storage_list_box.get_selected_row()
        if row is None:
            sensitive = False
            default_sensitive = False
        else:
            sensitive = True
            if row.get_default():
                default_sensitive = False
            else:
                default_sensitive = True
            self.external_button.handler_block(self.external_button_handle_id)
            self.external_button.set_active(row.external)
            self.external_button.handler_unblock(self.external_button_handle_id)

        self.remove_storage_button.set_sensitive(default_sensitive)
        self.external_button.set_sensitive(sensitive)
        self.default_storage_button.set_sensitive(default_sensitive)

        for child in self.storage_list_box.get_children():
            if row and child.db_id == row.db_id:
                child.set_selected(True)
            else:
                child.set_selected(False)

    def __on_external_clicked(self, widget):
        """
        The external/internal button was clicked.
        The new setting will be written to the cozy.
        """
        external = self.external_button.get_active()

        row = self.storage_list_box.get_selected_row()
        row.set_external(external)

        if external:
            self.emit_event("external-storage-added", row.path)
        else:
            self.emit_event("external-storage-removed", row.path)


class BlacklistColumn(Gtk.TreeViewColumn):
    """
    A column for a storage location.
    """

    def __init__(self, path):
        super(Gtk.TreeViewColumn, self).__init__()
        self.path = path
