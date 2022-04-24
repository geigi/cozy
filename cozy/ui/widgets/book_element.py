import os
import subprocess

from gi.repository import Gtk, GObject, Gdk

from cozy.extensions.gtk_widget import set_hand_cursor, reset_cursor
from cozy.model.book import Book
from cozy.ui.widgets.album_element import AlbumElement

MAX_LABEL_LENGTH = 60


@Gtk.Template.from_resource('/com/github/geigi/cozy/book_element.ui')
class BookElement(Gtk.FlowBoxChild):
    __gtype_name__ = "BookElement"

    name_label: Gtk.Label = Gtk.Template.Child()
    author_label: Gtk.Label = Gtk.Template.Child()
    container_box: Gtk.Box = Gtk.Template.Child()
    event_box: Gtk.Box = Gtk.Template.Child()

    def __init__(self, book: Book):
        self.book: Book = book

        super().__init__()

        self.name_label.set_text(book.name)
        self.name_label.set_tooltip_text(book.name)
        self.author_label.set_text(book.author)
        self.author_label.set_tooltip_text(book.author)
        self.art: AlbumElement = AlbumElement(self.book)
        self.context_menu = None
        self.pressed = False

        self.container_box.prepend(self.art)

        self.art.connect("play-pause-clicked", self._on_album_art_press_event)

        self._event_box_primary_gesture = Gtk.GestureClick()
        self._event_box_primary_gesture.set_button(Gdk.BUTTON_PRIMARY)
        self._event_box_primary_gesture.connect("pressed", self._select_item)
        self._event_box_primary_gesture.connect("released", self._open_book_overview)
        self.event_box.add_controller(self._event_box_primary_gesture)

        self._event_box_context_gesture = Gtk.GestureClick()
        self._event_box_context_gesture.set_button(Gdk.BUTTON_SECONDARY)
        self._event_box_context_gesture.connect("released", self._show_context_menu)
        self.event_box.add_controller(self._event_box_context_gesture)

        self._event_box_key = Gtk.EventControllerKey()
        self._event_box_key.connect("key-pressed", self._on_key_press_event)
        self.event_box.add_controller(self._event_box_key)

        self._event_box_motion = Gtk.EventControllerMotion()
        self._event_box_motion.connect("enter", self._on_cover_enter_notify)
        self._event_box_motion.connect("leave", self._on_cover_leave_notify)

    def set_playing(self, is_playing):
        self.art.set_playing(is_playing)

    def update_progress(self):
        self.art.update_progress()

    def _create_context_menu(self):
        menu = Gtk.Menu()
        read_item = Gtk.MenuItem(label=_("Mark as read"))
        read_item.connect("button-press-event", self._mark_as_read)

        jump_item = Gtk.MenuItem(label=_("Open in file browser"))
        jump_item.connect("button-press-event", self._jump_to_folder)

        rm_item = Gtk.MenuItem(label=_("Remove from library"))
        rm_item.connect("button-press-event", self._remove_book)

        menu.append(read_item)
        menu.append(jump_item)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(rm_item)
        menu.attach_to_widget(self)
        return menu

    def _remove_book(self, _, __):
        if self.context_menu:
            self.context_menu.popdown()

        self.emit("book-removed", self.book)

    def _mark_as_read(self, _, __):
        self.book.position = -1

    def _jump_to_folder(self, _, __):
        """
        Opens the folder containing this books files in the default file explorer.
        """
        track = self.book.chapters[0]
        path = os.path.dirname(track.file)
        subprocess.Popen(['xdg-open', path])

    def _show_context_menu(self, gesture: Gtk.Gesture, *_):
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

        if self.context_menu is None:
            self.context_menu = self._create_context_menu()
        self.context_menu.popup()

    def _select_item(self, gesture: Gtk.Gesture, *_):
        if super().get_sensitive():
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            self.pressed = True
            self.container_box.get_style_context().add_class("selected")

    def _open_book_overview(self, gesture, *_):
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

        self.pressed = False
        self.container_box.get_style_context().remove_class("selected")
        if super().get_sensitive():
            self.emit("open-book-overview", self.book)

    def _on_key_press_event(self, keyval, *_):
        if keyval == Gdk.KEY_Return and super().get_sensitive():
            self.emit("open-book-overview", self.book)
            return True

    def _on_cover_enter_notify(self, widget: Gtk.Widget, __):
        set_hand_cursor(widget)

        self.art.set_hover(True)
        return True

    def _on_cover_leave_notify(self, widget: Gtk.Widget, __):
        reset_cursor(widget)
        self.art.set_hover(False)
        return True

    def _on_album_art_press_event(self, _, __):
        self.emit("play-pause-clicked", self.book)


GObject.type_register(BookElement)
GObject.signal_new('play-pause-clicked', BookElement, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))
GObject.signal_new('open-book-overview', BookElement, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))
GObject.signal_new('book-removed', BookElement, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))
