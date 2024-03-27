import logging
from threading import Thread
from typing import Callable

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

import cozy.control.filesystem_monitor as fs_monitor
import cozy.ext.inject as inject
import cozy.report.reporter as report
from cozy.application_settings import ApplicationSettings
from cozy.architecture.event_sender import EventSender
from cozy.architecture.singleton import Singleton
from cozy.control.db import books, close_db
from cozy.media.files import Files
from cozy.media.importer import Importer, ScanStatus
from cozy.media.player import Player
from cozy.model.settings import Settings as SettingsModel
from cozy.ui.about_window import AboutWindow
from cozy.ui.library_view import LibraryView
from cozy.ui.preferences_window import PreferencesWindow
from cozy.ui.widgets.first_import_button import FirstImportButton
from cozy.view_model.storages_view_model import StoragesViewModel

log = logging.getLogger("ui")


class CozyUI(EventSender, metaclass=Singleton):
    """CozyUI is the main ui class"""

    fs_monitor = inject.attr(fs_monitor.FilesystemMonitor)
    application_settings = inject.attr(ApplicationSettings)
    _importer: Importer = inject.attr(Importer)
    _settings: SettingsModel = inject.attr(SettingsModel)
    _files: Files = inject.attr(Files)
    _player: Player = inject.attr(Player)
    _storages_view_model: StoragesViewModel = inject.attr(StoragesViewModel)

    _library_view: LibraryView

    def __init__(self, app, version):
        super().__init__()
        self.app = app
        self.version = version

    def activate(self, library_view: LibraryView):
        self.__init_window()
        self.__init_actions()
        self.__init_components()

        self._library_view = library_view

        self.auto_import()
        self.check_for_tracks()

    def startup(self):
        self.window_builder = Gtk.Builder.new_from_resource("/com/github/geigi/cozy/ui/main_window.ui")
        self.window: Adw.ApplicationWindow = self.window_builder.get_object("app_window")

    def __init_window(self):
        """
        Add fields for all UI objects we need to access from code.
        Initialize everything we can't do from the UI files like events and other stuff.
        """
        log.info("Initializing main window")
        self._restore_window_size()
        self.window.set_title("Cozy")
        self.window.set_application(self.app)

        self.window.connect("close-request", self.on_close)
        self.window.connect("notify::default-width", self._on_window_size_allocate)
        self.window.connect("notify::default-height", self._on_window_size_allocate)

        self._drop_target = Gtk.DropTarget()
        self._drop_target.set_gtypes([Gdk.FileList])
        self._drop_target.set_actions(Gdk.DragAction.COPY)
        self._drop_target.connect("enter", self._on_drag_enter)
        self._drop_target.connect("leave", self._on_drag_leave)
        self._drop_target.connect("drop", self._on_drag_data_received)
        self.window.add_controller(self._drop_target)

        self.main_stack: Gtk.Stack = self.window_builder.get_object("main_stack")
        self.navigation_view: Adw.NavigationView = self.window_builder.get_object("navigation_view")
        self.drop_revealer: Gtk.Revealer = self.window_builder.get_object("drop_revealer")

        self.window.present()

    def __init_actions(self):
        """
        Init all app actions.
        """
        self.create_action("about", self.show_about_window, ["F1"])
        self.create_action("prefs", self.show_preferences_window, ["<primary>comma"])
        self.create_action("quit", self.quit, ["<primary>q", "<primary>w"])
        self.scan_action = self.create_action("scan", self.scan)
        self.play_pause_action = self.create_action("play_pause", self.play_pause, ["space"])

        self.hide_offline_action = Gio.SimpleAction.new_stateful(
            "hide_offline", None, GLib.Variant.new_boolean(self.application_settings.hide_offline)
        )
        self.hide_offline_action.connect("change-state", self.__on_hide_offline)
        self.app.add_action(self.hide_offline_action)

    def __init_components(self):
        path = self._settings.default_location.path if self._settings.storage_locations else None
        self.import_button = FirstImportButton(self._set_audiobook_path, path)
        self.get_object("welcome_status_page").set_child(self.import_button)

        if not self._player.loaded_book:
            self.block_ui_buttons(True)

        self._importer.add_listener(self._on_importer_event)

    def create_action(
        self,
        name: str,
        callback: Callable[[Gio.SimpleAction, None], None],
        shortcuts: list[str] | None = None,
    ) -> Gio.SimpleAction:
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.app.add_action(action)

        if shortcuts:
            self.app.set_accels_for_action(f"app.{name}", shortcuts)

        return action

    def get_object(self, name):
        return self.window_builder.get_object(name)

    def quit(self, action, parameter):
        """
        Quit app.
        """
        self.on_close(None)
        self.app.quit()

    def show_about_window(self, *_):
        AboutWindow(self.version).present(self.window)

    def show_preferences_window(self, *_):
        PreferencesWindow().present(self.window)

    def play_pause(self, *_):
        self._player.play_pause()

    def block_ui_buttons(self, block, scan=False):
        """
        Makes the buttons to interact with the player insensetive.
        :param block: Boolean
        """
        sensitive = not block
        try:
            self.play_pause_action.set_enabled(sensitive)
            if scan:
                self.scan_action.set_enabled(sensitive)
                self.hide_offline_action.set_enabled(sensitive)
        except GLib.GError:
            pass

    def switch_to_playing(self):
        """
        Switch the UI state back to playing.
        This enables all UI functionality for the user.
        """
        if self.navigation_view.props.visible_page != "book_overview" and self.main_stack.props.visible_child_name != "welcome":
            self.navigation_view.pop_to_tag("main")

        if self._player.loaded_book:
            self.block_ui_buttons(False, True)
        else:
            # we want to only block the player controls
            # TODO: rework. this is messy
            self.block_ui_buttons(False, True)
            self.block_ui_buttons(True, False)

    def check_for_tracks(self):
        """
        Check if there are any imported files.
        If there aren't display a welcome screen.
        """
        if books().count() < 1:
            self.block_ui_buttons(True)

    def scan(self, _, __):
        thread = Thread(target=self._importer.scan, name="ScanMediaThread")
        thread.start()

    def auto_import(self):
        if self.application_settings.autoscan:
            self.scan(None, None)

    def __on_hide_offline(self, action, value):
        """
        Show/Hide offline books action handler.
        """
        action.set_state(value)
        self.application_settings.hide_offline = value.get_boolean()

    def _on_drag_enter(self, *_):
        self.drop_revealer.set_reveal_child(True)
        self.main_stack.add_css_class("blurred")
        return True

    def _on_drag_leave(self, *_):
        self.drop_revealer.set_reveal_child(False)
        self.main_stack.remove_css_class("blurred")
        return True

    def _on_drag_data_received(self, widget, value, *_):
        thread = Thread(target=self._files.copy, args=[value.get_files()], name="DnDImportThread")
        thread.start()
        return True

    def _set_audiobook_path(self, path: str | None) -> None:
        if path is None:
            return

        self.import_button.disable()
        self._storages_view_model.add_first_storage_location(path)
        self.scan(None, None)
        self.fs_monitor.init_offline_mode()

    def on_close(self, widget, data=None):
        """
        Close and dispose everything that needs to be when window is closed.
        """
        log.info("Closing.")
        self.fs_monitor.close()

        self._player.destroy()

        close_db()

        report.close()

        log.info("Closing app.")
        self.app.quit()
        log.info("App closed.")

    def get_builder(self):
        return self.window_builder

    def _on_importer_event(self, event: str, message):
        if event == "scan" and message == ScanStatus.SUCCESS:
            self.check_for_tracks()

    def _restore_window_size(self):
        width = self.application_settings.window_width
        height = self.application_settings.window_height
        self.window.set_default_size(width, height)
        if self.application_settings.window_maximize:
            self.window.maximize()
        else:
            self.window.unmaximize()

    def _on_window_size_allocate(self, *_):
        width, height = self.window.get_default_size()
        self.application_settings.window_width = width
        self.application_settings.window_height = height
        self.application_settings.window_maximize = self.window.is_maximized()

