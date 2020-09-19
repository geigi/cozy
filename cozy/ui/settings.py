from threading import Thread
import logging
import gi

from cozy.control.db import remove_tracks_with_path
from cozy.db.storage import Storage
from cozy.db.storage_blacklist import StorageBlackList
from cozy.ext import inject
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
    default_dark_mode = None

    def __init__(self):
        from cozy.control.artwork_cache import ArtworkCache
        self._artwork_cache: ArtworkCache = inject.instance(ArtworkCache)

        self.view_model = SettingsViewModel()

        self.ui = cozy.ui.main_view.CozyUI()
        self.builder = Gtk.Builder.new_from_resource(
            "/com/github/geigi/cozy/settings.ui")

        # get settings window
        self.window = self.builder.get_object("settings_window")
        self.window.set_transient_for(self.ui.window)
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

        self.remove_blacklist_button = self.builder.get_object("remove_blacklist_button")
        self.remove_blacklist_button.connect("clicked", self.__on_remove_blacklist_clicked)
        # self.remove_blacklist_button.set_sensitive(False)
        self.blacklist_tree_view = self.builder.get_object("blacklist_tree_view")
        self.blacklist_model = self.builder.get_object("blacklist_store")
        self.blacklist_tree_view.get_selection().connect("changed", self.__on_blacklist_selection_changed)

        self.sleep_fadeout_switch = self.builder.get_object("sleep_fadeout_switch")
        self.sleep_fadeout_switch.connect("notify::active", self.__on_fadeout_switch_changed)

        self.external_cover_switch = self.builder.get_object("external_cover_switch")
        self.external_cover_switch.connect("state-set", self.__on_external_cover_switch_changed)

        self.fadeout_duration_label = self.builder.get_object("fadeout_duration_label")
        self.fadeout_duration_row = self.builder.get_object("fadeout_duration_row")

        self.fadeout_duration_adjustment = self.builder.get_object("fadeout_duration_adjustment")
        self.fadeout_duration_adjustment.connect("value-changed", self.__on_fadeout_adjustment_changed)
        self.__on_fadeout_adjustment_changed(self.fadeout_duration_adjustment)

        self.force_refresh_button = self.builder.get_object("force_refresh_button")
        self.force_refresh_button.connect("clicked", self.__on_force_refresh_clicked)

        self.settings_stack: Gtk.Stack = self.builder.get_object("settings_stack")
        self.settings_stack.connect("notify::visible-child", self._on_settings_stack_changed)

        from cozy.ui.widgets.error_reporting import ErrorReporting
        self.settings_stack.add_titled(ScrollWrapper(ErrorReporting()), "feedback", _("Feedback"))

        self._init_storage()
        self._init_blacklist()
        self.__init_bindings()
        self.__on_storage_box_changed(None, None)

        self.set_darkmode()

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

    def _init_blacklist(self):
        """
        Init the Storage location list.
        """
        for file in StorageBlackList.select():
            self.blacklist_model.append([file.path, file.id])
        self.__on_blacklist_selection_changed(None)

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

        dark_mode_switch = self.builder.get_object("dark_mode_switch")
        self._glib_settings.bind("dark-mode", dark_mode_switch, "active",
                                 Gio.SettingsBindFlags.DEFAULT)

        swap_author_reader_switch = self.builder.get_object("swap_author_reader_switch")
        self._glib_settings.bind("swap-author-reader", swap_author_reader_switch, "active",
                                 Gio.SettingsBindFlags.DEFAULT)

        self._glib_settings.bind("prefer-external-cover", self.external_cover_switch, "active",
                                 Gio.SettingsBindFlags.DEFAULT)

        self._glib_settings.bind("sleep-timer-fadeout", self.sleep_fadeout_switch, "active",
                                 Gio.SettingsBindFlags.DEFAULT)

        self._glib_settings.bind("sleep-timer-fadeout-duration", self.fadeout_duration_adjustment,
                                 "value", Gio.SettingsBindFlags.DEFAULT)

        self._glib_settings.connect("changed", self.__on_settings_changed)

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
        thread = Thread(target=remove_tracks_with_path, args=(self.ui, row.path), name=("RemoveStorageFromDB"))
        thread.start()
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

    def __on_settings_changed(self, settings, key):
        """
        Updates cozy's ui to changed Gio settings.
        """
        if key == "titlebar-remaining-time":
            self.ui.titlebar._on_progress_setting_changed()
        elif key == "dark-mode":
            self.set_darkmode()

    def __on_remove_blacklist_clicked(self, widget):
        """
        Remove the selected storage from the db and ui.
        TODO: Does this trigger a rescan?
        """
        model, pathlist = self.blacklist_tree_view.get_selection().get_selected_rows()
        if pathlist:
            ids = []
            for path in reversed(pathlist):
                treeiter = model.get_iter(path)
                ids.append(self.blacklist_model.get_value(treeiter, 1))
                self.blacklist_model.remove(treeiter)

            StorageBlackList.delete().where(StorageBlackList.id in ids).execute()

        self.__on_blacklist_selection_changed(self.blacklist_tree_view.get_selection())

    def __on_blacklist_selection_changed(self, tree_selection):
        """
        The user selected a different storage location.
        Here we enable or disable the remove button depending on 
        weather this is the default storage or not.
        """
        if tree_selection is None or len(tree_selection.get_selected_rows()[1]) < 1:
            self.remove_blacklist_button.set_sensitive(False)
        else:
            self.remove_blacklist_button.set_sensitive(True)

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

    def __on_fadeout_adjustment_changed(self, adjustment):
        """
        This refreshes the label belonging to the fadeout duration adjustment.
        """
        self.fadeout_duration_label.set_text(str(int(adjustment.get_value())) + " s")

    def __on_fadeout_switch_changed(self, switch, state):
        """
        Enable/Disable sensitivity for the fadeout duration settings row.
        """
        self.fadeout_duration_row.set_sensitive(switch.get_active())

    def __on_external_cover_switch_changed(self, switch, state):
        """
        Set the glib setting prefer-external-cover.
        This is needed because the binding gets called after this function.
        Then refresh the artwork cache.
        """
        # We have to test if everything is initialized before triggering the refresh
        # otherwise this might be just the initial call when starting up
        if self.ui.is_initialized:
            self._glib_settings.set_boolean("prefer-external-cover", state)
            self._artwork_cache.delete_artwork_cache()
            self.ui.refresh_content()

    def __on_force_refresh_clicked(self, widget):
        """
        Start a force refresh of the database.
        """
        self.ui.scan(None, False, True)

    def _on_settings_stack_changed(self, widget, property):
        page = widget.props.visible_child_name

        if page == "files":
            self.blacklist_model.clear()
            self._init_blacklist()

    def set_darkmode(self):
        """
        Enable or disable the dark gtk theme.
        """
        settings = Gtk.Settings.get_default()

        if self.default_dark_mode is None:
            self.default_dark_mode = settings.get_property("gtk-application-prefer-dark-theme")

        user_enabled = self._glib_settings.get_boolean("dark-mode")
        if user_enabled:
            settings.set_property("gtk-application-prefer-dark-theme", True)
        else:
            settings.set_property("gtk-application-prefer-dark-theme", self.default_dark_mode)


class BlacklistColumn(Gtk.TreeViewColumn):
    """
    A column for a storage location.
    """

    def __init__(self, path):
        super(Gtk.TreeViewColumn, self).__init__()
        self.path = path
