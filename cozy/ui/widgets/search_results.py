from gi.repository import Gtk, Gdk
import cozy.tools as tools
from cozy.control.artwork_cache import ArtworkCache
from cozy.ext import inject
from cozy.model.book import Book

MAX_BOOK_LENGTH = 80
BOOK_ICON_SIZE = 40


class SearchResult(Gtk.Box):
    """
    This class is the base class for all search result GUI object.
    It features a GTK box that is highlighted when hovered.
    """

    def __init__(self, on_click, on_click_data):
        super().__init__()

        self.on_click = on_click
        self.on_click_data = on_click_data

        self.connect("enter-notify-event", self._on_enter_notify)
        self.connect("leave-notify-event", self._on_leave_notify)
        if on_click:
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
        :param widget: as Gtk.Box
        :param event: as Gdk.Event
        """
        self.box.get_style_context().add_class("box_hover")

    def _on_leave_notify(self, widget, event):
        """
        On leave notify remove css hover class
        :param widget: as Gtk.Box (can be None)
        :param event: as Gdk.Event (can be None)
        """
        self.box.get_style_context().remove_class("box_hover")

    def __on_clicked(self, widget, event):
        self.on_click(self.on_click_data)


class ArtistSearchResult(SearchResult):
    """
    This class represents an author or reader search result.
    """

    def __init__(self, on_click, artist: str, is_author):

        super().__init__(on_click, artist)

        self.is_author = is_author
        self.on_click = on_click

        title_label = Gtk.Label()
        if is_author:
            title_label.set_text(tools.shorten_string(artist, MAX_BOOK_LENGTH))
            self.set_tooltip_text(_("Jump to author ") + artist)
        else:
            title_label.set_text(tools.shorten_string(artist, MAX_BOOK_LENGTH))
            self.set_tooltip_text(_("Jump to reader ") + artist)
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


class BookSearchResult(SearchResult):
    """
    This class represents a book search result.
    """
    _artwork_cache: ArtworkCache = inject.attr(ArtworkCache)

    def __init__(self, book: Book, on_click):
        super().__init__(on_click, book)

        self.set_tooltip_text(_("Play this book"))
        scale = self.get_scale_factor()

        pixbuf = self._artwork_cache.get_cover_pixbuf(book, scale, BOOK_ICON_SIZE)
        if pixbuf:
            surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, scale, None)
            img = Gtk.Image.new_from_surface(surface)
        else:
            img = Gtk.Image.new_from_icon_name("book-open-variant-symbolic", Gtk.IconSize.MENU)
            img.props.pixel_size = BOOK_ICON_SIZE
        img.set_size_request(BOOK_ICON_SIZE, BOOK_ICON_SIZE)

        title_label = Gtk.Label()
        title_label.set_text(tools.shorten_string(book.name, MAX_BOOK_LENGTH))
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
