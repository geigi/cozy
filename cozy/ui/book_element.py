import os
import subprocess

import cozy.ext.inject as inject
from gi.repository import Gtk, Gdk, Pango, GObject

import cozy.tools as tools
import cozy.ui
from cozy.control.db import is_external
from cozy.control.filesystem_monitor import FilesystemMonitor
from cozy.model.book import Book
from cozy.ui.album_element import AlbumElement
from cozy.ui.settings import Settings

MAX_BOOK_LENGTH = 60
MAX_TRACK_LENGTH = 40


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
    _filesystem_monitor = inject.attr("FilesystemMonitor")
    _settings = inject.attr(Settings)

    def __init__(self, book: Book):
        self.book: Book = book
        self.ui = cozy.ui.main_view.CozyUI()

        self.ONLINE_TOOLTIP_TEXT = _("Open book overview")
        self.OFFLINE_TOOLTIP_TEXT = _("Currently offline")

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

        self.art = AlbumElement(
            self.book, 180, self.ui.window.get_scale_factor(), bordered=True, square=False)

        if is_external(self.book.db_object) and not self.book.offline and not self._filesystem_monitor.get_book_online(
                self.book):
            self.box.set_tooltip_text(self.OFFLINE_TOOLTIP_TEXT)
        else:
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
        self._filesystem_monitor.add_listener(self.__on_storage_changed)
        self._settings.add_listener(self.__on_storage_changed)

    def set_playing(self, is_playing):
        if is_playing:
            self.art.play_button.set_from_icon_name(
                "media-playback-pause-symbolic", self.art.icon_size)
        else:
            self.art.play_button.set_from_icon_name(
                "media-playback-start-symbolic", self.art.icon_size)

    def _on_album_art_press_event(self, widget, book):
        self.emit("play-pause-clicked", book)

    def __on_button_press_event(self, widget, event):
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

    def __on_key_press_event(self, widget, key):
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

    def __remove_book(self, widget, parameter):
        if self.context_menu:
            self.context_menu.popdown()

        self.emit("book-removed", self.book)

    def __mark_as_read(self, widget, parameter):
        self.book.position = -1

    def __jump_to_folder(self, widget, parameter):
        """
        Opens the folder containing this books files in the default file explorer.
        """
        track = self.book.chapters[0]
        path = os.path.dirname(track.file)
        subprocess.Popen(['xdg-open', path])

    def __on_storage_changed(self, event, message):
        if event == "storage-online" or event == "external-storage-removed":
            if message in self.book.chapters[0].file:
                self.box.set_tooltip_text(self.ONLINE_TOOLTIP_TEXT)
        elif event == "storage-offline":
            if message in self.book.chapters[0].file and not self.book.offline:
                self.box.set_tooltip_text(self.OFFLINE_TOOLTIP_TEXT)
        elif event == "external-storage-added":
            if not self._filesystem_monitor.is_book_online(self.book.db_object):
                self.box.set_tooltip_text(self.OFFLINE_TOOLTIP_TEXT)
        if event == "external-storage-removed":
            first_track = self.book.chapters[0]
            if first_track and message in first_track.file:
                self.box.set_tooltip_text(self.ONLINE_TOOLTIP_TEXT)


GObject.type_register(AlbumElement)
GObject.signal_new('play-pause-clicked', BookElement, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))
GObject.signal_new('open-book-overview', BookElement, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))
GObject.signal_new('book-removed', BookElement, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))
