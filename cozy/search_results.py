from gi.repository import Gtk
from cozy.db import *

MAX_BOOK_LENGTH = 60
MAX_TRACK_LENGTH = 40
BOOK_ICON_SIZE = 40

class SearchResult(Gtk.EventBox):
  """
  This class is the base class for all search result GUI object.
  It features a GTK box that is highlighted when hovered.
  """
  def __init__(self):
    super().__init__()

    self.connect("enter-notify-event", self._on_enter_notify)
    self.connect("leave-notify-event", self._on_leave_notify)

    self.props.margin_top = 2
    self.props.margin_bottom = 2

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

class ArtistSearchResult(SearchResult):
  """
  This class represents an author or reader search result.
  """
  def __init__(self, on_click, book, is_author):

    super().__init__()

    self.book = book
    self.is_author = is_author

    # This box contains all content
    self.box = Gtk.Box()
    self.box.set_orientation(Gtk.Orientation.HORIZONTAL)
    self.box.set_spacing(3)
    self.box.set_halign(Gtk.Align.FILL)
    self.box.set_valign(Gtk.Align.CENTER)

    title_label = Gtk.Label()
    if is_author:
      title_label.set_text((self.book.author[:MAX_BOOK_LENGTH] + '...') if len(self.book.author) > MAX_BOOK_LENGTH else self.book.author)
    else:
      title_label.set_text((self.book.reader[:MAX_BOOK_LENGTH] + '...') if len(self.book.reader) > MAX_BOOK_LENGTH else self.book.reader)
    title_label.set_halign(Gtk.Align.START)
    title_label.props.margin = 4
    title_label.props.hexpand = True
    title_label.props.hexpand_set = True
    title_label.set_margin_right(5)
    title_label.props.width_request = 100
    title_label.props.xalign = 0.0

    self.box.add(title_label)
    self.add(self.box)
    self.show_all()

class TrackSearchResult(SearchResult):
  """
  This class represents a track search result (currently not used).
  """
  def __init__(self, on_click, track):
    super().__init__()

    self.track = track

    # This box contains all content
    self.box = Gtk.Box()
    self.box.set_orientation(Gtk.Orientation.HORIZONTAL)
    self.box.set_spacing(3)
    self.box.set_halign(Gtk.Align.FILL)
    self.box.set_valign(Gtk.Align.CENTER)

    title_label = Gtk.Label()
    title_label.set_text((self.track.name[:MAX_TRACK_LENGTH] + '...') if len(self.track.name) > MAX_TRACK_LENGTH else self.track.name)
    title_label.set_halign(Gtk.Align.START)
    title_label.props.margin = 4
    title_label.props.hexpand = True
    title_label.props.hexpand_set = True
    title_label.set_margin_right(5)
    title_label.props.width_request = 100
    title_label.props.xalign = 0.0

    self.box.add(title_label)
    self.add(self.box)
    self.show_all()

class BookSearchResult(SearchResult):
  """
  This class represents a book search result.
  """
  def __init__(self, on_click, book):
    super().__init__()

    self.book = book

    # This box contains all content
    self.box = Gtk.Box()
    self.box.set_orientation(Gtk.Orientation.HORIZONTAL)
    self.box.set_spacing(3)
    self.box.set_halign(Gtk.Align.FILL)
    self.box.set_valign(Gtk.Align.CENTER)

    pixbuf = get_cover_pixbuf(book, BOOK_ICON_SIZE)
    img = Gtk.Image()
    img.set_halign(Gtk.Align.CENTER)
    img.set_valign(Gtk.Align.CENTER)
    img.set_from_pixbuf(pixbuf)
    img.set_size_request(BOOK_ICON_SIZE, BOOK_ICON_SIZE)

    title_label = Gtk.Label()
    title_label.set_text((self.book.name[:MAX_BOOK_LENGTH] + '...') if len(self.book.name) > MAX_BOOK_LENGTH else self.book.name)
    title_label.set_halign(Gtk.Align.START)
    title_label.props.margin = 4
    title_label.props.hexpand = True
    title_label.props.hexpand_set = True
    title_label.set_margin_right(5)
    title_label.props.width_request = 100
    title_label.props.xalign = 0.0

    self.box.add(img)
    self.box.add(title_label)
    self.add(self.box)
    self.show_all()