from gi.repository import Gtk
from cozy.book_element import AlbumElement

MAX_BOOK_LENGTH = 80
MAX_TRACK_LENGTH = 40
BOOK_ICON_SIZE = 40


class SearchResult(Gtk.EventBox):
    """
    This class is the base class for all search result GUI object.
    It features a GTK box that is highlighted when hovered.
    """

    def __init__(self, on_click, book):
        super().__init__()

        self.on_click = on_click
        self.book = book

        self.connect("enter-notify-event", self._on_enter_notify)
        self.connect("leave-notify-event", self._on_leave_notify)
        if on_click is not None:
            self.connect("button-press-event", self.__on_clicked)

        self.props.margin_top = 2
        self.props.margin_bottom = 2

        # This box contains all content
        self.box = Gtk.Box()
        self.box.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.box.set_spacing(3)
        self.box.set_halign(Gtk.Align.FILL)
        self.box.set_valign(Gtk.Align.CENTER)

    def _on_enter_notify(self, widget, event):
        """
        On enter notify add css hover class
        :param widget: as Gtk.EventBox
        :param event: as Gdk.Event
        """
        self.box.get_style_context().add_class("box_hover")

    def _on_leave_notify(self, widget, event):
        """
        On leave notify remove css hover class
        :param widget: as Gtk.EventBox (can be None)
        :param event: as Gdk.Event (can be None)
        """
        self.box.get_style_context().remove_class("box_hover")

    def __on_clicked(self, widget, event):
        self.on_click(self.book)


class ArtistSearchResult(SearchResult):
    """
    This class represents an author or reader search result.
    """

    def __init__(self, on_click, book, is_author):

        super().__init__(on_click, book)

        self.is_author = is_author
        self.on_click = on_click

        title_label = Gtk.Label()
        if is_author:
            title_label.set_text((self.book.author[:MAX_BOOK_LENGTH] + '...') if len(
                self.book.author) > MAX_BOOK_LENGTH else self.book.author)
            self.set_tooltip_text(_("Jump to author ") + book.author)
        else:
            title_label.set_text((self.book.reader[:MAX_BOOK_LENGTH] + '...') if len(
                self.book.reader) > MAX_BOOK_LENGTH else self.book.reader)
            self.set_tooltip_text(_("Jump to reader ") + book.reader)
        title_label.set_halign(Gtk.Align.START)
        title_label.props.margin = 4
        title_label.props.hexpand = True
        title_label.props.hexpand_set = True
        title_label.set_margin_right(5)
        title_label.props.width_request = 100
        title_label.props.xalign = 0.0
        title_label.set_line_wrap(True)

        self.box.add(title_label)
        self.add(self.box)
        self.show_all()


class TrackSearchResult(SearchResult):
    """
    This class represents a track search result (currently not used).
    """

    def __init__(self, on_click, track):
        super().__init__(on_click)

        self.track = track

        title_label = Gtk.Label()
        title_label.set_text((self.track.name[:MAX_TRACK_LENGTH] + '...') if len(
            self.track.name) > MAX_TRACK_LENGTH else self.track.name)
        title_label.set_halign(Gtk.Align.START)
        title_label.props.margin = 4
        title_label.props.hexpand = True
        title_label.props.hexpand_set = True
        title_label.set_margin_right(5)
        title_label.props.width_request = 100
        title_label.props.xalign = 0.0
        title_label.set_line_wrap(True)

        self.box.add(title_label)
        self.add(self.box)
        self.show_all()


class BookSearchResult(SearchResult):
    """
    This class represents a book search result.
    """

    def __init__(self, book, on_click):
        super().__init__(on_click, book)

        self.set_tooltip_text(_("Play this book"))

        img = AlbumElement(self.book, BOOK_ICON_SIZE, False, True)
        img.disconnect_signals()
        self.connect("enter-notify-event", img._on_enter_notify)
        self.connect("enter-notify-event", img._on_play_enter_notify)
        self.connect("leave-notify-event", img._on_leave_notify)
        self.connect("leave-notify-event", img._on_play_leave_notify)
        self.connect("button-press-event", img._on_play_button_press)

        title_label = Gtk.Label()
        title_label.set_text((self.book.name[:MAX_BOOK_LENGTH] + '...') if len(
            self.book.name) > MAX_BOOK_LENGTH else self.book.name)
        title_label.set_halign(Gtk.Align.START)
        title_label.props.margin = 4
        title_label.props.hexpand = True
        title_label.props.hexpand_set = True
        title_label.set_margin_right(5)
        title_label.props.width_request = 100
        title_label.props.xalign = 0.0
        title_label.set_line_wrap(True)

        self.box.add(img)
        self.box.add(title_label)
        self.add(self.box)
        self.show_all()
