import webbrowser

from cozy.control.db import books, authors, readers, is_external, close_db
from cozy.db.book import Book
from cozy.db.storage import Storage
from cozy.db.track import Track

from gi.repository import Gtk, Gio, Gdk, GLib, Gst
from threading import Thread
from cozy.ui.book_element import BookElement
from cozy.ui.import_failed_dialog import ImportFailedDialog
from cozy.ui.file_not_found_dialog import FileNotFoundDialog
from cozy.ui.search import Search
from cozy.control.sleep_timer import SleepTimer
from cozy.control.playback_speed import PlaybackSpeed
from cozy.ui.titlebar import Titlebar
from cozy.ui.settings import Settings
from cozy.ui.book_overview import BookOverview
from cozy.architecture.singleton import Singleton
import cozy.report.reporter as report
import cozy.control.importer as importer
import cozy.control.player as player
import cozy.tools as tools
import cozy.control.filesystem_monitor as fs_monitor
import cozy.control.offline_cache as offline_cache

import os

import logging
log = logging.getLogger("ui")


class CozyUI(metaclass=Singleton):
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
    is_initialized = False
    first_play = True
    __inhibit_cookie = None

    def __init__(self, pkgdatadir, app, version):
        super().__init__()
        self.pkgdir = pkgdatadir
        self.app = app
        self.version = version

    def activate(self):
        self.first_play = True

        self.__init_window()
        self.__init_components()

        self.auto_import()
        self.refresh_content()
        self.check_for_tracks()
        self.__load_last_book()

        self.is_initialized = True

    def startup(self):
        self.__init_resources()
        self.__init_css()
        self.__init_actions()
        report.info("main", "startup")

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

        self.window_builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/main_window.ui")

        self.about_builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/about.ui")

    def __init_css(self):
        """
        Initialize the main css files and providers.
        Add css classes to the default screen style context.
        """
        main_cssProviderFile = Gio.File.new_for_uri(
            "resource:///de/geigi/cozy/application.css")
        main_cssProvider = Gtk.CssProvider()
        main_cssProvider.load_from_file(main_cssProviderFile)

        if Gtk.get_minor_version() > 18:
            log.debug("Fanciest design possible")
            cssProviderFile = Gio.File.new_for_uri(
                "resource:///de/geigi/cozy/application_default.css")
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
            screen, main_cssProvider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        styleContext.add_provider_for_screen(
            screen, cssProvider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        styleContext.add_class("bordered")

    def __init_window(self):
        """
        Add fields for all ui objects we need to access from code.
        Initialize everything we can't do from glade like events and other stuff.
        """
        log.info("Initialize main window")
        self.window: Gtk.Window = self.window_builder.get_object("app_window")
        self.window.set_default_size(1100, 700)
        self.window.set_application(self.app)
        self.window.show_all()
        self.window.present()
        self.window.connect("delete-event", self.on_close)
        self.window.connect("drag_data_received", self.__on_drag_data_received)
        self.window.drag_dest_set(Gtk.DestDefaults.MOTION | Gtk.DestDefaults.HIGHLIGHT | Gtk.DestDefaults.DROP,
                                  [Gtk.TargetEntry.new("text/uri-list", 0, 80)], Gdk.DragAction.COPY)
        self.window.title = "Cozy"

        # resizing the progress bar for older gtk versions
        if not Gtk.get_minor_version() > 18:
            self.window.connect("check-resize", self.__window_resized)

        self.author_box = self.window_builder.get_object("author_box")
        self.reader_box = self.window_builder.get_object("reader_box")
        self.book_box = self.window_builder.get_object("book_box")
        self.book_scroller = self.window_builder.get_object("book_scroller")
        self.sort_stack = self.window_builder.get_object("sort_stack")
        self.sort_stack.connect("notify::visible-child",
                                self.__on_sort_stack_changed)
        self.sort_box = self.window_builder.get_object("sort_box")
        self.import_box = self.window_builder.get_object("import_box")
        self.position_box = self.window_builder.get_object("position_box")
        self.main_stack = self.window_builder.get_object("main_stack")
        self.toolbar_revealer = self.window_builder.get_object("toolbar_revealer")
        self.back_button = self.window_builder.get_object("back_button")
        self.back_button.connect("clicked", self.__on_back_clicked)

        self.category_toolbar = self.window_builder.get_object(
            "category_toolbar")

        self.sort_stack_revealer = self.window_builder.get_object(
            "sort_stack_revealer")
        # This fixes a bug where otherwise expand is
        # somehow set to true internally
        # but is still showing false in the inspector
        self.sort_stack_revealer.props.expand = True
        self.sort_stack_revealer.props.expand = False

        self.sort_stack_switcher = self.window_builder.get_object(
            "sort_stack_switcher")
        self.no_media_file_chooser = self.window_builder.get_object(
            "no_media_file_chooser")
        self.no_media_file_chooser.connect(
            "file-set", self.__on_no_media_folder_changed)
        self.external_switch = self.window_builder.get_object(
            "external_switch")

        self.auto_scan_switch = self.window_builder.get_object(
            "auto_scan_switch")

        # some visual stuff
        self.category_toolbar_separator = self.window_builder.get_object("category_toolbar_separator")
        if tools.is_elementary():
            self.category_toolbar.set_visible(False)

        # get about dialog
        self.about_dialog = self.about_builder.get_object("about_dialog")
        self.about_dialog.set_transient_for(self.window)
        self.about_dialog.connect("delete-event", self.hide_window)
        self.about_dialog.set_version(self.version)

        # shortcuts
        self.accel = Gtk.AccelGroup()

        # sorting and filtering
        self.author_box.connect("row-selected", self.__on_listbox_changed)
        self.reader_box.connect("row-selected", self.__on_listbox_changed)
        self.book_box.set_sort_func(self.__sort_books, None, False)
        self.book_box.set_filter_func(self.__filter_books, None, False)

        try:
            about_close_button = self.about_builder.get_object(
                "button_box").get_children()[2]

            if about_close_button:
                about_close_button.connect(
                    "clicked", self.__about_close_clicked)
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

        self.play_pause_action = Gio.SimpleAction.new("play_pause", None)
        self.play_pause_action.connect("activate", self.play_pause)
        self.app.add_action(self.play_pause_action)
        self.app.set_accels_for_action("app.play_pause", ["space"])

        back_action = Gio.SimpleAction.new("back", None)
        back_action.connect("activate", self.back)
        self.app.add_action(back_action)
        self.app.set_accels_for_action("app.back", ["Escape"])

        self.hide_offline_action = Gio.SimpleAction.new_stateful("hide_offline", None, GLib.Variant.new_boolean(
            tools.get_glib_settings().get_boolean("hide-offline")))
        self.hide_offline_action.connect("change-state", self.__on_hide_offline)
        self.app.add_action(self.hide_offline_action)

    def __init_components(self):
        self.titlebar = Titlebar()

        self.sleep_timer = SleepTimer()
        self.speed = PlaybackSpeed()
        self.search = Search()
        self.settings = Settings()
        self.settings.add_listener(self.__on_settings_changed)
        self.book_overview = BookOverview()
        self.fs_monitor = fs_monitor.FilesystemMonitor()
        self.offline_cache = offline_cache.OfflineCache()
        player.init()

        self.titlebar.activate()

        if player.get_current_track() is None:
            self.block_ui_buttons(True)

    def __load_last_book(self):
        """
        Loads the last book into the player
        """
        player.load_last_book()
        if player.get_current_track():
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
        self.settings.show()

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

    def play_pause(self, action, parameter):
        player.play_pause(None)

    def pause(self):
        self.current_book_element.set_playing(False)

    def stop(self):
        """
        Remove all information about a playing book from the ui.
        """
        if self.current_book_element:
            self.current_book_element.set_playing(False)

    def block_ui_buttons(self, block, scan=False):
        """
        Makes the buttons to interact with the player insensetive.
        :param block: Boolean
        """
        sensitive = not block
        self.play_pause_action.set_enabled(sensitive)
        self.titlebar.block_ui_buttons(block, scan)
        if scan:
            self.scan_action.set_enabled(sensitive)
            self.hide_offline_action.set_enabled(sensitive)
            self.settings.block_ui_elements(block)
            self.book_overview.block_ui_elements(block)

    def get_ui_buttons_blocked(self):
        """
        Are the UI buttons currently blocked?
        """
        return self.titlebar.get_ui_buttons_blocked(), self.settings.get_storage_elements_blocked()

    def switch_to_working(self, message, first, block=True):
        """
        Switch the UI state to working.
        This is used for example when an import is currently happening.
        This blocks the user from doing some stuff like starting playback.
        """
        self.titlebar.switch_to_working(message, first)
        if block:
            self.block_ui_buttons(True, True)
        self.window.props.window.set_cursor(
            Gdk.Cursor.new_from_name(self.window.get_display(), "progress"))

    def switch_to_playing(self):
        """
        Switch the UI state back to playing.
        This enables all UI functionality for the user.
        """
        self.titlebar.switch_to_playing()
        if self.main_stack.props.visible_child_name != "book_overview" and self.main_stack.props.visible_child_name != "nothing_here" and self.main_stack.props.visible_child_name != "no_media":
            self.main_stack.props.visible_child_name = "main"
        if self.main_stack.props.visible_child_name != "no_media" and self.main_stack.props.visible_child_name != "book_overview":
            self.category_toolbar.set_visible(True)
        if player.get_current_track():
            self.block_ui_buttons(False, True)
        else:
            # we want to only block the player controls
            self.block_ui_buttons(False, True)
            self.block_ui_buttons(True, False)
        self.window.props.window.set_cursor(None)

    def check_for_tracks(self):
        """
        Check if there are any imported files.
        If there aren't display a welcome screen.
        """
        if books().count() < 1:
            path = ""
            if Storage.select().count() > 0:
                path = Storage.select().where(Storage.default == True).get().path
                    
            
            if not path:
                path = os.path.join(os.path.expanduser("~"), _("Audiobooks"))
                
                if not os.path.exists(path):
                    os.mkdir(path)

                Storage.create(path=path, default=True)

            self.no_media_file_chooser.set_current_folder(path)
            self.main_stack.props.visible_child_name = "no_media"
            self.block_ui_buttons(True)
            self.titlebar.stop()
            self.category_toolbar.set_visible(False)
        else:
            self.main_stack.props.visible_child_name = "main"
            # This displays the placeholder if there is not a recent book yet
            self.__on_sort_stack_changed(None, None)

    def scan(self, action, first_scan, force=False):
        """
        Start the db import in a seperate thread
        """
        self.switch_to_working(_("Importing Audiobooks"), first_scan)
        thread = Thread(target=importer.update_database,
                        args=(self, force, ), name="UpdateDatabaseThread")
        thread.start()

    def auto_import(self):
        if tools.get_glib_settings().get_boolean("autoscan"):
            self.scan(None, False)

    def back(self, action, parameter):
        self.__on_back_clicked(None)

    def filter_author_reader(self, hide_offline):
        """
        This method filters unavailable (offline) author and readers from
        the list boxes.
        """
        offline_authors = []
        offline_readers = []
        online_authors = []
        online_readers = []

        if hide_offline:
            for b in books():
                if not self.fs_monitor.is_book_online(b) and not b.downloaded:
                    offline_authors.append(b.author)
                    offline_readers.append(b.reader)
                else:
                    online_authors.append(b.author)
                    online_readers.append(b.reader)
            
            offline_authors = sorted(list(set(offline_authors)))
            offline_readers = sorted(list(set(offline_readers)))
            online_authors = sorted(list(set(online_authors)))
            online_readers = sorted(list(set(online_readers)))

            authors = [i for i in offline_authors if i not in online_authors]
            readers = [i for i in offline_readers if i not in online_readers]

            for row in self.author_box.get_children():
                if not isinstance(row, ListBoxRowWithData):
                    continue

                if any(row.data == x for x in authors):
                    row.set_visible(False)
                else:
                    row.set_visible(True)
            
            for row in self.reader_box.get_children():
                if not isinstance(row, ListBoxRowWithData):
                    continue
                
                if any(row.data == x for x in readers):
                    row.set_visible(False)
                else:
                    row.set_visible(True)
        else:
            for row in self.author_box:
                row.set_visible(True)

            for row in self.reader_box:
                row.set_visible(True)
            

    def populate_author_reader(self):
        tools.remove_all_children(self.author_box)
        tools.remove_all_children(self.reader_box)

        # Add the special All element
        all_row = ListBoxRowWithData(_("All"), False)
        all_row.set_tooltip_text(_("Display all books"))
        self.author_box.add(all_row)
        self.author_box.add(ListBoxSeparatorRow())
        self.author_box.select_row(all_row)

        all_row = ListBoxRowWithData(_("All"), False)
        all_row.set_tooltip_text(_("Display all books"))
        self.reader_box.add(all_row)
        self.reader_box.add(ListBoxSeparatorRow())
        self.reader_box.select_row(all_row)

        for book in authors():
            row = ListBoxRowWithData(book.author, False)
            self.author_box.add(row)

        for book in readers():
            row = ListBoxRowWithData(book.reader, False)
            self.reader_box.add(row)

        # this is required to see the new items
        self.author_box.show_all()
        self.reader_box.show_all()


    def refresh_content(self):
        """
        Refresh all content.
        """
        # First clear the boxes
        childs = self.book_box.get_children()
        for element in childs:
            self.book_box.remove(element)

        self.populate_author_reader()
        self.filter_author_reader(tools.get_glib_settings().get_boolean("hide-offline"))

        for b in books():
            self.book_box.add(BookElement(b))

        self.book_box.show_all()

        return False

    def refresh_recent(self):
        if self.titlebar.current_book:
            book_element = next(filter(
                lambda x: x.book.id == self.titlebar.current_book.id,
                self.book_box.get_children()), None)
            book_element.refresh_book_object()

            if self.sort_stack.props.visible_child_name == "recent":
                self.book_box.invalidate_sort()

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

    def display_failed_imports(self, files):
        """
        Displays a dialog with a list of files that could not be imported.
        """
        dialog = ImportFailedDialog(files)
        dialog.show()

    def jump_to_author(self, book):
        """
        Jump to the given book author.
        This is used from the search popover.
        """
        row = next(filter(
            lambda x: type(x.get_children()[0]) is Gtk.Label and x.get_children()[
                0].get_text() == book.author,
            self.author_box.get_children()), None)

        self.sort_stack.props.visible_child_name = "author"
        self.__on_sort_stack_changed(None, None)
        self.author_box.select_row(row)
        self.book_box.invalidate_filter()
        self.book_box.invalidate_sort()
        self.toolbar_revealer.set_reveal_child(True)
        self.search.close()

    def jump_to_reader(self, book):
        """
        Jump to the given book reader.
        This is used from the search popover.
        """
        row = next(filter(
            lambda x: type(x.get_children()[0]) is Gtk.Label and x.get_children()[
                0].get_text() == book.reader,
            self.reader_box.get_children()), None)

        self.sort_stack.props.visible_child_name = "reader"
        self.__on_sort_stack_changed(None, None)
        self.reader_box.select_row(row)
        self.book_box.invalidate_filter()
        self.book_box.invalidate_sort()
        self.toolbar_revealer.set_reveal_child(True)
        self.search.close()

    def jump_to_book(self, book):
        """
        Open book overview with the given book.
        """
        # first update track ui
        book = Book.select().where(Book.id == book.id).get()
        self.book_overview.set_book(book)

        # then switch the stacks
        self.main_stack.props.visible_child_name = "book_overview"
        self.toolbar_revealer.set_reveal_child(False)
        self.search.close()

    def __on_hide_offline(self, action, value):
        """
        Show/Hide offline books action handler.
        """
        action.set_state(value)
        tools.get_glib_settings().set_boolean("hide-offline", value.get_boolean())

        self.book_box.invalidate_filter()
        self.filter_author_reader(value.get_boolean())

    def __on_drag_data_received(self, widget, context, x, y, selection, target_type, timestamp):
        """
        We want to import the files that are dragged onto the window.
        inspired by https://stackoverflow.com/questions/24094186/drag-and-drop-file-example-in-pygobject
        """
        if target_type == 80:
            self.switch_to_working("copying new files…", False)
            thread = Thread(target=importer.copy, args=(
                self, selection, ), name="DragDropImportThread")
            thread.start()

    def __on_no_media_folder_changed(self, sender):
        """
        Get's called when the user changes the audiobook location from
        the no media screen. Now we want to do a first scan instead of a rebase.
        """
        location = self.no_media_file_chooser.get_file().get_path()
        external = self.external_switch.get_active()
        Storage.delete().where(Storage.path != "").execute()
        Storage.create(path=location, default=True, external=external)
        self.main_stack.props.visible_child_name = "import"
        self.scan(None, True)
        self.settings._init_storage()
        self.fs_monitor.init_offline_mode()

    def __on_sort_stack_changed(self, widget, page):
        """
        Switch to author selection
        """
        page = self.sort_stack.props.visible_child_name

        if page == "recent":
            self.sort_stack_revealer.set_reveal_child(False)
            if Book.select().where(Book.last_played > 0).count() < 1:
                self.main_stack.props.visible_child_name = "nothing_here"
        else:
            self.sort_stack_revealer.set_reveal_child(True)
            self.main_stack.props.visible_child_name = "main"

        self.__on_listbox_changed(None, None)

    def track_changed(self):
        """
        The track loaded in the player has changed.
        Refresh the currently playing track and mark it in the track overview popover.
        """
        # also reset the book playing state
        if self.current_book_element:
            self.current_book_element.set_playing(False)

        curr_track = player.get_current_track()
        self.current_book_element = next(
            filter(
                lambda x: x.book.id == curr_track.book.id,
                self.book_box.get_children()), None)

        self.block_ui_buttons(False, True)

    def __player_changed(self, event, message):
        """
        Listen to and handle all gst player messages that are important for the ui.
        """
        if event == "stop":
            if self.__inhibit_cookie:
                self.app.uninhibit(self.__inhibit_cookie)
            self.stop()
            self.titlebar.stop()
            self.sleep_timer.stop()
        elif event == "play":
            self.play()
            self.titlebar.play()
            self.sleep_timer.start()
            self.refresh_recent()
            self.__inhibit_cookie = self.app.inhibit(
                self.window, Gtk.ApplicationInhibitFlags.SUSPEND, "Playback of audiobook")
        elif event == "pause":
            if self.__inhibit_cookie:
                self.app.uninhibit(self.__inhibit_cookie)
            self.pause()
            self.titlebar.pause()
            self.sleep_timer.stop()
        elif event == "track-changed":
            self.track_changed()
            if self.sort_stack.props.visible_child_name == "recent":
                self.book_box.invalidate_filter()
                self.book_box.invalidate_sort()
        elif event == "resource-not-found":
            if self.dialog_open:
                return

            self.dialog_open = True
            dialog = FileNotFoundDialog(message.file)
            dialog.show()

    def __window_resized(self, window):
        """
        Resize the progress scale to expand to the window size
        for older gtk versions.
        """
        width, height = self.window.get_size()
        value = width - 850
        if value < 80:
            value = 80
        self.titlebar.set_progress_scale_width(value)

    def __about_close_clicked(self, widget):
        self.about_dialog.hide()

    def __on_back_clicked(self, widget):
        self.book_box.unselect_all()
        self.main_stack.props.visible_child_name = "main"
        self.toolbar_revealer.set_reveal_child(True)

    def on_close(self, widget, data=None):
        """
        Close and dispose everything that needs to be when window is closed.
        """
        log.info("Closing.")
        self.titlebar.close()
        self.fs_monitor.close()
        if self.sleep_timer.is_running():
            self.sleep_timer.stop()

        # save current position when still playing
        if player.get_gst_player_state() == Gst.State.PLAYING:
            Track.update(position=player.get_current_duration()).where(
                Track.id == player.get_current_track().id).execute()
            player.stop()

        player.dispose()

        close_db()

        report.close()

        log.info("Closing app.")
        self.app.quit()
        log.info("App closed.")

    def __on_listbox_changed(self, sender, row):
        """
        Refresh the filtering on author/reader selection.
        """
        self.book_box.invalidate_filter()
        self.book_box.invalidate_sort()

    def __sort_books(self, book_1, book_2, data, notify_destroy):
        """
        Sort books alphabetically by name.
        """
        selected_stack = self.sort_stack.props.visible_child_name
        if selected_stack == "recent":
            return book_1.book.last_played < book_2.book.last_played
        else:
            return book_1.book.name.lower() > book_2.book.name.lower()

    def __filter_books(self, book, data, notify_destroy):
        """
        Filter the books in the book view according to the selected author/reader or "All".
        """
        selected_stack = self.sort_stack.props.visible_child_name
        if tools.get_glib_settings().get_boolean("hide-offline"):
            if not self.fs_monitor.is_book_online(book.book):
                offline_available = Book.get(Book.id == book.book.id).downloaded
            else:
                offline_available = True
        else:
            offline_available = True

        if selected_stack == "author":
            row = self.author_box.get_selected_row()
        elif selected_stack == "reader":
            row = self.reader_box.get_selected_row()

        if selected_stack == "author" or selected_stack == "reader":
            if row is None:
                return True and offline_available

            field = row.data
            if field is None or field == _("All"):
                return True and offline_available
            else:
                if selected_stack == "author":
                    return True and offline_available if book.book.author == field else False
                if selected_stack == "reader":
                    return True and offline_available if book.book.reader == field else False
        elif selected_stack == "recent":
            return True and offline_available if book.book.last_played > 0 else False

    def set_book_overview(self, book):
        # first update track ui
        self.book_overview.set_book(book)

        # then switch the stacks
        self.main_stack.props.visible_child_name = "book_overview"
        self.toolbar_revealer.set_reveal_child(False)

        self.book_overview.play_book_button.grab_remove()
        self.book_overview.scroller.grab_focus()
    
    def __on_settings_changed(self, event, message):
        """
        This method reacts to storage settings changes.
        """
        pass


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


class ListBoxSeparatorRow(Gtk.ListBoxRow):
    """
    This class represents a separator in a listbox row.
    """

    def __init__(self):
        super().__init__()
        separator = Gtk.Separator()
        self.add(separator)
        self.set_sensitive(False)
        self.props.selectable = False
