from threading import Thread
import logging
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio

import cozy.db as db
import cozy.tools as tools
import cozy.importer as importer

log = logging.getLogger("settings")

class Settings:
    """
    This class contains all logic for cozys preferences.
    """
    ui = None
    default_dark_mode = None

    def __init__(self, ui):
        self.ui = ui
        self.builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/settings.ui")

        # get settings window
        self.window = self.builder.get_object("settings_window")
        self.window.set_transient_for(self.ui.window)
        self.window.connect("delete-event", self.ui.hide_window)

        self.add_storage_button = self.builder.get_object("add_location_button")
        self.add_storage_button.connect("clicked", self.__on_add_storage_clicked)
        self.remove_storage_button = self.builder.get_object("remove_location_button")
        self.remove_storage_button.connect("clicked", self.__on_remove_storage_clicked)        
        self.default_storage_button = self.builder.get_object("default_location_button")
        self.default_storage_button.connect("clicked", self.__on_default_storage_clicked)
        self.storage_list_box = self.builder.get_object("storage_list_box")
        self.storage_list_box.connect("row-activated", self.__on_storage_box_changed)

        self._init_storage()
        self.__init_bindings()
        self.__on_storage_box_changed(None, None)

        self.set_darkmode()

    def _init_storage(self):
        """
        Display settings from the database in the ui.
        """
        for location in db.Storage.select():
            row = StorageListBoxRow(self.ui, location.id, location.path, location.default)
            self.storage_list_box.add(row)
            if location.default == True:
                self.storage_list_box.select_row(row)

    def __init_bindings(self):
        """
        Bind Gio.Settings to widgets in settings dialog.
        """
        sl_switch = self.builder.get_object("symlinks_switch")
        tools.get_glib_settings().bind("symlinks", sl_switch, "active",
                           Gio.SettingsBindFlags.DEFAULT)

        auto_scan_switch = self.builder.get_object("auto_scan_switch")
        tools.get_glib_settings().bind("autoscan", auto_scan_switch,
                           "active", Gio.SettingsBindFlags.DEFAULT)

        timer_suspend_switch = self.builder.get_object(
            "timer_suspend_switch")
        tools.get_glib_settings().bind("suspend", timer_suspend_switch,
                           "active", Gio.SettingsBindFlags.DEFAULT)

        replay_switch = self.builder.get_object("replay_switch")
        tools.get_glib_settings().bind("replay", replay_switch, "active",
                           Gio.SettingsBindFlags.DEFAULT)

        crc32_switch = self.builder.get_object("crc32_switch")
        tools.get_glib_settings().bind("use-crc32", crc32_switch, "active",
                           Gio.SettingsBindFlags.DEFAULT)

        titlebar_remaining_time_switch = self.builder.get_object("titlebar_remaining_time_switch")
        tools.get_glib_settings().bind("titlebar-remaining-time", titlebar_remaining_time_switch, "active",
                           Gio.SettingsBindFlags.DEFAULT)

        dark_mode_switch = self.builder.get_object("dark_mode_switch")
        tools.get_glib_settings().bind("dark-mode", dark_mode_switch, "active",
                           Gio.SettingsBindFlags.DEFAULT)

        tools.get_glib_settings().connect("changed", self.__on_settings_changed)

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

        row = self.storage_list_box.get_selected_row()
        if row is not None and row.get_default() != True:
            self.remove_storage_button.set_sensitive(sensitive)
            self.default_storage_button.set_sensitive(sensitive)

    def __on_add_storage_clicked(self, widget):
        """
        Add a new storage selector to the ui.
        """
        db_obj = db.Storage.create(path="")
        self.storage_list_box.add(StorageListBoxRow(self.ui, db_obj.id, "", False))

    def __on_remove_storage_clicked(self, widget):
        """
        Remove a storage selector from the ui and database.
        """
        row = self.storage_list_box.get_selected_row()
        db.Storage.select().where(db.Storage.path == row.path).get().delete_instance()
        self.storage_list_box.remove(row)
        thread = Thread(target=db.remove_tracks_with_path, args=(self.ui, row.path))
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
        if row is None or row.get_default() == True:
            sensitive = False
        else:
            sensitive = True
        
        self.remove_storage_button.set_sensitive(sensitive)
        self.default_storage_button.set_sensitive(sensitive)

        for child in self.storage_list_box.get_children():
            if row is not None and child.db_id == row.db_id:
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

    def set_darkmode(self):
        settings = Gtk.Settings.get_default()

        if self.default_dark_mode is None:
            self.default_dark_mode = settings.get_property("gtk-application-prefer-dark-theme")
        
        user_enabled = tools.get_glib_settings().get_boolean("dark-mode")
        if user_enabled:
            settings.set_property("gtk-application-prefer-dark-theme", True)
        else:
            settings.set_property("gtk-application-prefer-dark-theme", self.default_dark_mode)


class StorageListBoxRow(Gtk.ListBoxRow):
    """
    This class represents a listboxitem for a storage location.
    """

    def __init__(self, ui, db_id, path, default=False):
        super(Gtk.ListBoxRow, self).__init__()
        self.ui = ui
        self.db_id = db_id
        self.path = path
        self.default = default

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

        self.location_chooser = Gtk.FileChooserButton()
        self.location_chooser.set_local_only(False)
        self.location_chooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        if path != "":
            self.location_chooser.set_current_folder(path)
        self.location_chooser.set_halign(Gtk.Align.START)
        self.location_chooser.props.hexpand = True
        self.location_chooser.connect("file-set", self.__on_folder_changed)
        
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
        db.Storage.update(default=default).where(db.Storage.id == self.db_id).execute()

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

    def __on_folder_changed(self, widget):
        """
        Update the location in the database.
        Start an import scan or a rebase operation.
        """
        new_path = self.location_chooser.get_file().get_path()
        # First test if the new location is already in the database
        if db.Storage.select().where(db.Storage.path == new_path).count() > 0:
            return

        # If not, add it to the database
        old_path = db.Storage.select().where(db.Storage.id == self.db_id).get().path
        self.path = new_path
        db.Storage.update(path=new_path).where(db.Storage.id == self.db_id).execute()

        # Run a reimport or rebase
        if old_path == "":
            log.info("New audiobook location added. Starting import scan.")
            self.ui.scan(None, False)
        else:
            log.info("Audio book location changed, rebasing the location in db.")
            self.ui.switch_to_working(_("Changing audio book location..."), False)
            thread = Thread(target=importer.rebase_location, args=(
                self.ui, old_path, new_path))
            thread.start()