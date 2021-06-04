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
        self.author_label.set_text(book.author)
        self.art: AlbumElement = AlbumElement(self.book)
        self.context_menu = None
        self.pressed = False

        self.container_box.pack_start(self.art, False, True, 0)

        self.art.connect("play-pause-clicked", self._on_album_art_press_event)
        self.event_box.connect("button-press-event", self._on_button_press_event)
        self.event_box.connect("button-release-event", self._on_button_release_event)
        self.event_box.connect("key-press-event", self._on_key_press_event)
        self.event_box.connect("enter-notify-event", self._on_cover_enter_notify)
        self.event_box.connect("leave-notify-event", self._on_cover_leave_notify)

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
        menu.show_all()
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

    def _on_button_press_event(self, _, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            if self.context_menu is None:
                self.context_menu = self._create_context_menu()
            self.context_menu.popup(
                None, None, None, None, event.button, event.time)
            return True
        elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            if super().get_sensitive():
                self.pressed = True
                self.container_box.get_style_context().add_class("selected")
        elif event.type == Gdk.EventType.KEY_PRESS and event.keyval == Gdk.KEY_Return:
            if super().get_sensitive():
                self.emit("open-book-overview", self.book)
                return True

    def _on_button_release_event(self, _, event):
        if event.type == Gdk.EventType.BUTTON_RELEASE and event.button == 1 and self.pressed:
            self.pressed = False
            self.container_box.get_style_context().remove_class("selected")
            if super().get_sensitive():
                self.emit("open-book-overview", self.book)
                return True

    def _on_key_press_event(self, _, key):
        if key.keyval == Gdk.KEY_Return and super().get_sensitive():
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
