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
from cozy.search_results import BookSearchResult, ArtistSearchResult
from cozy.file_not_found_dialog import FileNotFoundDialog

import cozy.db as db
import cozy.importer as importer
import cozy.player as player

import os

import logging
log = logging.getLogger("ui")


class CozyUI:
    """
    CozyUI is the main ui class.
    """
    current_book = None
    play_status_updater = None
    sleep_timer = None
    progress_scale_clicked = False
    is_elementary = False
    current_timer_time = 0
    current_book_element = None
    current_track_element = None
    dialog_open = False
    speed = 1.0
    is_playing = False

    def __init__(self, pkgdatadir, app, version):
        self.pkgdir = pkgdatadir
        self.app = app
        self.version = version

    def activate(self):
        self.__first_play = True

        self.__init_window()
        self.__init_bindings()

        self.auto_import()
        self.refresh_content()
        self.check_for_tracks()
        self.__load_last_book()

    def startup(self):
        self.__check_current_distro()
        self.__init_resources()
        self.__init_css()
        self.__init_actions()
        self.__init_search()

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

        self.settings = Gio.Settings.new("com.github.geigi.cozy")

        self.window_builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/main_window.ui")
        self.search_builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/search_popover.ui")
        self.speed_builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/playback_speed_popover.ui")
        self.timer_builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/timer_popover.ui")
        self.settings_builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/settings.ui")
        self.menu_builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/app_menu.ui")
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

    def __check_current_distro(self):
        """
        Currently we are only checking for elementaryOS
        """
        log.debug(platform.dist())
        if '"elementary"' in platform.dist():
            self.is_elementary = True
        else:
            self.is_elementary = False

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
        if not Gtk.get_minor_version() > 18:
            self.window.connect("check-resize", self.__window_resized)

        # hide wip stuff
        self.search_popover = self.search_builder.get_object("search_popover")
        timer_popover = self.timer_builder.get_object("timer_popover")

        self.timer_switch = self.timer_builder.get_object("timer_switch")
        self.timer_scale = self.timer_builder.get_object("timer_scale")
        self.timer_spinner = self.timer_builder.get_object("timer_spinner")
        self.timer_buffer = self.timer_builder.get_object("timer_buffer")
        self.cover_img = self.window_builder.get_object("cover_img")
        self.throbber = self.window_builder.get_object("spinner")
        self.author_box = self.window_builder.get_object("author_box")
        self.reader_box = self.window_builder.get_object("reader_box")
        self.book_box = self.window_builder.get_object("book_box")
        self.book_scroller = self.window_builder.get_object("book_scroller")
        self.sort_stack = self.window_builder.get_object("sort_stack")
        self.sort_box = self.window_builder.get_object("sort_box")
        self.progress_bar = self.window_builder.get_object("progress_bar")
        self.update_progress_bar = self.window_builder.get_object(
            "update_progress_bar")
        self.import_box = self.window_builder.get_object("import_box")
        self.position_box = self.window_builder.get_object("position_box")
        self.location_chooser = self.settings_builder.get_object(
            "location_chooser")
        self.status_stack = self.window_builder.get_object("status_stack")
        self.status_label = self.window_builder.get_object("status_label")
        self.play_button = self.window_builder.get_object("play_button")
        self.prev_button = self.window_builder.get_object("prev_button")
        self.main_stack = self.window_builder.get_object("main_stack")
        self.play_img = self.window_builder.get_object("play_img")
        self.pause_img = self.window_builder.get_object("pause_img")
        self.title_label = self.window_builder.get_object("title_label")
        self.subtitle_label = self.window_builder.get_object("subtitle_label")
        self.progress_scale = self.window_builder.get_object("progress_scale")
        self.current_label = self.window_builder.get_object("current_label")
        self.remaining_label = self.window_builder.get_object(
            "remaining_label")
        self.author_toggle_button = self.window_builder.get_object(
            "author_toggle_button")
        self.reader_toggle_button = self.window_builder.get_object(
            "reader_toggle_button")
        self.no_media_file_chooser = self.window_builder.get_object(
            "no_media_file_chooser")
        self.cover_img_box = self.window_builder.get_object("cover_img_box")
        self.timer_image = self.window_builder.get_object("timer_image")
        self.search_button = self.window_builder.get_object("search_button")
        self.timer_button = self.window_builder.get_object("timer_button")
        self.auto_scan_switch = self.window_builder.get_object(
            "auto_scan_switch")
        self.settings.bind("autoscan", self.auto_scan_switch,
                           "active", Gio.SettingsBindFlags.DEFAULT)

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

        # init popovers
        self.search_button.set_popover(self.search_popover)
        self.timer_button.set_popover(timer_popover)
        self.timer_switch.connect(
            "notify::active", self.__timer_switch_changed)

        # init playback speed
        self.playback_speed_scale = self.speed_builder.get_object(
            "playback_speed_scale")
        self.playback_speed_scale.add_mark(1.0, Gtk.PositionType.RIGHT, None)
        self.playback_speed_scale.set_increments(0.02, 0.05)
        self.playback_speed_scale.connect(
            "value-changed", self.__set_playback_speed)
        self.playback_speed_label = self.speed_builder.get_object(
            "playback_speed_label")

        self.playback_speed_button = self.window_builder.get_object(
            "playback_speed_button")
        playback_speed_popover = self.speed_builder.get_object("speed_popover")
        self.playback_speed_button.set_popover(playback_speed_popover)

        # init search
        self.search_book_label = self.search_builder.get_object("book_label")
        self.search_track_label = self.search_builder.get_object("track_label")
        self.search_author_label = self.search_builder.get_object(
            "author_label")
        self.search_reader_label = self.search_builder.get_object(
            "reader_label")
        self.search_reader_box = self.search_builder.get_object(
            "reader_result_box")
        self.search_author_box = self.search_builder.get_object(
            "author_result_box")
        self.search_book_box = self.search_builder.get_object(
            "book_result_box")
        self.search_track_box = self.search_builder.get_object(
            "track_result_box")
        self.search_entry = self.search_builder.get_object("search_entry")
        self.search_scroller = self.search_builder.get_object(
            "search_scroller")
        self.search_book_separator = self.search_builder.get_object(
            "book_separator")
        self.search_author_separator = self.search_builder.get_object(
            "author_separator")
        self.search_reader_separator = self.search_builder.get_object(
            "reader_separator")
        self.search_stack = self.search_builder.get_object("search_stack")

        self.search_entry.connect("search-changed", self.__on_search_changed)

        if Gtk.get_minor_version() > 20:
            self.search_scroller.set_max_content_width(400)
            self.search_scroller.set_max_content_height(600)
            self.search_scroller.set_propagate_natural_height(True)
            self.search_scroller.set_propagate_natural_width(True)

        # add marks to timer scale
        for i in range(0, 181, 15):
            self.timer_scale.add_mark(i, Gtk.PositionType.RIGHT, None)

        # this is required otherwise the timer will not show "min" on start
        self.__init_timer_buffer()
        # timer SpinButton text format
        self.timer_spinner.connect("value-changed", self.__on_timer_changed)
        self.timer_spinner.connect(
            "focus-out-event", self.__on_timer_focus_out)

        # init progress scale
        self.progress_scale.set_increments(30.0, 60.0)
        self.progress_scale.connect(
            "button-release-event", self.__on_progress_clicked)
        self.progress_scale.connect(
            "button-press-event", self.__on_progress_press)
        self.progress_scale.connect(
            "key-press-event", self.__on_progress_key_pressed)
        self.progress_scale.connect("value-changed", self.__update_ui_time)

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
        self.play_button.connect("clicked", self.__on_play_pause_clicked)
        self.prev_button.connect("clicked", self.__on_rewind_clicked)
        self.author_toggle_button.connect("toggled", self.__toggle_author)
        self.reader_toggle_button.connect("toggled", self.__toggle_reader)

        # volume button
        self.volume_button = self.window_builder.get_object("volume_button")
        self.volume_button.connect("value-changed", self.__on_volume_changed)

        # hide remaining and current labels
        self.current_label.set_visible(False)
        self.remaining_label.set_visible(False)

        # menu
        menu = self.menu_builder.get_object("app_menu")
        self.menu_button = self.window_builder.get_object("menu_button")
        self.menu_button.set_menu_model(menu)

        if self.is_elementary:
            self.cover_img_box.props.width_request = 28
            self.cover_img_box.props.height_request = 28
            about_close_button = self.about_builder.get_object(
                "button_box").get_children()[2]
            about_close_button.connect("clicked", self.__about_close_clicked)

        player.add_player_listener(self.__player_changed)

    def __init_actions(self):
        """
        Init all app actions.
        """
        self.accel = Gtk.AccelGroup()

        #menu = self.menu_builder.get_object("app_menu")
        # self.app.set_app_menu(menu)

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
        self.settings.bind("symlinks", sl_switch, "active",
                           Gio.SettingsBindFlags.DEFAULT)

        auto_scan_switch = self.settings_builder.get_object("auto_scan_switch")
        self.settings.bind("autoscan", auto_scan_switch,
                           "active", Gio.SettingsBindFlags.DEFAULT)

        timer_suspend_switch = self.settings_builder.get_object(
            "timer_suspend_switch")
        self.settings.bind("suspend", timer_suspend_switch,
                           "active", Gio.SettingsBindFlags.DEFAULT)

        replay_switch = self.settings_builder.get_object("replay_switch")
        self.settings.bind("replay", replay_switch, "active",
                           Gio.SettingsBindFlags.DEFAULT)

    def __init_timer_buffer(self):
        """
        Add "min" to the timer text field on startup.
        """
        value = self.settings.get_int("timer")
        adjustment = self.timer_spinner.get_adjustment()
        adjustment.set_value(value)

        text = str(int(value)) + " " + _("min")
        self.timer_buffer.set_text(text, len(text))

        return True

    def __init_search(self):
        self.search_thread = Thread(target=self.search)
        self.search_thread_stop = threading.Event()

    def __load_last_book(self):
        """
        Loads the last book into the player
        """
        player.load_last_book()
        if db.Settings.get().last_played_book is not None:
            self.__update_track_ui()
            self.__update_ui_time(self.progress_scale)
            cur_m, cur_s = player.get_current_duration_ui()
            self.progress_scale.set_value(cur_m * 60 + cur_s)

            pos = int(player.get_current_track().position)
            if self.settings.get_boolean("replay"):
                log.info("Replaying the previous 30 seconds.")
                amount = 30 * 1000000000
                if (pos < amount):
                    pos = 0
                else:
                    pos = pos - amount
            self.progress_scale.set_value(int(pos / 1000000000))

    def help(self, action, parameter):
        """
        Show app help.
        """
        webbrowser.open("https://github.com/geigi/cozy/issues", new=2)

    def quit(self, action, parameter):
        """
        Quit app.
        """
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
            self.__track_changed()
        self.play_button.set_image(self.pause_img)
        self.__set_play_status_updater(True)
        self.current_book_element.set_playing(True)

    def pause(self):
        self.play_button.set_image(self.play_img)
        self.__set_play_status_updater(False)
        self.current_book_element.set_playing(False)

    def block_ui_buttons(self, block, scan=False):
        """
        Makes the buttons to interact with the player insensetive.
        :param block: Boolean
        """
        sensitive = not block
        self.play_button.set_sensitive(sensitive)
        self.volume_button.set_sensitive(sensitive)
        self.prev_button.set_sensitive(sensitive)
        self.timer_button.set_sensitive(sensitive)
        self.playback_speed_button.set_sensitive(sensitive)

        if scan:
            self.scan_action.set_enabled(sensitive)
            self.location_chooser.set_sensitive(sensitive)
            self.search_button.set_sensitive(sensitive)

    def stop(self):
        """
        Remove all information about a playing book from the ui.
        """
        self.play_button.set_image(self.play_img)
        self.__set_play_status_updater(False)

        self.title_label.set_text("")
        self.subtitle_label.set_text("")

        self.cover_img.set_from_pixbuf(None)

        self.progress_scale.set_range(0, 0)
        self.progress_scale.set_range(0, 0)
        self.progress_scale.set_visible(False)

        self.remaining_label.set_visible(False)
        self.current_label.set_visible(False)

        self.block_ui_buttons(True)

        self.progress_scale.set_sensitive(False)
        if self.current_book_element is not None:
            self.current_book_element.set_playing(False)

    def switch_to_working(self, message, first):
        """
        Switch the UI state to working.
        This is used for example when an import is currently happening.
        This blocks the user from doing some stuff like starting playback.
        """
        self.throbber.start()
        self.status_label.set_text(message)
        self.block_ui_buttons(True, True)
        if not first:
            self.update_progress_bar.set_fraction(0)
            self.status_stack.props.visible_child_name = "working"

    def switch_to_playing(self):
        """
        Switch the UI state back to playing.
        This enables all UI functionality for the user.
        """
        self.main_stack.props.visible_child_name = "main"
        self.status_stack.props.visible_child_name = "playback"
        self.block_ui_buttons(True, False)
        self.throbber.stop()

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
            self.progress_scale.set_visible(False)
        else:
            self.main_stack.props.visible_child_name = "main"
            self.search_button.set_sensitive(True)

    def set_title_cover(self, pixbuf):
        """
        Sets the cover in the title bar.
        """
        self.cover_img.set_from_pixbuf(pixbuf)
        self.cover_img.set_tooltip_text(player.get_current_track().book.name)

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
        if self.settings.get_boolean("autoscan"):
            self.scan(None, False)

    def search(self, user_search):
        """
        Perform a search with the current search entry
        """
        # we need the main context to call methods in the main thread after the search is finished
        main_context = GLib.MainContext.default()

        books = db.search_books(user_search)
        if self.search_thread_stop.is_set():
            return
        main_context.invoke_full(
            GLib.PRIORITY_DEFAULT, self.__on_book_search_finished, books)

        authors = db.search_authors(user_search)
        if self.search_thread_stop.is_set():
            return
        main_context.invoke_full(
            GLib.PRIORITY_DEFAULT, self.__on_author_search_finished, authors)

        readers = db.search_readers(user_search)
        if self.search_thread_stop.is_set():
            return
        main_context.invoke_full(
            GLib.PRIORITY_DEFAULT, self.__on_reader_search_finished, readers)

        if readers.count() < 1 and authors.count() < 1 and books.count() < 1:
            main_context.invoke_full(
                GLib.PRIORITY_DEFAULT, self.search_stack.set_visible_child_name, "nothing")

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

    def display_failed_imports(self, files):
        """
        Displays a dialog with a list of files that could not be imported.
        """
        dialog = ImportFailedDialog(files, self)
        dialog.show()

    def __jump_to_author(self, book):
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
        self.__close_search_popover()

    def __jump_to_reader(self, book):
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
        self.__close_search_popover()

    def __close_search_popover(self, object=None):
        """
        Close the search popover specific to the used gtk version.
        """
        if Gtk.get_minor_version() < 22:
            self.search_popover.hide()
        else:
            self.search_popover.popdown()

    def __on_timer_changed(self, spinner):
        """
        Add "min" to the timer text box on change.
        """
        if not self.timer_switch.get_active():
            self.timer_switch.set_active(True)

        adjustment = self.timer_spinner.get_adjustment()
        value = adjustment.get_value()

        if self.sleep_timer is not None and not self.sleep_timer.is_running:
            self.settings.set_int("timer", int(value))

        self.current_timer_time = value * 60

        text = str(int(value)) + " " + _("min")
        self.timer_buffer.set_text(text, len(text))

    def __timer_switch_changed(self, sender, widget):
        """
        Start/Stop the sleep timer object.
        """
        if self.timer_switch.get_active():
            self.timer_image.set_from_icon_name(
                "timer-on-symbolic", Gtk.IconSize.BUTTON)
            if player.get_gst_player_state() == Gst.State.PLAYING:
                self.__start_sleep_timer()
        else:
            self.timer_image.set_from_icon_name(
                "timer-off-symbolic", Gtk.IconSize.BUTTON)
            if self.sleep_timer is not None:
                self.sleep_timer.stop()

    def __on_timer_focus_out(self, event, widget):
        """
        Do not propagate event further.
        This fixes the disappearing ' min' after the spin button looses focus.
        """
        return True

    def __start_sleep_timer(self):
        """
        Start the sleep timer but only when it is enabled by the user.
        """
        if self.timer_switch.get_active():
            # Enable Timer
            adjustment = self.timer_spinner.get_adjustment()
            countdown = int(adjustment.get_value())
            self.sleep_timer = RepeatedTimer(1, self.__sleep_timer_fired)
            self.sleep_timer.start()
            self.current_timer_time = countdown * 60

    def __pause_sleep_timer(self):
        """
        Stop the sleep timer.
        """
        if self.sleep_timer is not None:
            self.sleep_timer.stop()

    def __sleep_timer_fired(self):
        """
        The sleep timer gets called every second. Here we do the countdown stuff
        aswell as stop the playback / suspend the machine.
        """
        self.current_timer_time = self.current_timer_time - 1
        adjustment = self.timer_spinner.get_adjustment()
        adjustment.set_value(int(self.current_timer_time / 60) + 1)
        if self.current_timer_time < 1:
            self.timer_switch.set_active(False)
            if player.get_gst_player_state() == Gst.State.PLAYING:
                player.play_pause(None)

            self.sleep_timer.stop()

    def __on_progress_press(self, widget, sender):
        """
        Remember that progress scale is clicked so it won't get updates from the player.
        """
        self.progress_scale_clicked = True

        # If the user drags the slider we don't want to jump back
        # another 30 seconds on first play
        if self.__first_play:
            self.__first_play = False

        return False

    def __on_progress_clicked(self, widget, sender):
        """
        Jump to the slided time and release the progress scale update lock.
        """
        player.jump_to(self.progress_scale.get_value())
        self.progress_scale_clicked = False

        return False

    def __on_drag_data_received(self, widget, context, x, y, selection, target_type, timestamp):
        """
        We want to import the files that are dragged onto the window.
        inspired by https://stackoverflow.com/questions/24094186/drag-and-drop-file-example-in-pygobject
        """
        if target_type == 80:
            self.throbber.start()
            self.switch_to_working("copying new files...", False)
            thread = Thread(target=importer.copy, args=(self, selection, ))
            thread.start()

    def __on_progress_key_pressed(self, widget, event):
        """
        Jump to the modified time.
        """
        old_val = self.progress_scale.get_value()
        if event.keyval == Gdk.KEY_Up or event.keyval == Gdk.KEY_Left:
            if old_val > 30.0:
                player.jump_to(old_val - 30)
            else:
                player.jump_to(0)
        elif event.keyval == Gdk.KEY_Down or event.keyval == Gdk.KEY_Right:
            upper = self.progress_scale.get_adjustment().get_upper()
            if old_val + 30.0 < upper:
                player.jump_to(old_val + 30)
            else:
                player.jump_to(upper)

        return False

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
        self.throbber.start()
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

    def __on_play_pause_clicked(self, button):
        """
        Play/Pause the player.
        """
        player.play_pause(None)
        pos = player.get_current_track().position
        if self.__first_play:
            self.__first_play = False

            if self.settings.get_boolean("replay"):
                amount = 30 * 1000000000
                if pos < amount:
                    pos = 0
                else:
                    pos = pos - amount
        player.jump_to_ns(pos)

    def __on_rewind_clicked(self, button):
        """
        Jump back 30 seconds.
        """
        player.rewind(30)
        if self.progress_scale.get_value() > 30:
            self.progress_scale.set_value(self.progress_scale.get_value() - 30)
        else:
            self.progress_scale.set_value(0)

    def __on_search_changed(self, sender):
        """
        Reset the search if running and start a new async search.
        """
        self.search_thread_stop.set()
        self.throbber.start()

        # we want to avoid flickering of the search box size
        # as we remove widgets and add them again
        # so we get the current search popup size and set it as
        # the preferred size until the search is finished
        # this helps only a bit, the widgets are still flickering
        self.search_popover.set_size_request(self.search_popover.get_allocated_width(),
                                             self.search_popover.get_allocated_height())

        # hide nothing found
        self.search_stack.set_visible_child_name("main")

        # First clear the boxes
        self.__remove_all_children(self.search_book_box)
        self.__remove_all_children(self.search_author_box)
        self.__remove_all_children(self.search_reader_box)

        # Hide all the labels & separators
        self.search_book_label.set_visible(False)
        self.search_author_label.set_visible(False)
        self.search_reader_label.set_visible(False)
        self.search_book_separator.set_visible(False)
        self.search_author_separator.set_visible(False)
        self.search_reader_separator.set_visible(False)
        self.search_track_label.set_visible(False)

        user_search = self.search_entry.get_text()
        if user_search:
            if self.search_thread.is_alive():
                self.search_thread.join(timeout=0.2)
            self.search_thread_stop.clear()
            self.search_thread = Thread(
                target=self.search, args=(user_search, ))
            self.search_thread.start()
        else:
            self.throbber.stop()
            self.search_stack.set_visible_child_name("start")
            self.search_popover.set_size_request(-1, -1)

    def __on_book_search_finished(self, books):
        """
        This gets called after the book search is finished.
        It adds all the results to the gui.
        :param books: Result peewee query containing the books
        """
        if len(books) > 0:
            self.search_stack.set_visible_child_name("main")
            self.search_book_label.set_visible(True)
            self.search_book_separator.set_visible(True)

            for book in books:
                if self.search_thread_stop.is_set():
                    return
                self.search_book_box.add(BookSearchResult(
                    book, self.__close_search_popover))

    def __on_author_search_finished(self, authors):
        """
        This gets called after the author search is finished.
        It adds all the results to the gui.
        :param authors: Result peewee query containing the authors
        """
        if len(authors) > 0:
            self.search_stack.set_visible_child_name("main")
            self.search_author_label.set_visible(True)
            self.search_author_separator.set_visible(True)

            for author in authors:
                if self.search_thread_stop.is_set():
                    return
                self.search_author_box.add(ArtistSearchResult(
                    self.__jump_to_author, author, True))

    def __on_reader_search_finished(self, readers):
        """
        This gets called after the reader search is finished.
        It adds all the results to the gui.
        It also resets the gui to a state before the search.
        :param readers: Result peewee query containing the readers
        """
        if len(readers) > 0:
            self.search_stack.set_visible_child_name("main")
            self.search_reader_label.set_visible(True)
            self.search_reader_separator.set_visible(True)

            for reader in readers:
                if self.search_thread_stop.is_set():
                    return
                self.search_reader_box.add(ArtistSearchResult(
                    self.__jump_to_reader, reader, False))

        # the reader search is the last that finishes
        # so we stop the throbber and reset the prefered height & width
        self.throbber.stop()
        self.search_popover.set_size_request(-1, -1)

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

    def __update_track_ui(self):
        # set data of new stream in ui
        track = player.get_current_track()
        self.title_label.set_text(track.book.name)
        self.subtitle_label.set_text(track.name)
        self.block_ui_buttons(False, True)
        self.progress_scale.set_sensitive(True)
        self.progress_scale.set_visible(True)

        # only change cover when book has changed
        if self.current_book is not track.book:
            self.current_book = track.book
            if self.is_elementary:
                size = 28
            else:
                size = 40
            self.set_title_cover(db.get_cover_pixbuf(track.book, size))

        total = player.get_current_track().length
        self.progress_scale.set_range(0, total)
        self.progress_scale.set_value(int(track.position / 1000000000))
        self.__update_ui_time(None)

    def __update_time(self):
        """
        Update the current and remaining time.
        """
        if not self.progress_scale_clicked:
            cur_m, cur_s = player.get_current_duration_ui()
            Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE,
                                 self.progress_scale.set_value, cur_m * 60 + cur_s)

    def __update_ui_time(self, widget):
        """
        Displays the value of the progress slider in the text boxes as time.
        """
        val = int(self.progress_scale.get_value())
        m, s = divmod(val, 60)
        self.current_label.set_markup(
            "<tt><b>" + str(m).zfill(2) + ":" + str(s).zfill(2) + "</b></tt>")
        track = player.get_current_track()

        if track is not None:
            remaining_secs = int(track.length - val)
            remaining_mins, remaining_secs = divmod(remaining_secs, 60)

            self.remaining_label.set_markup(
                "<tt><b>" + str(remaining_mins).zfill(2) + ":" + str(remaining_secs).zfill(2) + "</b></tt>")

    def __set_play_status_updater(self, enable):
        """
        Starts/stops the play status ui update timer.
        Restarts if enable is True and the timer is already running.
        :params enable: Boolean
        """
        if self.play_status_updater is not None:
            self.play_status_updater.stop()
            self.play_status_updater = None

        if enable and self.is_playing:
            self.play_status_updater = RepeatedTimer(
                1.0 / self.speed, self.__update_time)
            self.play_status_updater.start()

    def __set_playback_speed(self, widget):
        """
        Set the playback speed.
        Update playback speed label.
        """
        self.speed = round(self.playback_speed_scale.get_value(), 2)
        self.playback_speed_label.set_text(str(round(self.speed, 1)) + " x")
        player.set_playback_speed(self.speed)
        self.__set_play_status_updater(True)

    def __track_changed(self):
        """
        The track loaded in the player has changed.
        Refresh the currently playing track and mark it in the track overview popover.
        """
        if self.current_track_element is not None:
            self.current_track_element.play_img.set_from_icon_name(
                "media-playback-start-symbolic", Gtk.IconSize.SMALL_TOOLBAR)

        if self.current_book_element is not None:
            self.current_book_element.set_playing(False)

        curr_track = player.get_current_track()
        self.current_book_element = next(
            filter(
                lambda x: x.get_children()[0].book.id == curr_track.book.id,
                self.book_box.get_children()), None).get_children()[0]
        self.current_track_element = next(
            filter(
                lambda x: x.track.id == curr_track.id,
                self.current_book_element.track_box.get_children()), None)

        self.current_track_element.play_img.set_from_icon_name(
            "media-playback-start-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        self.current_book_element._mark_current_track()
        self.remaining_label.set_visible(True)
        self.current_label.set_visible(True)

    def __player_changed(self, event, message):
        """
        Listen to and handle all gst player messages that are important for the ui.
        """
        if event == "stop":
            self.is_playing = False
            self.stop()
            self.__pause_sleep_timer()
        elif event == "play":
            self.is_playing = True
            self.play()
            self.__start_sleep_timer()
            self.current_track_element.play_img.set_from_icon_name(
                "media-playback-pause-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        elif event == "pause":
            self.is_playing = False
            self.pause()
            self.__pause_sleep_timer()
            self.current_track_element.play_img.set_from_icon_name(
                "media-playback-start-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        elif event == "track-changed":
            self.__update_track_ui()
            self.__track_changed()
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
        self.progress_scale.props.width_request = value

    def __about_close_clicked(self, widget):
        self.about_dialog.hide()

    def __remove_all_children(self, container):
        """
        Removes all widgets from a gtk container.
        """
        childs = container.get_children()
        for element in childs:
            container.remove(element)
            element.destroy()

    def __on_volume_changed(self, widget, value):
        """
        Sets the ui value in the player.
        """
        player.set_volume(value)

    def on_close(self, widget, data=None):
        """
        Close and dispose everything that needs to be when window is closed.
        """
        # Stop timers
        if self.play_status_updater is not None:
            self.play_status_updater.stop()
        if self.sleep_timer is not None:
            self.sleep_timer.stop()

        # save current position when still playing
        if player.get_gst_player_state() == Gst.State.PLAYING:
            db.Track.update(position=player.get_current_duration()).where(
                db.Track.id == player.get_current_track().id).execute()
            player.stop()

        player.dispose()

    ####################
    # CONTENT HANDLING #
    ####################

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
