import logging
import os
from collections import defaultdict
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
from cozy.ui.library_view import LibraryView
from cozy.ui.preferences_view import PreferencesView
from cozy.view_model.settings_view_model import SettingsViewModel

log = logging.getLogger("ui")


class CozyUI(EventSender, metaclass=Singleton):
    """
    CozyUI is the main ui class.
    """
    # Is currently an dialog open?
    is_initialized = False
    __inhibit_cookie = None
    fs_monitor = inject.attr(fs_monitor.FilesystemMonitor)
    application_settings = inject.attr(ApplicationSettings)
    _importer: Importer = inject.attr(Importer)
    _settings: SettingsModel = inject.attr(SettingsModel)
    _files: Files = inject.attr(Files)
    _player: Player = inject.attr(Player)
    _settings_view_model: SettingsViewModel = inject.attr(SettingsViewModel)

    def __init__(self, pkgdatadir, app, version):
        super().__init__()
        self.pkgdir = pkgdatadir
        self.app = app
        self.version = version

        self._library_view: LibraryView = None

    def activate(self, library_view: LibraryView):
        self.__init_window()
        self.__init_actions()
        self.__init_components()

        self._library_view = library_view

        self.auto_import()
        self.check_for_tracks()

        self.is_initialized = True

    def startup(self):
        self.__init_resources()

    def __init_resources(self):
        """
        Initialize all resources like gresource and glade windows.
        """
        resource = Gio.resource_load(
            os.path.join(self.pkgdir, 'com.github.geigi.cozy.ui.gresource'))
        Gio.Resource._register(resource)

        resource = Gio.resource_load(
            os.path.join(self.pkgdir, 'com.github.geigi.cozy.img.gresource'))
        Gio.Resource._register(resource)

        self.appdata_resource = Gio.resource_load(
            os.path.join(self.pkgdir, 'com.github.geigi.cozy.appdata.gresource'))
        Gio.Resource._register(self.appdata_resource)

        self.window_builder = Gtk.Builder.new_from_resource(
            "/com/github/geigi/cozy/main_window.ui")

        self.window: Gtk.Window = self.window_builder.get_object("app_window")

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

        self.no_media_file_chooser = self.window_builder.get_object("no_media_file_chooser")
        self.no_media_file_chooser.connect("clicked", self._open_audiobook_dir_selector)

        self.window.present()

    def __init_actions(self):
        """
        Init all app actions.
        """

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.about)
        self.app.add_action(about_action)
        self.app.set_accels_for_action("app.about", ["F1"])

        self.create_action("about", self.about)
        self.create_action("quit", self.quit, ["<primary>q", "<primary>w"])
        self.create_action("prefs", self.show_prefs, ["<primary>comma"])
        self.create_action("scan", self.scan)
        self.play_pause_action = self.create_action("play_pause", self.play_pause, ["space"])

        self.hide_offline_action = Gio.SimpleAction.new_stateful(
            "hide_offline", None, GLib.Variant.new_boolean(self.application_settings.hide_offline)
        )
        self.hide_offline_action.connect("change-state", self.__on_hide_offline)
        self.app.add_action(self.hide_offline_action)

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

    def __init_components(self):
        if not self._player.loaded_book:
            self.block_ui_buttons(True)

        self._importer.add_listener(self._on_importer_event)

    def get_object(self, name):
        return self.window_builder.get_object(name)

    def quit(self, action, parameter):
        """
        Quit app.
        """
        self.on_close(None)
        self.app.quit()

    def _get_contributors(self):
        authors_file = self.appdata_resource.lookup_data("/com/github/geigi/cozy/authors", Gio.ResourceLookupFlags.NONE)

        current_section = ""
        result = defaultdict(list)
        for line in authors_file.get_data().decode().splitlines():
            if line.startswith("#"):
                current_section = line[1:].strip().lower()
            elif line.startswith("-"):
                result[current_section].append(line[1:].strip())

        return result

    def about(self, *junk):
        """
        Show about window.
        """
        about = Adw.AboutWindow.new_from_appdata(
            "/com/github/geigi/cozy/com.github.geigi.cozy.appdata.xml",
            release_notes_version=self.version,
        )

        contributors = self._get_contributors()
        about.set_developers(sorted(contributors["code"]))
        about.set_designers(sorted(contributors["design"]))
        about.set_artists(sorted(contributors["icon"]))

        about.set_license_type(Gtk.License.GPL_3_0)

        about.add_acknowledgement_section(
            _("Patreon Supporters"),
            ["Fred Warren", "Gabriel", "Hu Mann", "Josiah", "Oleksii Kriukov"]
        )
        about.add_acknowledgement_section(
            _("m4b chapter support in mutagen"),
            ("mweinelt",),
        )
        about.add_acknowledgement_section(
            _("Open Source Projects"),
            ("Lollypop music player https://gitlab.gnome.org/World/lollypop",),
        )

        # Translators: Replace "translator-credits" with your names, one name per line
        about.set_translator_credits(_("translator-credits"))
        about.add_legal_section("python-inject", "© 2010 Ivan Korobkov", Gtk.License.APACHE_2_0)

        about.set_transient_for(self.window)
        about.present()

    def show_prefs(self, *_):
        """
        Show preferences window.
        """
        PreferencesView().present()

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
        if self.navigation_view.props.visible_page != "book_overview" and self.main_stack.props.visible_child_name != "no_media":
            self.navigation_view.pop_to_page("main")
        if self._player.loaded_book:
            self.block_ui_buttons(False, True)
        else:
            # we want to only block the player controls
            self.block_ui_buttons(False, True)
            self.block_ui_buttons(True, False)
        self.emit_event_main_thread("working", False)

    def check_for_tracks(self):
        """
        Check if there are any imported files.
        If there aren't display a welcome screen.
        """
        if books().count() < 1:
            self.block_ui_buttons(True)

    def _open_audiobook_dir_selector(self, __):
        path = ""
        if len(self._settings.storage_locations) > 0:
            path = self._settings.default_location.path

        location_chooser = Gtk.FileDialog(title=_("Set Audiobooks Directory"))
        location_chooser.select_folder(self.window, None, self._location_chooser_open_callback)

    def _location_chooser_open_callback(self, dialog, result):
        try:
            file = dialog.select_folder_finish(result)
        except GLib.GError:
            pass
        else:
            if file is not None:
                self._set_audiobook_path(file.get_path())

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

    def _set_audiobook_path(self, path):
        self._settings_view_model.add_first_storage_location(path)
        self.main_stack.props.visible_child_name = "import"
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

