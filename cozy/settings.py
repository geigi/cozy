from threading import Thread
import logging
import platform
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, Pango

from cozy.event_sender import EventSender
from cozy.singleton import Singleton

import cozy.db
import cozy.tools as tools
import cozy.importer as importer
import cozy.artwork_cache as artwork_cache
import cozy.ui

log = logging.getLogger("settings")

class Settings(EventSender, metaclass=Singleton):
    """
    This class contains all logic for cozys preferences.
    """
    ui = None
    default_dark_mode = None

    def __init__(self):
        self.ui = cozy.ui.CozyUI()
        self.builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/settings.ui")

        # get settings window
        self.window = self.builder.get_object("settings_window")
        self.window.set_transient_for(self.ui.window)
        self.window.connect("delete-event", self.ui.hide_window)

        if platform.system() == 'Darwin':
            headerbar = self.builder.get_object('headerbar')
            headerbar.set_decoration_layout("close:menu")

        self.add_storage_button = self.builder.get_object("add_location_button")
        self.add_storage_button.connect("clicked", self.__on_add_storage_clicked)
        self.remove_storage_button = self.builder.get_object("remove_location_button")
        self.remove_storage_button.connect("clicked", self.__on_remove_storage_clicked)        
        self.external_button = self.builder.get_object("external_button")
        self.external_button.connect("clicked", self.__on_external_clicked)
        self.default_storage_button = self.builder.get_object("default_location_button")
        self.default_storage_button.connect("clicked", self.__on_default_storage_clicked)
        self.storage_list_box = self.builder.get_object("storage_list_box")
        self.storage_list_box.connect("row-activated", self.__on_storage_box_changed)

        self.remove_blacklist_button = self.builder.get_object("remove_blacklist_button")
        self.remove_blacklist_button.connect("clicked", self.__on_remove_blacklist_clicked)
        #self.remove_blacklist_button.set_sensitive(False)
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
        tools.remove_all_children(self.storage_list_box)
        for location in cozy.db.Storage.select():
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
        for file in cozy.db.StorageBlackList.select():
            self.blacklist_model.append([file.path, file.id])
        self.__on_blacklist_selection_changed(None)

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

        tools.get_glib_settings().bind("prefer-external-cover", self.external_cover_switch, "active",
                           Gio.SettingsBindFlags.DEFAULT)

        tools.get_glib_settings().bind("sleep-timer-fadeout", self.sleep_fadeout_switch, "active",
                           Gio.SettingsBindFlags.DEFAULT)

        tools.get_glib_settings().bind("sleep-timer-fadeout-duration", self.fadeout_duration_adjustment,
                           "value", Gio.SettingsBindFlags.DEFAULT)

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
        self.external_button.set_sensitive(sensitive)

        row = self.storage_list_box.get_selected_row()
        if row and row.get_default() != True:
            self.remove_storage_button.set_sensitive(sensitive)
            self.default_storage_button.set_sensitive(sensitive)

    def __on_add_storage_clicked(self, widget):
        """
        Add a new storage selector to the ui.
        """
        db_obj = cozy.db.Storage.create(path="")
        self.storage_list_box.add(StorageListBoxRow(self, db_obj.id, "", False, False))

    def __on_remove_storage_clicked(self, widget):
        """
        Remove a storage selector from the ui and database.
        """
        row = self.storage_list_box.get_selected_row()
        cozy.db.Storage.select().where(cozy.db.Storage.path == row.path).get().delete_instance()
        self.storage_list_box.remove(row)
        self.emit_event("storage-removed", row.path)
        thread = Thread(target=cozy.db.remove_tracks_with_path, args=(self.ui, row.path), name=("RemoveStorageFromDB"))
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
            
            self.external_button.set_active(row.external)

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
            
            cozy.db.StorageBlackList.delete().where(cozy.db.StorageBlackList.id in ids).execute()

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
        The new setting will be written to the cozy.db.
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
        tools.get_glib_settings().set_boolean("prefer-external-cover", state)
        artwork_cache.delete_artwork_cache()
        self.ui.refresh_content()

    def __on_force_refresh_clicked(self, widget):
        """
        Start a force refresh of the database.
        """
        self.ui.scan(None, False, True)


    def set_darkmode(self):
        """
        Enable or disable the dark gtk theme.
        """
        settings = Gtk.Settings.get_default()

        if self.default_dark_mode is None:
            self.default_dark_mode = settings.get_property("gtk-application-prefer-dark-theme")
        
        user_enabled = tools.get_glib_settings().get_boolean("dark-mode")
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
        

class StorageListBoxRow(Gtk.ListBoxRow):
    """
    This class represents a listboxitem for a storage location.
    """

    def __init__(self, parent, db_id, path, external, default=False):
        super(Gtk.ListBoxRow, self).__init__()
        self.ui = cozy.ui.CozyUI()
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
        cozy.db.Storage.update(default=default).where(cozy.db.Storage.id == self.db_id).execute()

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
        This method also writes the setting to the cozy.db.
        """
        self.external = external
        if external:
            self.type_image.set_from_icon_name("network-server-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
            self.type_image.set_tooltip_text(_("External drive"))
        else:
            self.type_image.set_from_icon_name("drive-harddisk-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
            self.type_image.set_tooltip_text(_("Internal drive"))

        cozy.db.Storage.update(external=external).where(cozy.db.Storage.id == self.db_id).execute()

    def __on_folder_changed(self, widget):
        """
        Update the location in the database.
        Start an import scan or a rebase operation.
        """
        new_path = self.location_chooser.get_file().get_path()
        # First test if the new location is already in the database
        if cozy.db.Storage.select().where(cozy.db.Storage.path == new_path).count() > 0:
            return

        # If not, add it to the database
        old_path = cozy.db.Storage.select().where(cozy.db.Storage.id == self.db_id).get().path
        self.path = new_path
        cozy.db.Storage.update(path=new_path).where(cozy.db.Storage.id == self.db_id).execute()

        # Run a reimport or rebase
        if old_path == "":
            self.parent.emit_event("storage-added", self.path)
            log.info("New audiobook location added. Starting import scan.")
            self.ui.scan(None, False)
        else:
            self.parent.emit_event("storage-changed", self.path)
            log.info("Audio book location changed, rebasing the location in cozy.db.")
            self.ui.switch_to_working(_("Changing audio book location..."), False)
            thread = Thread(target=importer.rebase_location, args=(
                self.ui, old_path, new_path), name="RebaseStorageLocationThread")
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