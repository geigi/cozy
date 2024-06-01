from gi.repository import Gdk, Gio, GObject, Gtk

from cozy.model.book import Book
from cozy.ui.widgets.album_element import AlbumElement


@Gtk.Template.from_resource('/com/github/geigi/cozy/ui/book_element.ui')
class BookElement(Gtk.FlowBoxChild):
    __gtype_name__ = "BookElement"

    name_label: Gtk.Label = Gtk.Template.Child()
    author_label: Gtk.Label = Gtk.Template.Child()
    container_box: Gtk.Box = Gtk.Template.Child()

    def __init__(self, book: Book):
        super().__init__()

        self.book = book
        self.pressed = False

        self.name_label.set_text(book.name)
        self.name_label.set_tooltip_text(book.name)
        self.author_label.set_text(book.author)
        self.author_label.set_tooltip_text(book.author)

        self.art = AlbumElement(self.book)
        self.art.connect("play-pause-clicked", self._on_album_art_press_event)

        self.container_box.prepend(self.art)
        self.set_cursor(Gdk.Cursor.new_from_name("pointer"))

        self._add_event_controllers()

    def _add_event_controllers(self):
        primary_button_gesture = Gtk.GestureClick(button=Gdk.BUTTON_PRIMARY)
        # primary_button_gesture.connect("pressed", self._select_item)
        primary_button_gesture.connect("released", self._open_book_overview)
        self.container_box.add_controller(primary_button_gesture)

        secondary_button_gesture = Gtk.GestureClick(button=Gdk.BUTTON_SECONDARY)
        secondary_button_gesture.connect("released", self._show_context_menu)
        self.container_box.add_controller(secondary_button_gesture)

        # FIXME: When clicking on an album's play button in the recents view,
        # it jumps to the first position, and GtkGestureLongPress thinks it's
        # a long press gesture, although it's just an unfinished long press
        long_press_gesture = Gtk.GestureLongPress()
        long_press_gesture.connect("pressed", self._show_context_menu)
        self.container_box.add_controller(long_press_gesture)

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect("key-pressed", self._on_key_press_event)
        self.container_box.add_controller(key_event_controller)

        motion_event_controller = Gtk.EventControllerMotion()
        motion_event_controller.connect("enter", self._on_cover_enter_notify)
        motion_event_controller.connect("leave", self._on_cover_leave_notify)
        self.container_box.add_controller(motion_event_controller)

    @GObject.Signal(arg_types=(object,))
    def play_pause_clicked(self, *_): ...

    @GObject.Signal(arg_types=(object,))
    def open_book_overview(self, *_): ...

    @GObject.Signal(arg_types=(object,))
    def book_removed(self, *_): ...

    def set_playing(self, is_playing):
        self.art.set_playing(is_playing)

    def update_progress(self):
        self.art.update_progress()

    def _create_context_menu(self):
        menu_model = Gio.Menu()

        self.install_action("book_element.mark_as_read", None, self._mark_as_read)
        menu_model.append(_("Mark as read"), "book_element.mark_as_read")

        self.install_action("book_element.jump_to_folder", None, self._jump_to_folder)
        menu_model.append(_("Open in file browser"), "book_element.jump_to_folder")

        self.install_action("book_element.remove_book", None, self._remove_book)
        menu_model.append(_("Remove from library"), "book_element.remove_book")

        menu = Gtk.PopoverMenu(menu_model=menu_model, has_arrow=False)
        menu.set_parent(self.art)

        return menu

    def _remove_book(self, *_):
        self.emit("book-removed", self.book)

    def _mark_as_read(self, *_):
        self.book.position = -1

    def _jump_to_folder(self, *_):
        """
        Opens the folder containing this books files in the default file explorer.
        """
        track = self.book.chapters[0]

        file_launcher = Gtk.FileLauncher(file=Gio.File.new_for_path(track.file))
        dummy_callback = lambda d, r: d.open_containing_folder_finish(r)
        file_launcher.open_containing_folder(None, None, dummy_callback)

    def _show_context_menu(self, gesture: Gtk.Gesture, *_):
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

        self._create_context_menu().popup()

    def _select_item(self, gesture: Gtk.Gesture, *_):
        if super().get_sensitive():
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            self.pressed = True
            self.container_box.add_css_class("selected")

    def _open_book_overview(self, gesture, *_):
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

        self.pressed = False
        self.container_box.remove_css_class("selected")
        if super().get_sensitive():
            self.emit("open-book-overview", self.book)

    def _on_key_press_event(self, keyval, *_):
        if keyval == Gdk.KEY_Return and super().get_sensitive():
            self.emit("open-book-overview", self.book)

    def _on_cover_enter_notify(self, *_):
        self.art.set_hover(True)

    def _on_cover_leave_notify(self, *_):
        self.art.set_hover(False)

    def _on_album_art_press_event(self, *_):
        self.emit("play-pause-clicked", self.book)
