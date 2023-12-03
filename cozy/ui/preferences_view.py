from gi.repository import Adw, Gio, Gtk

from cozy.ext import inject
from cozy.ui.widgets.error_reporting import ErrorReporting
from cozy.ui.widgets.storage_list_box_row import StorageListBoxRow
from cozy.view_model.settings_view_model import SettingsViewModel


@Gtk.Template.from_resource('/com/github/geigi/cozy/preferences.ui')
class PreferencesView(Adw.PreferencesWindow):
    __gtype_name__ = "PreferencesWindow"

    main_window = inject.attr("MainWindow")

    _glib_settings: Gio.Settings = inject.attr(Gio.Settings)
    _view_model: SettingsViewModel = inject.attr(SettingsViewModel)

    dark_mode_switch: Gtk.Switch = Gtk.Template.Child()
    swap_author_reader_switch: Gtk.Switch = Gtk.Template.Child()
    replay_switch: Gtk.Switch = Gtk.Template.Child()
    sleep_timer_fadeout_switch: Adw.SwitchRow = Gtk.Template.Child()
    fadeout_duration_spin_button: Adw.SpinRow = Gtk.Template.Child()
    artwork_prefer_external_switch: Gtk.Switch = Gtk.Template.Child()

    rewind_duration_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    forward_duration_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    fadeout_duration_adjustment: Gtk.Adjustment = Gtk.Template.Child()

    storage_list_box: Gtk.ListBox = Gtk.Template.Child()
    add_storage_button: Gtk.Button = Gtk.Template.Child()
    remove_storage_button: Gtk.Button = Gtk.Template.Child()
    external_storage_toggle_button: Gtk.ToggleButton = Gtk.Template.Child()
    default_storage_button: Gtk.ToggleButton = Gtk.Template.Child()

    user_feedback_preference_group: Adw.PreferencesRow = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        error_reporting = ErrorReporting()
        error_reporting.show_header(False)
        self.user_feedback_preference_group.add(error_reporting)

        self._bind_settings()
        self._bind_view_model()

        self.sleep_timer_fadeout_switch.connect("notify::active", self._on_sleep_fadeout_switch_changed)
        self.fadeout_duration_spin_button.set_sensitive(self.sleep_timer_fadeout_switch.props.active)

        self.storage_list_box.connect("row-selected", self._on_storage_box_changed)

        self.add_storage_button.connect("clicked", self._on_add_storage_clicked)
        self.remove_storage_button.connect("clicked", self._on_remove_storage_clicked)
        self.external_button_handle_id = self.external_storage_toggle_button.connect("clicked", self._on_external_clicked)
        self.default_storage_button.connect("clicked", self._on_default_storage_clicked)

        self.set_transient_for(self.main_window.window)

        self._init_storage_box()

    def _bind_view_model(self):
        self._view_model.bind_to("storage_locations", self._init_storage_box)
        self._view_model.bind_to("storage_attributes", self._refresh_storage_rows)

    def _bind_settings(self):
        self._glib_settings.bind("dark-mode", self.dark_mode_switch, "active",
                                 Gio.SettingsBindFlags.DEFAULT)

        self._glib_settings.bind("swap-author-reader", self.swap_author_reader_switch, "active",
                                 Gio.SettingsBindFlags.DEFAULT)

        self._glib_settings.bind("replay", self.replay_switch, "active", Gio.SettingsBindFlags.DEFAULT)
        self._glib_settings.bind("rewind-duration", self.rewind_duration_adjustment, "value",
                                 Gio.SettingsBindFlags.DEFAULT)
        self._glib_settings.bind("forward-duration", self.forward_duration_adjustment, "value",
                                 Gio.SettingsBindFlags.DEFAULT)

        self._glib_settings.bind("sleep-timer-fadeout", self.sleep_timer_fadeout_switch, "active",
                                 Gio.SettingsBindFlags.DEFAULT)

        self._glib_settings.bind("sleep-timer-fadeout-duration", self.fadeout_duration_adjustment,
                                 "value", Gio.SettingsBindFlags.DEFAULT)

        self._glib_settings.bind("prefer-external-cover", self.artwork_prefer_external_switch, "active",
                                 Gio.SettingsBindFlags.DEFAULT)

    def _on_sleep_fadeout_switch_changed(self, widget, param):
        state = widget.get_property(param.name)
        self.fadeout_duration_spin_button.set_sensitive(state)

    def _init_storage_box(self):
        self.storage_list_box.remove_all_children()

        for storage in self._view_model.storage_locations:
            row = StorageListBoxRow(storage)
            row.connect("location-changed", self._on_storage_location_changed)
            self.storage_list_box.append(row)

    def _on_add_storage_clicked(self, _):
        self._view_model.add_storage_location()

    def _on_remove_storage_clicked(self, _):
        row = self.storage_list_box.get_selected_row()
        self._view_model.remove_storage_location(row.model)

    def _on_default_storage_clicked(self, _):
        row = self.storage_list_box.get_selected_row()
        self._view_model.set_default_storage(row.model)
        self._on_storage_box_changed(None, row)

    def _on_storage_box_changed(self, _, row):
        row = self.storage_list_box.get_selected_row()
        if row is None:
            sensitive = False
            default_sensitive = False
            remove_sensitive = False
        else:
            sensitive = True
            remove_sensitive = True
            if row.model.default or not row.model.path:
                default_sensitive = remove_sensitive = False
            else:
                default_sensitive = True

            if not row.model.path:
                remove_sensitive = True
            
            self.external_storage_toggle_button.handler_block(self.external_button_handle_id)
            self.external_storage_toggle_button.set_active(row.model.external)
            self.external_storage_toggle_button.handler_unblock(self.external_button_handle_id)

        self.remove_storage_button.set_sensitive(remove_sensitive)
        self.external_storage_toggle_button.set_sensitive(sensitive)
        self.default_storage_button.set_sensitive(default_sensitive)

    def _on_external_clicked(self, _):
        external = self.external_storage_toggle_button.get_active()
        row = self.storage_list_box.get_selected_row()
        self._view_model.set_storage_external(row.model, external)        

    def _on_storage_location_changed(self, widget, new_location):
        self._view_model.change_storage_location(widget.model, new_location)

    def _refresh_storage_rows(self):
        self._init_storage_box()
        
        self._on_storage_box_changed(None, self.storage_list_box.get_selected_row())
    
    def _on_lock_ui_changed(self):
        sensitive = not self._view_model.lock_ui

        self.storage_list_box.set_sensitive(sensitive)
        self.add_storage_button.set_sensitive(sensitive)
        self.remove_storage_button.set_sensitive(sensitive)
        self.external_storage_toggle_button.set_sensitive(sensitive)
        self.default_storage_button.set_sensitive(sensitive)
        self._on_storage_box_changed(None, self.storage_list_box.get_selected_row())

