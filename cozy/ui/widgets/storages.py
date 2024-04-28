from typing import Callable

from gi.repository import Adw, Gio, GLib, GObject, Gtk

from cozy.ext import inject
from cozy.model.storage import Storage
from cozy.view_model.storages_view_model import StoragesViewModel


def ask_storage_location(callback: Callable[[str | None], None], initial_folder: str | None = None):
    location_chooser = Gtk.FileDialog(title=_("Set Audiobooks Directory"))

    if initial_folder:
        gfile = Gio.File.new_for_path(initial_folder)
        location_chooser.set_initial_folder(gfile)

    def finish_callback(dialog, result):
        try:
            file = dialog.select_folder_finish(result)
        except GLib.GError:
            pass
        else:
            callback(None if file is None else file.get_path())

    location_chooser.select_folder(inject.instance("MainWindow").window, None, finish_callback)


@Gtk.Template.from_resource("/com/github/geigi/cozy/ui/storage_row.ui")
class StorageRow(Adw.ActionRow):
    __gtype_name__ = "StorageRow"

    icon: Gtk.Image = Gtk.Template.Child()
    default_icon: Gtk.Image = Gtk.Template.Child()
    menu_button: Gtk.MenuButton = Gtk.Template.Child()

    def __init__(self, model: Storage, menu_model: Gio.Menu) -> None:
        self._model = model

        super().__init__(title=model.path)
        self.connect("activated", self.ask_for_new_location)

        self.menu_button.set_menu_model(menu_model)
        self.menu_button.connect("notify::active", self._on_menu_opened)

        self._set_default_icon()
        self._set_drive_icon()

    @property
    def model(self) -> Storage:
        return self._model

    def ask_for_new_location(self, *_) -> None:
        ask_storage_location(self._on_folder_changed, initial_folder=self._model.path)

    def _on_folder_changed(self, new_path: str | None) -> None:
        if new_path is not None:
            self.emit("location-changed", new_path)

    def _on_menu_opened(self, *_) -> None:
        self.emit("menu-opened")

    def _set_drive_icon(self) -> None:
        if self._model.external:
            self.icon.set_from_icon_name("network-server-symbolic")
            self.icon.set_tooltip_text(_("External drive"))
        else:
            self.icon.set_from_icon_name("folder-open-symbolic")
            self.icon.set_tooltip_text(_("Internal drive"))

    def _set_default_icon(self) -> None:
        self.default_icon.set_visible(self._model.default)


GObject.signal_new(
    "location-changed",
    StorageRow,
    GObject.SIGNAL_RUN_LAST,
    GObject.TYPE_PYOBJECT,
    (GObject.TYPE_PYOBJECT,),
)
GObject.signal_new("menu-opened", StorageRow, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT, ())


@Gtk.Template.from_resource("/com/github/geigi/cozy/ui/storage_locations.ui")
class StorageLocations(Adw.PreferencesGroup):
    __gtype_name__ = "StorageLocations"

    _view_model: StoragesViewModel = inject.attr(StoragesViewModel)

    storage_locations_list: Gtk.ListBox = Gtk.Template.Child()
    storage_menu: Gio.Menu = Gtk.Template.Child()

    def __init__(self) -> None:
        super().__init__()

        self._view_model.bind_to("storage_locations", self._reload_storage_list)
        self._view_model.bind_to("storage_attributes", self._reload_storage_list)

        self._create_actions()
        self.new_storage_button = self._create_new_storage_button()

        self._reload_storage_list()

    def _create_actions(self) -> None:
        self.action_group = Gio.SimpleActionGroup.new()
        self.insert_action_group("storage", self.action_group)

        self.set_external_action = Gio.SimpleAction.new_stateful(
            "mark-external", None, GLib.Variant.new_boolean(False)
        )
        self._set_external_signal_handler = self.set_external_action.connect(
            "notify::state", self._mark_storage_location_external
        )
        self.action_group.add_action(self.set_external_action)

        self.remove_action = Gio.SimpleAction.new("remove", None)
        self.remove_action.connect("activate", self._remove_storage_location)
        self.action_group.add_action(self.remove_action)

        self.make_default_action = Gio.SimpleAction.new("make-default", None)
        self.make_default_action.connect("activate", self._set_default_storage_location)
        self.action_group.add_action(self.make_default_action)

    def _create_new_storage_button(self) -> Adw.ActionRow:
        icon = Gtk.Image(icon_name="list-add-symbolic", margin_top=18, margin_bottom=18)
        row = Adw.ActionRow(selectable=False, activatable=True)
        row.connect("activated", self._on_new_storage_clicked)
        row.set_child(icon)
        return row

    def _reload_storage_list(self) -> None:
        self.storage_locations_list.remove_all()

        for storage in self._view_model.storages:
            row = StorageRow(storage, menu_model=self.storage_menu)
            row.connect("location-changed", self._on_storage_location_changed)
            row.connect("menu-opened", self._on_storage_menu_opened)
            self.storage_locations_list.append(row)

        self.storage_locations_list.append(self.new_storage_button)

    def _remove_storage_location(self, *_) -> None:
        self._view_model.remove(self._view_model.selected_storage)

    def _set_default_storage_location(self, *_) -> None:
        self._view_model.set_default(self._view_model.selected_storage)

    def _mark_storage_location_external(
        self, action: Gio.SimpleAction, value: GObject.ParamSpec
    ) -> None:
        value = action.get_property(value.name)
        self._view_model.set_external(self._view_model.selected_storage, value)

    def _on_new_storage_clicked(self, *_) -> None:
        ask_storage_location(self._view_model.add_storage_location)

    def _on_storage_location_changed(self, widget: StorageRow, new_location: str) -> None:
        self._view_model.change_storage_location(widget.model, new_location)

    def _on_storage_menu_opened(self, widget: StorageRow) -> None:
        with self.set_external_action.handler_block(self._set_external_signal_handler):
            self.set_external_action.props.state = GLib.Variant.new_boolean(widget.model.external)

        self.remove_action.props.enabled = (
            not widget.model.default and len(self._view_model.storages) > 1
        )
        self.make_default_action.props.enabled = widget.model is not self._view_model.default
        self._view_model.selected_storage = widget.model
