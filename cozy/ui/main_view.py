import logging
from threading import Thread
from typing import Callable

import inject
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

import cozy.control.filesystem_monitor as fs_monitor
import cozy.report.reporter as report
from cozy.architecture.event_sender import EventSender
from cozy.architecture.singleton import Singleton
from cozy.control.db import books, close_db
from cozy.media.files import Files
from cozy.media.importer import Importer, ScanStatus
from cozy.media.player import Player
from cozy.model.settings import Settings as SettingsModel
from cozy.settings import ApplicationSettings
from cozy.ui.about_window import AboutWindow
from cozy.ui.book_detail_view import BookDetailView
from cozy.ui.library_view import LibraryView
from cozy.ui.preferences_window import PreferencesWindow
from cozy.ui.widgets.first_import_button import FirstImportButton
from cozy.view_model.playback_control_view_model import PlaybackControlViewModel
from cozy.view_model.playback_speed_view_model import PlaybackSpeedViewModel
from cozy.view_model.storages_view_model import StoragesViewModel

log = logging.getLogger("ui")


class CozyUI(EventSender, metaclass=Singleton):
    """CozyUI is the main ui class"""

    fs_monitor = inject.attr(fs_monitor.FilesystemMonitor)
    application_settings = inject.attr(ApplicationSettings)
    _importer: Importer = inject.attr(Importer)
    _settings: SettingsModel = inject.attr(SettingsModel)
    _gio_settings: Gio.Settings = inject.attr(Gio.Settings)
    _files: Files = inject.attr(Files)
    _player: Player = inject.attr(Player)
    _storages_view_model: StoragesViewModel = inject.attr(StoragesViewModel)
    _playback_control_view_model: PlaybackControlViewModel = inject.attr(PlaybackControlViewModel)
    _playback_speed_view_model: PlaybackSpeedViewModel = inject.attr(PlaybackSpeedViewModel)

    _library_view: LibraryView

    def __init__(self, app, version):
        super().__init__()
        self.app = app
        self.version = version

        self._actions_to_disable = []

    def activate(self, library_view: LibraryView):
        self.__init_window()
        self.__init_actions()
        self.__init_components()

        self._library_view = library_view

        self.auto_import()
        self.check_for_tracks()

    def startup(self):
        self.window_builder = Gtk.Builder.new_from_resource(
            "/com/github/geigi/cozy/ui/main_window.ui"
        )
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

        self.navigation_view.add(BookDetailView())

        self.window.present()

    def __init_actions(self):
        """
        Init all app actions.
        """
        self.create_action("about", self.show_about_window, ["F1"], global_shorcut=True)
        self.create_action("reset_book", self.reset_book)
        self.create_action("remove_book", self.remove_book)

        self.create_action("mark_book_as_read", self.mark_book_as_read)
        self.create_action("mark_book_as_unread", self.mark_book_as_unread)
        self.create_action("jump_to_book_folder", self.jump_to_book_folder)

        self.create_action("prefs", self.show_preferences_window, ["<primary>comma"], global_shorcut=True)
        self.create_action("quit", self.quit, ["<primary>q", "<primary>w"], global_shorcut=True)

        self.scan_action = self.create_action("scan", self.scan)

        self.hide_offline_action = Gio.SimpleAction.new_stateful(
            "hide_offline", None, GLib.Variant.new_boolean(self.application_settings.hide_offline)
        )
        self.hide_offline_action.connect("change-state", self.__on_hide_offline)
        self.app.add_action(self.hide_offline_action)

        self.hide_read_action = Gio.SimpleAction.new_stateful(
            "hide_read", None, GLib.Variant.new_boolean(self.application_settings.hide_read)
        )
        self.hide_read_action.connect("change-state", self.__on_hide_read)
        self.app.add_action(self.hide_read_action)

    def set_hotkeys_enabled(self, enabled: bool) -> None:
        for action in self._actions_to_disable:
            action.set_enabled(enabled)

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
        *,
        global_shorcut: bool = False,
    ) -> Gio.SimpleAction:
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.app.add_action(action)

        if shortcuts:
            self.app.set_accels_for_action(f"app.{name}", shortcuts)

        if not global_shorcut:
            self._actions_to_disable.append(action)

        return action

    def refresh_library_filters(self):
        self._library_view.refresh_filters()

    def reset_book(self, *_) -> None:
        if self.app.selected_book is not None:
            self.app.selected_book.reset()
        self.refresh_library_filters()

    def remove_book(self, *_) -> None:
        if self.app.selected_book is not None:
            self.app.selected_book.remove()

    def mark_book_as_read(self, *_) -> None:
        if self.app.selected_book is not None:
            self.app.selected_book.mark_as_read()

    def mark_book_as_unread(self, *_) -> None:
        if self.app.selected_book is not None:
            self.app.selected_book.mark_as_unread()

    def jump_to_book_folder(self, *_) -> None:
        if self.app.selected_book is not None:
            self.app.selected_book.jump_to_folder()

    def get_object(self, name):
        return self.window_builder.get_object(name)

    def quit(self, action, parameter):
        """
        Quit app.
        """
        self.on_close(None)
        self.app.quit()

    def _dialog_close_callback(self, dialog):
        dialog.disconnect_by_func(self._dialog_close_callback)
        self.set_hotkeys_enabled(True)

    def show_about_window(self, *_):
        self.set_hotkeys_enabled(False)
        about = AboutWindow(self.version)
        about.connect("closed", self._dialog_close_callback)
        about.present(self.window)

    def show_preferences_window(self, *_):
        self.set_hotkeys_enabled(False)
        prefs = PreferencesWindow()
        prefs.connect("closed", self._dialog_close_callback)
        prefs.present(self.window)

    def block_ui_buttons(self, block, scan=False):
        """
        Makes the buttons to interact with the player insensitive.
        :param block: Boolean
        """
        sensitive = not block
        try:
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
        if (
            self.navigation_view.props.visible_page != "book_overview"
            and self.main_stack.props.visible_child_name != "welcome"
        ):
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

    def __on_hide_read(self, action, value):
        """
        Hide read books from the library view.
        """
        action.set_state(value)
        self.application_settings.hide_read = value.get_boolean()

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

        self._save_window_size()

        self._player.destroy()

        close_db()

        report.close()

        log.info("Saving settings.")
        self._gio_settings.apply()
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

    def _save_window_size(self, *_):
        width, height = self.window.get_default_size()
        self.application_settings.window_width = width
        self.application_settings.window_height = height
        self.application_settings.window_maximize = self.window.is_maximized()
