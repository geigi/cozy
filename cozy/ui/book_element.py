import logging
import os
import subprocess

from gi.repository import Gtk, Gdk, Pango, GObject

import cozy.tools as tools
import cozy.ui
from cozy.model.book import Book
from cozy.ui.widgets.album_element import AlbumElement

MAX_BOOK_LENGTH = 60
MAX_TRACK_LENGTH = 40

log = logging.getLogger("book_element")


class BookElement(Gtk.FlowBoxChild):
    """
    This class represents a book with big artwork in the book viewer.
    """
    ui = None
    selected = False
    wait_to_seek = False
    playing = False
    track_box = None
    current_track_element = None
    context_menu = None

    def __init__(self, book: Book):
        self.book: Book = book
        self.ui = cozy.ui.main_view.CozyUI()

        self.ONLINE_TOOLTIP_TEXT = _("Open book overview")

        super().__init__()
        self.event_box = Gtk.EventBox()
        self.add_events(Gdk.EventMask.KEY_PRESS_MASK)
        self.box = Gtk.Box()
        self.box.set_orientation(Gtk.Orientation.VERTICAL)
        self.box.set_spacing(7)
        self.box.set_halign(Gtk.Align.CENTER)
        self.box.set_valign(Gtk.Align.START)
        self.box.set_margin_top(10)

        # label contains the book name and is limited to x chars
        title_label = Gtk.Label()
        title = tools.shorten_string(self.book.name, MAX_BOOK_LENGTH)
        title_label.set_text(title)
        title_label.get_style_context().add_class("bold")
        title_label.set_xalign(0.5)
        title_label.set_line_wrap(Pango.WrapMode.WORD_CHAR)
        title_label.props.max_width_chars = 30
        title_label.props.justify = Gtk.Justification.CENTER

        author_label = Gtk.Label.new(
            tools.shorten_string(self.book.author, MAX_BOOK_LENGTH))
        author_label.set_xalign(0.5)
        author_label.set_line_wrap(Pango.WrapMode.WORD_CHAR)
        author_label.props.max_width_chars = 30
        author_label.props.justify = Gtk.Justification.CENTER
        author_label.get_style_context().add_class("dim-label")

        self.art = AlbumElement(self.book)

        self.box.set_tooltip_text(self.ONLINE_TOOLTIP_TEXT)

        # assemble finished element
        self.box.add(self.art)
        self.box.add(title_label)
        self.box.add(author_label)
        self.event_box.add(self.box)
        self.add(self.event_box)

        self.art.connect("play-pause-clicked", self._on_album_art_press_event)
        self.event_box.connect("button-press-event", self.__on_button_press_event)
        self.connect("key-press-event", self.__on_key_press_event)
        self.event_box.connect("enter-notify-event", self._on_cover_enter_notify)
        self.event_box.connect("leave-notify-event", self._on_cover_leave_notify)

    def set_playing(self, is_playing):
        self.art.set_playing(is_playing)

    def update_progress(self):
        self.art.update_progress()

    def _on_album_art_press_event(self, _, __):
        self.emit("play-pause-clicked", self.book)

    def __on_button_press_event(self, _, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            if self.context_menu is None:
                self.context_menu = self.__create_context_menu()
            self.context_menu.popup(
                None, None, None, None, event.button, event.time)
            return True
        elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            if super().get_sensitive():
                self.emit("open-book-overview", self.book)
                return True
        elif event.type == Gdk.EventType.KEY_PRESS and event.keyval == Gdk.KEY_Return:
            if super().get_sensitive():
                self.emit("open-book-overview", self.book)
                return True

    def __on_key_press_event(self, _, key):
        if key.keyval == Gdk.KEY_Return and super().get_sensitive():
            self.emit("open-book-overview", self.book)
            return True

    def __create_context_menu(self):
        menu = Gtk.Menu()
        read_item = Gtk.MenuItem(label=_("Mark as read"))
        read_item.connect("button-press-event", self.__mark_as_read)

        jump_item = Gtk.MenuItem(label=_("Open in file browser"))
        jump_item.connect("button-press-event", self.__jump_to_folder)

        rm_item = Gtk.MenuItem(label=_("Remove from library"))
        rm_item.connect("button-press-event", self.__remove_book)

        menu.append(read_item)
        menu.append(jump_item)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(rm_item)
        menu.attach_to_widget(self)
        menu.show_all()
        return menu

    def __remove_book(self, _, __):
        if self.context_menu:
            self.context_menu.popdown()

        self.emit("book-removed", self.book)

    def __mark_as_read(self, _, __):
        self.book.position = -1

    def __jump_to_folder(self, _, __):
        """
        Opens the folder containing this books files in the default file explorer.
        """
        track = self.book.chapters[0]
        path = os.path.dirname(track.file)
        subprocess.Popen(['xdg-open', path])

    def _on_cover_enter_notify(self, widget: Gtk.Widget, __):
        try:
            widget.props.window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
        except:
            log.error("Broken mouse theme, failed to set cursor.")

        self.art.set_hover(True)

    def _on_cover_leave_notify(self, widget: Gtk.Widget, __):
        widget.props.window.set_cursor(None)
        self.art.set_hover(False)


GObject.type_register(BookElement)
GObject.signal_new('play-pause-clicked', BookElement, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))
GObject.signal_new('open-book-overview', BookElement, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))
GObject.signal_new('book-removed', BookElement, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))
