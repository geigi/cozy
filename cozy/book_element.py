from gi.repository import Gtk, Gdk, GdkPixbuf, Pango

from cozy.db import *

class BookElement(Gtk.Box):
  """
  This class represents a book with big artwork in the book viewer.
  """
  book = None
  selected = False
  def __init__(self, b):
    self.book = b

    super(Gtk.Box, self).__init__()
    self.set_orientation(Gtk.Orientation.VERTICAL)
    self.set_spacing(10)
    self.set_halign(Gtk.Align.CENTER)
    self.set_valign(Gtk.Align.START)
    self.set_margin_top(10)

    # label contains the book name and is limited to x chars
    label = Gtk.Label((self.book.name[:60] + '...') if len(self.book.name) > 60 else self.book.name)
    label.set_xalign(0.5)
    label.set_line_wrap(Pango.WrapMode.WORD_CHAR)
    label.props.max_width_chars = 30
    label.props.justify = Gtk.Justification.CENTER

    # load the book cover, otherwise the placeholder
    if self.book.cover is not None:
        loader = GdkPixbuf.PixbufLoader.new_with_type("jpeg")
        loader.write(b.cover)
        loader.close()
        pixbuf = loader.get_pixbuf()
    else:
        pixbuf = GdkPixbuf.Pixbuf.new_from_resource("/de/geigi/cozy/blank_album.png")

    # scale the book cover to a fix size.
    pixbuf = pixbuf.scale_simple(180, 180, GdkPixbuf.InterpType.BILINEAR)
    
    # box is the main container for the album art
    box = Gtk.EventBox()
    box.set_halign(Gtk.Align.CENTER)
    box.set_valign(Gtk.Align.CENTER)
    # connect mouse events to the event box
    box.connect("enter-notify-event", self._on_enter_notify)
    box.connect("leave-notify-event", self._on_leave_notify)
    box.connect("button-press-event", self.__on_button_press)

    # img contains the album art
    img = Gtk.Image()
    img.set_halign(Gtk.Align.CENTER)
    img.set_valign(Gtk.Align.CENTER)
    img.get_style_context().add_class("bordered")
    img.set_from_pixbuf(pixbuf)

    play_box = Gtk.EventBox()

    # we want to change the mouse cursor if the user is hovering over the play button
    play_box.connect("enter-notify-event", self._on_play_enter_notify)
    play_box.connect("leave-notify-event", self._on_play_leave_notify)
    # on click we want to play the audio book
    play_box.connect("button-press-event", self.__on_play_button_press)

    # play_img is the themed play button for the overlay
    play_img = Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.DIALOG)
    play_img.get_style_context().add_class("white")

    # play_color is an overlay for the play button 
    # with this it should be visible on any album art color
    play_color = Gtk.Grid()
    play_color.get_style_context().add_class("black_opacity")
    play_color.set_property("halign", Gtk.Align.CENTER)
    play_color.set_property("valign", Gtk.Align.CENTER)

    # this is the main overlay for the album art
    # we need to create field for the overlays 
    # to change the opacity of them on mouse over/leave events
    self.overlay = Gtk.Overlay.new()

    # this is the play symbol overlay
    self.play_overlay = Gtk.Overlay.new()
    self.play_overlay.set_opacity(0.0)
    
    # this grid has a background color to act as a visible overlay
    color = Gtk.Grid()
    color.get_style_context().add_class("mouse_hover")
    color.set_property("halign", Gtk.Align.CENTER)
    color.set_property("valign", Gtk.Align.CENTER)

    # assemble play overlay
    play_box.add(play_img)
    play_color.add(play_box)
    self.play_overlay.add(play_color)

    # assemble overlay with album art
    self.overlay.add(img)
    self.overlay.add_overlay(self.play_overlay)

    # assemble overlay color
    color.add(self.overlay)
    box.add(color)

    # assemble finished element
    self.add(box)
    self.add(label)

    # create track list popover
    self.__create_popover()

  def __create_popover(self):
    self.popover = Gtk.Popover.new(self)
    self.popover.set_position(Gtk.PositionType.BOTTOM)

    # TODO: Scroll if there are many tracks
    box = Gtk.Box()
    box.set_orientation(Gtk.Orientation.VERTICAL)
    box.set_halign(Gtk.Align.CENTER)
    box.set_valign(Gtk.Align.START)
    box.props.margin = 8

    for track in Tracks(self.book):
      box.add(TrackElement(track))

    self.popover.connect("closed", self.__on_popover_close)

    self.popover.add(box)

  def __on_button_press(self, eventbox, event):
    # TODO: Handle deselect
    self.selected = True
    self.popover.show_all()
    pass

  def _on_enter_notify(self, widget, event):
    """
    On enter notify change overlay opacity
    :param widget: as Gtk.EventBox
    :param event: as Gdk.Event
    """
    self.overlay.set_opacity(0.9)
    self.play_overlay.set_opacity(1.0)

  def _on_leave_notify(self, widget, event):
    """
    On leave notify change overlay opacity
    :param widget: as Gtk.EventBox (can be None)
    :param event: as Gdk.Event (can be None)
    """
    if not self.selected:
      self.overlay.set_opacity(1.0)
      self.play_overlay.set_opacity(0.0)

  def __on_popover_close(self, popover):
    """
    On popover close deselect this element and hide the overlay.
    """
    self.selected = False
    self._on_leave_notify(None, None)

  def _on_play_enter_notify(self, widget, event):
    """
    Change the cursor to pointing hand
    """
    self.props.window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

  def _on_play_leave_notify(self, widget, event):
    """
    Reset the cursor.
    """
    self.props.window.set_cursor(None)

  def __on_play_button_press(self, widget, event):
    """
    Play this book.
    """
    return True

class TrackElement(Gtk.EventBox):
  """
  An element to display a track in a book popover.
  """
  track = None
  selected = False
  def __init__(self, t):
    self.track = t

    super(Gtk.EventBox, self).__init__()
    self.connect("enter-notify-event", self._on_enter_notify)
    self.connect("leave-notify-event", self._on_leave_notify)
    self.connect("button-press-event", self.__on_button_press)

    self.box = Gtk.Box()
    self.box.set_orientation(Gtk.Orientation.HORIZONTAL)
    self.box.set_spacing(3)
    self.box.set_halign(Gtk.Align.FILL)
    self.box.set_valign(Gtk.Align.CENTER)

    self.play_img = Gtk.Image()
    no_label = Gtk.Label()
    title_label = Gtk.Label()
    dur_label = Gtk.Label()

    self.play_img.set_margin_right(5)
    self.play_img.props.width_request = 16

    no_label.set_text(str(self.track.number))
    no_label.props.margin = 4
    no_label.set_margin_right(7)

    # TODO: title max length
    title_label.set_text(self.track.name)
    title_label.set_halign(Gtk.Align.START)
    title_label.props.margin = 4
    title_label.set_margin_right(7)

    dur_label.set_text("1:00")
    dur_label.set_halign(Gtk.Align.END)
    dur_label.props.margin = 4

    self.box.add(self.play_img)
    self.box.add(no_label)
    self.box.pack_start(title_label, True, True, 0)
    self.box.pack_end(dur_label, False, False, 0)

    self.add(self.box)

  def __on_button_press(self, eventbox, event):
    pass

  def _on_enter_notify(self, widget, event):
    """
    On enter notify add css hover class
    :param widget: as Gtk.EventBox
    :param event: as Gdk.Event
    """
    self.play_img.set_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
    self.box.get_style_context().add_class("box_hover")

  def _on_leave_notify(self, widget, event):
    """
    On leave notify remove css hover class
    :param widget: as Gtk.EventBox (can be None)
    :param event: as Gdk.Event (can be None)
    """
    self.box.get_style_context().remove_class("box_hover")
    self.play_img.clear()