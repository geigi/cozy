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

        self.__init_bindings()

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


class BlacklistColumn(Gtk.TreeViewColumn):
    """
    A column for a storage location.
    """

    def __init__(self, path):
        super(Gtk.TreeViewColumn, self).__init__()
        self.path = path
