import platform
import webbrowser
import threading

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gio, Gdk, GLib, Gst
from threading import Thread
from cozy.book_element import BookElement
from cozy.tools import RepeatedTimer
from cozy.import_failed_dialog import ImportFailedDialog
from cozy.file_not_found_dialog import FileNotFoundDialog
from cozy.event_sender import EventSender
from cozy.search import Search
from cozy.sleep_timer import SleepTimer
from cozy.playback_speed import PlaybackSpeed
from cozy.titlebar import Titlebar

import cozy.db as db
import cozy.importer as importer
import cozy.player as player
import cozy.tools as tools

import os

import logging
log = logging.getLogger("ui")


class CozyUI:
    """
    CozyUI is the main ui class.
    """
    # The book that is currently loaded in the player
    current_book = None
    # Current book ui element
    current_book_element = None
    # Current track ui element
    current_track_element = None
    # Is currently an dialog open?
    dialog_open = False
    # Are we currently playing?
    is_playing = False
    first_play = True

    def __init__(self, pkgdatadir, app, version):
        super().__init__()
        self.pkgdir = pkgdatadir
        self.app = app
        self.version = version

    def activate(self):
        self.first_play = True

        self.__init_window()
        self.__init_bindings()
        self.__init_components()

        self.auto_import()
        self.refresh_content()
        self.check_for_tracks()
        self.__load_last_book()

    def startup(self):
        self.__init_resources()
        self.__init_css()
        self.__init_actions()

    def __init_resources(self):
        """
        Initialize all resources like gresource and glade windows.
        """
        resource = Gio.resource_load(
            os.path.join(self.pkgdir, 'cozy.ui.gresource'))
        Gio.Resource._register(resource)

        resource = Gio.resource_load(
            os.path.join(self.pkgdir, 'cozy.img.gresource'))
        Gio.Resource._register(resource)

        self.window_builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/main_window.ui")
        self.settings_builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/settings.ui")
        
        self.about_builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/about.ui")

    def __init_css(self):
        """
        Initialize the main css files and providers.
        Add css classes to the default screen style context.
        """
        if Gtk.get_minor_version() > 18:
            log.debug("Fanciest design possible")
            cssProviderFile = Gio.File.new_for_uri(
                "resource:///de/geigi/cozy/application.css")
        else:
            log.debug("Using legacy css file")
            cssProviderFile = Gio.File.new_for_uri(
                "resource:///de/geigi/cozy/application_legacy.css")
        cssProvider = Gtk.CssProvider()
        cssProvider.load_from_file(cssProviderFile)

        # add the bordered css class to the default screen for the borders around album art
        screen = Gdk.Screen.get_default()
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(
            screen, cssProvider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        styleContext.add_class("bordered")

    def __init_window(self):
        """
        Add fields for all ui objects we need to access from code.
        Initialize everything we can't do from glade like events and other stuff.
        """
        log.info("Initialize main window")
        self.window = self.window_builder.get_object("app_window")
        self.window.set_default_size(1100, 700)
        self.window.set_application(self.app)
        self.window.show_all()
        self.window.present()
        self.window.connect("delete-event", self.on_close)
        self.window.connect("drag_data_received", self.__on_drag_data_received)
        self.window.drag_dest_set(Gtk.DestDefaults.MOTION | Gtk.DestDefaults.HIGHLIGHT | Gtk.DestDefaults.DROP,
                                  [Gtk.TargetEntry.new("text/uri-list", 0, 80)], Gdk.DragAction.COPY)
        
        # resizing the progress bar for older gtk versions
        if not Gtk.get_minor_version() > 18:
            self.window.connect("check-resize", self.__window_resized)

        self.author_box = self.window_builder.get_object("author_box")
        self.reader_box = self.window_builder.get_object("reader_box")
        self.book_box = self.window_builder.get_object("book_box")
        self.book_scroller = self.window_builder.get_object("book_scroller")
        self.sort_stack = self.window_builder.get_object("sort_stack")
        self.sort_box = self.window_builder.get_object("sort_box")
        self.import_box = self.window_builder.get_object("import_box")
        self.position_box = self.window_builder.get_object("position_box")
        self.location_chooser = self.settings_builder.get_object(
            "location_chooser")
        self.main_stack = self.window_builder.get_object("main_stack")
        
        self.author_toggle_button = self.window_builder.get_object(
            "author_toggle_button")
        self.reader_toggle_button = self.window_builder.get_object(
            "reader_toggle_button")
        self.no_media_file_chooser = self.window_builder.get_object(
            "no_media_file_chooser")
        
        self.auto_scan_switch = self.window_builder.get_object(
            "auto_scan_switch")

        # get settings window
        self.settings_window = self.settings_builder.get_object(
            "settings_window")
        self.settings_window.set_transient_for(self.window)
        self.settings_window.connect("delete-event", self.hide_window)
        self.init_db_settings()

        # get about dialog
        self.about_dialog = self.about_builder.get_object("about_dialog")
        self.about_dialog.set_transient_for(self.window)
        self.about_dialog.connect("delete-event", self.hide_window)
        self.about_dialog.set_version(self.version)

        # we need to update the database when the audio book location was changed
        folder_chooser = self.settings_builder.get_object("location_chooser")
        folder_chooser.connect("file-set", self.__on_folder_changed)
        self.no_media_file_chooser.connect(
            "file-set", self.__on_no_media_folder_changed)

        # shortcuts
        self.accel = Gtk.AccelGroup()

        # sorting and filtering
        self.author_box.connect("row-activated", self.__on_listbox_changed)
        self.reader_box.connect("row-activated", self.__on_listbox_changed)
        self.book_box.set_sort_func(self.__sort_books, None, False)
        self.book_box.set_filter_func(self.__filter_books, None, False)
        self.book_box.connect("selected-children-changed",
                              self.__on_book_selec_changed)

        # button actions
        self.author_toggle_button.connect("toggled", self.__toggle_author)
        self.reader_toggle_button.connect("toggled", self.__toggle_reader)
        
        try:
            about_close_button = self.about_builder.get_object(
                "button_box").get_children()[2]
        
            if about_close_button is not None:
                about_close_button.connect("clicked", self.__about_close_clicked)
        except Exception as e:
            log.info("Not connecting about close button.")
        
        player.add_player_listener(self.__player_changed)

    def __init_actions(self):
        """
        Init all app actions.
        """
        self.accel = Gtk.AccelGroup()

        help_action = Gio.SimpleAction.new("help", None)
        help_action.connect("activate", self.help)
        self.app.add_action(help_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.about)
        self.app.add_action(about_action)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.quit)
        self.app.add_action(quit_action)
        self.app.set_accels_for_action(
            "app.quit", ["<Control>q", "<Control>w"])

        pref_action = Gio.SimpleAction.new("prefs", None)
        pref_action.connect("activate", self.show_prefs)
        self.app.add_action(pref_action)
        self.app.set_accels_for_action("app.prefs", ["<Control>comma"])

        self.scan_action = Gio.SimpleAction.new("scan", None)
        self.scan_action.connect("activate", self.scan)
        self.app.add_action(self.scan_action)

    def __init_bindings(self):
        """
        Bind Gio.Settings to widgets in settings dialog.
        """

        sl_switch = self.settings_builder.get_object("symlinks_switch")
        tools.get_glib_settings().bind("symlinks", sl_switch, "active",
                           Gio.SettingsBindFlags.DEFAULT)

        auto_scan_switch = self.settings_builder.get_object("auto_scan_switch")
        tools.get_glib_settings().bind("autoscan", auto_scan_switch,
                           "active", Gio.SettingsBindFlags.DEFAULT)

        timer_suspend_switch = self.settings_builder.get_object(
            "timer_suspend_switch")
        tools.get_glib_settings().bind("suspend", timer_suspend_switch,
                           "active", Gio.SettingsBindFlags.DEFAULT)

        replay_switch = self.settings_builder.get_object("replay_switch")
        tools.get_glib_settings().bind("replay", replay_switch, "active",
                           Gio.SettingsBindFlags.DEFAULT)

        crc32_switch = self.settings_builder.get_object("crc32_switch")
        tools.get_glib_settings().bind("use-crc32", crc32_switch, "active",
                           Gio.SettingsBindFlags.DEFAULT)

        titlebar_remaining_time_switch = self.settings_builder.get_object("titlebar_remaining_time_switch")
        self.remaining_time_eventbox = self.settings_builder.get_object("titlebar_remaining_time_eventbox")
        tools.get_glib_settings().bind("titlebar-remaining-time", titlebar_remaining_time_switch, "active",
                           Gio.SettingsBindFlags.DEFAULT)

    def __init_components(self):
        self.titlebar = Titlebar(self)

        self.sleep_timer = SleepTimer(self)
        self.speed = PlaybackSpeed(self)
        self.search = Search(self)

        self.titlebar.activate()

        self.remaining_time_eventbox.connect("button-release-event", self.titlebar._on_remaining_clicked)

    def __load_last_book(self):
        """
        Loads the last book into the player
        """
        player.load_last_book()
        self.titlebar.load_last_book()

    def get_object(self, name):
        return self.window_builder.get_object(name)

    def help(self, action, parameter):
        """
        Show app help.
        """
        webbrowser.open("https://github.com/geigi/cozy/issues", new=2)

    def quit(self, action, parameter):
        """
        Quit app.
        """
        self.on_close(None)
        self.app.quit()

    def about(self, action, parameter):
        """
        Show about window.
        """
        self.about_dialog.show()

    def show_prefs(self, action, parameter):
        """
        Show preferences window.
        """
        self.settings_window.show()

    def hide_window(self, widget, data=None):
        """
        Hide a given window. This is used for the about and settings dialog
        as they will never be closed only hidden.

        param widget: The widget that will be hidden.
        """
        widget.hide()

        # we handeled the close event so the window must not get destroyed.
        return True

    def play(self):
        if self.current_book_element is None:
            self.track_changed()
        self.current_book_element.set_playing(True)

    def pause(self):
        self.current_book_element.set_playing(False)

    def stop(self):
        """
        Remove all information about a playing book from the ui.
        """
        if self.current_book_element is not None:
            self.current_book_element.set_playing(False)

        if self.current_book_element is not None:
            self.current_book_element._mark_current_track()

    def block_ui_buttons(self, block, scan=False):
        """
        Makes the buttons to interact with the player insensetive.
        :param block: Boolean
        """
        sensitive = not block
        self.titlebar.block_ui_buttons(block, scan)
        if scan:
            self.scan_action.set_enabled(sensitive)
            self.location_chooser.set_sensitive(sensitive)

    def switch_to_working(self, message, first):
        """
        Switch the UI state to working.
        This is used for example when an import is currently happening.
        This blocks the user from doing some stuff like starting playback.
        """
        self.titlebar.switch_to_working(message, first)
        self.block_ui_buttons(True, True)

    def switch_to_playing(self):
        """
        Switch the UI state back to playing.
        This enables all UI functionality for the user.
        """
        self.titlebar.switch_to_playing()
        self.main_stack.props.visible_child_name = "main"
        self.block_ui_buttons(False, True)

    def check_for_tracks(self):
        """
        Check if there are any imported files.
        If there aren't display a welcome screen.
        """
        if db.books().count() < 1:
            self.no_media_file_chooser.set_current_folder(
                db.Settings.get().path)
            self.main_stack.props.visible_child_name = "no_media"
            self.block_ui_buttons(True)
            self.titlebar.stop()
        else:
            self.main_stack.props.visible_child_name = "main"

    def scan(self, action, first_scan):
        """
        Start the db import in a seperate thread
        """
        self.switch_to_working(_("Importing Audiobooks"), first_scan)
        thread = Thread(target=importer.update_database, args=(self, ))
        thread.start()

    def init_db_settings(self):
        """
        Display settings from the database in the ui.
        """
        chooser = self.settings_builder.get_object("location_chooser")
        chooser.set_current_folder(db.Settings.get().path)

    def auto_import(self):
        if tools.get_glib_settings().get_boolean("autoscan"):
            self.scan(None, False)

    def refresh_content(self):
        """
        Refresh all content.
        """
        # First clear the boxes
        childs = self.author_box.get_children()
        for element in childs:
            self.author_box.remove(element)

        childs = self.reader_box.get_children()
        for element in childs:
            self.reader_box.remove(element)

        childs = self.book_box.get_children()
        for element in childs:
            self.book_box.remove(element)

        # Add the special All element
        all_row = ListBoxRowWithData(_("All"), True)
        all_row.set_tooltip_text(_("Display all books"))
        self.author_box.add(all_row)
        self.author_box.select_row(all_row)
        all_row = ListBoxRowWithData(_("All"), True)
        all_row.set_tooltip_text(_("Display all books"))
        self.reader_box.add(all_row)
        self.reader_box.select_row(all_row)

        for book in db.authors():
            row = ListBoxRowWithData(book.author, False)
            self.author_box.add(row)

        for book in db.readers():
            row = ListBoxRowWithData(book.reader, False)
            self.reader_box.add(row)

        # this is required to see the new items
        self.author_box.show_all()
        self.reader_box.show_all()

        for b in db.books():
            self.book_box.add(BookElement(b, self))

        self.book_box.show_all()

        return False

    def get_playback_start_position(self):
        """
        Returns the position where to start playback of the current track.
        This checks for the automatic replay option.
        :return: Position in ns
        """
        pos = player.get_current_track().position
        if self.first_play:
            self.first_play = False

            if tools.get_glib_settings().get_boolean("replay"):
                amount = 30 * 1000000000
                if pos < amount:
                    pos = 0
                else:
                    pos = pos - amount

        return pos

    def update_book_popover_time(self):
        if self.current_book_element is not None:
            self.current_book_element.update_time()

    def display_failed_imports(self, files):
        """
        Displays a dialog with a list of files that could not be imported.
        """
        dialog = ImportFailedDialog(files, self)
        dialog.show()

    def jump_to_author(self, book):
        """
        Jump to the given book author.
        This is used from the search popover.
        """
        row = next(filter(
            lambda x: x.get_children()[0].get_text() == book.author,
            self.author_box.get_children()), None)

        self.author_toggle_button.set_active(True)
        self.__toggle_author(None)
        self.author_box.select_row(row)
        self.book_box.invalidate_filter()
        self.search.close()

    def jump_to_reader(self, book):
        """
        Jump to the given book reader.
        This is used from the search popover.
        """
        row = next(filter(
            lambda x: x.get_children()[0].get_text() == book.reader,
            self.reader_box.get_children()), None)

        self.reader_toggle_button.set_active(True)
        self.__toggle_reader(None)
        self.reader_box.select_row(row)
        self.book_box.invalidate_filter()
        self.search.close()

    def __on_drag_data_received(self, widget, context, x, y, selection, target_type, timestamp):
        """
        We want to import the files that are dragged onto the window.
        inspired by https://stackoverflow.com/questions/24094186/drag-and-drop-file-example-in-pygobject
        """
        if target_type == 80:
            self.switch_to_working("copying new files...", False)
            thread = Thread(target=importer.copy, args=(self, selection, ))
            thread.start()

    def __on_no_media_folder_changed(self, sender):
        """
        Get's called when the user changes the audiobook location from
        the no media screen. Now we want to do a first scan instead of a rebase.
        """
        location = self.no_media_file_chooser.get_file().get_path()
        db.Settings.update(path=location).execute()
        self.main_stack.props.visible_child_name = "import"
        self.scan(None, True)

    def __on_folder_changed(self, sender):
        """
        Clean the database when the audio book location is changed.
        """
        log.debug("Audio book location changed, rebasing the location in db.")
        self.location_chooser.set_sensitive(False)

        settings = db.Settings.get()
        oldPath = settings.path
        settings.path = self.location_chooser.get_file().get_path()
        settings.save()

        self.switch_to_working(_("Changing audio book location..."), False)

        thread = Thread(target=importer.rebase_location, args=(
            self, oldPath, settings.path))
        thread.start()

    def __on_book_selec_changed(self, flowbox):
        """
        Fix the overlay on the selected book.
        """
        if len(flowbox.get_selected_children()) > 0:
            selected = flowbox.get_selected_children()[0]
            for child in flowbox.get_children():
                if child == selected:
                    child.get_children()[0].selected = True
                else:
                    child.get_children()[0].selected = False
                    child.get_children()[0]._on_leave_notify(None, None)

    def __toggle_reader(self, button):
        """
        Switch to reader selection
        """
        if self.reader_toggle_button.get_active():
            self.author_toggle_button.set_active(False)
            self.sort_stack.props.visible_child_name = "reader"
            self.book_box.invalidate_filter()
        elif self.author_toggle_button.get_active() is False:
            self.reader_toggle_button.set_active(True)

    def __toggle_author(self, button):
        """
        Switch to author selection
        """
        if self.author_toggle_button.get_active():
            self.reader_toggle_button.set_active(False)
            self.sort_stack.props.visible_child_name = "author"
            self.book_box.invalidate_filter()
        elif self.reader_toggle_button.get_active() is False:
            self.author_toggle_button.set_active(True)

    def track_changed(self):
        """
        The track loaded in the player has changed.
        Refresh the currently playing track and mark it in the track overview popover.
        """
        # also reset the book playing state
        if self.current_book_element is not None:
            self.current_book_element.set_playing(False)
            self.current_book_element.select_track(None, False)

        curr_track = player.get_current_track()
        self.current_book_element = next(
            filter(
                lambda x: x.get_children()[0].book.id == curr_track.book.id,
                self.book_box.get_children()), None).get_children()[0]

        self._update_current_track_element()
        self.block_ui_buttons(False, True)

    def _update_current_track_element(self):
        """
        Updates the current track element to correctly display the play pause icons
        in the track popups after it was created.
        """
        # The track popover is only created on demand
        # when the user opens it the first time
        if self.current_book_element is None:
            return

        if self.current_book_element.popover_created is True:
            curr_track = player.get_current_track()
            self.current_book_element.select_track(curr_track, self.is_playing)

    def __player_changed(self, event, message):
        """
        Listen to and handle all gst player messages that are important for the ui.
        """
        if event == "stop":
            self.is_playing = False
            self.stop()
            self.titlebar.stop()
            self.sleep_timer.stop()
        elif event == "play":
            self.is_playing = True
            self.play()
            self.titlebar.play()
            self.sleep_timer.start()
            self.current_book_element.select_track(None, True)
        elif event == "pause":
            self.is_playing = False
            self.pause()
            self.titlebar.pause()
            self.sleep_timer.stop()
            self.current_book_element.select_track(None, False)
        elif event == "track-changed":
            self.track_changed()
        elif event == "error":
            if self.dialog_open:
                return
            if "Resource not found" in str(message):
                self.dialog_open = True
                dialog = FileNotFoundDialog(
                    player.get_current_track().file, self)
                dialog.show()

    def __window_resized(self, window):
        """
        Resize the progress scale to expand to the window size
        for older gtk versions.
        """
        width, height = self.window.get_size()
        value = width - 800
        if value < 80:
            value = 80
        self.titlebar.set_progress_scale_width(value)

    def __about_close_clicked(self, widget):
        self.about_dialog.hide()
    
    def on_close(self, widget, data=None):
        """
        Close and dispose everything that needs to be when window is closed.
        """
        self.titlebar.close()
        if self.sleep_timer.is_running():
            self.sleep_timer.stop()

        # save current position when still playing
        if player.get_gst_player_state() == Gst.State.PLAYING:
            db.Track.update(position=player.get_current_duration()).where(
                db.Track.id == player.get_current_track().id).execute()
            player.stop()

        player.dispose()

    def __on_listbox_changed(self, sender, row):
        """
        Refresh the filtering on author/reader selection.
        """
        self.book_box.invalidate_filter()

    def __sort_books(self, book_1, book_2, data, notify_destroy):
        """
        Sort books alphabetically by name.
        """
        return book_1.get_children()[0].book.name.lower() > book_2.get_children()[0].book.name.lower()

    def __filter_books(self, book, data, notify_destroy):
        """
        Filter the books in the book view according to the selected author/reader or "All".
        """
        if self.author_toggle_button.get_active():
            author = self.author_box.get_selected_row().data
            if author is None:
                return True

            if author == _("All"):
                return True
            else:
                return True if book.get_children()[0].book.author == author else False
        else:
            reader = self.reader_box.get_selected_row().data
            if reader is None:
                return True

            if reader == _("All"):
                return True
            else:
                return True if book.get_children()[0].book.reader == reader else False


class ListBoxRowWithData(Gtk.ListBoxRow):
    """
    This class represents a listboxitem for an author/reader.
    """
    MARGIN = 5

    def __init__(self, data, bold=False):
        super(Gtk.ListBoxRow, self).__init__()
        self.data = data
        label = Gtk.Label.new(data)
        if bold:
            label.set_markup("<b>" + data + "</b>")
        label.set_xalign(0.0)
        label.set_margin_top(self.MARGIN)
        label.set_margin_bottom(self.MARGIN)
        label.set_margin_start(7)
        self.add(label)
