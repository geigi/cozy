from gi.repository import Gtk, Gdk, GdkPixbuf, Pango

from cozy.db import *
from cozy.player import *

MAX_BOOK_LENGTH = 60
MAX_TRACK_LENGTH = 40

class BookElement(Gtk.Box):
  """
  This class represents a book with big artwork in the book viewer.
  """
  book = None
  ui = None
  selected = False
  wait_to_seek = False

  def __init__(self, b, ui):
    self.book = b
    self.ui = ui

    super(Gtk.Box, self).__init__()
    self.set_orientation(Gtk.Orientation.VERTICAL)
    self.set_spacing(7)
    self.set_halign(Gtk.Align.CENTER)
    self.set_valign(Gtk.Align.START)
    self.set_margin_top(10)

    # label contains the book name and is limited to x chars
    title_label = Gtk.Label("")
    title = (self.book.name[:MAX_BOOK_LENGTH] + '...') if len(self.book.name) > MAX_BOOK_LENGTH else self.book.name
    title_label.set_markup("<b>" + title + "</b>")
    title_label.set_xalign(0.5)
    title_label.set_line_wrap(Pango.WrapMode.WORD_CHAR)
    title_label.props.max_width_chars = 30
    title_label.props.justify = Gtk.Justification.CENTER

    author_label = Gtk.Label((self.book.author[:MAX_BOOK_LENGTH] + '...') if len(self.book.author) > MAX_BOOK_LENGTH else self.book.author)
    author_label.set_xalign(0.5)
    author_label.set_line_wrap(Pango.WrapMode.WORD_CHAR)
    author_label.props.max_width_chars = 30
    author_label.props.justify = Gtk.Justification.CENTER

    # scale the book cover to a fix size.
    pixbuf = get_cover_pixbuf(self.book)
    if pixbuf.get_height() > pixbuf.get_width():
      width = int(pixbuf.get_width() / (pixbuf.get_height() / 180))
      pixbuf = pixbuf.scale_simple(width, 180, GdkPixbuf.InterpType.BILINEAR)
    else:
      height = int(pixbuf.get_height() / (pixbuf.get_width() / 180))
      pixbuf = pixbuf.scale_simple(180, height, GdkPixbuf.InterpType.BILINEAR)
    
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
    play_box.set_property("halign", Gtk.Align.CENTER)
    play_box.set_property("valign", Gtk.Align.CENTER)

    # play_color is an overlay for the play button 
    # with this it should be visible on any album art color
    play_image = GdkPixbuf.Pixbuf.new_from_resource("/de/geigi/cozy/play_background.svg")
    play_button = Gtk.Image.new_from_pixbuf(play_image)
    play_button.set_property("halign", Gtk.Align.CENTER)
    play_button.set_property("valign", Gtk.Align.CENTER)

    # this is the main overlay for the album art
    # we need to create field for the overlays 
    # to change the opacity of them on mouse over/leave events
    self.overlay = Gtk.Overlay.new()

    # this is the play symbol overlay
    self.play_overlay = Gtk.Overlay.new()

    # this is for the play button animation
    self.play_revealer = Gtk.Revealer()
    self.play_revealer.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
    self.play_revealer.set_transition_duration(300)
    self.play_revealer.add(self.play_overlay)
    
    # this grid has a background color to act as a visible overlay
    color = Gtk.Grid()
    color.set_property("halign", Gtk.Align.CENTER)
    color.set_property("valign", Gtk.Align.CENTER)

    # assemble play overlay
    play_box.add(play_button)
    self.play_overlay.add(play_box)

    # assemble overlay with album art
    self.overlay.add(img)
    self.overlay.add_overlay(self.play_revealer)

    # assemble overlay color
    color.add(self.overlay)
    box.add(color)

    # assemble finished element
    self.add(box)
    self.add(title_label)
    self.add(author_label)

    # create track list popover
    self.__create_popover()

    # listen to gst messages
    get_gst_bus().connect("message", self.__on_gst_message)

  def __create_popover(self):
    self.popover = Gtk.Popover.new(self)
    self.popover.set_position(Gtk.PositionType.BOTTOM)

    # We need to scroll when there are many tracks in a Book
    scroller = Gtk.ScrolledWindow()
    scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    
    # This box contains all content
    box = Gtk.Box()
    box.set_orientation(Gtk.Orientation.VERTICAL)
    box.set_halign(Gtk.Align.CENTER)
    box.set_valign(Gtk.Align.START)
    box.props.margin = 8

    count = 0
    for track in tracks(self.book):
      box.add(TrackElement(track))
      count += 1

    if Gtk.get_minor_version() > 20:
      scroller.set_propagate_natural_height(True)
      scroller.set_max_content_height(500)
    else:
      count = 0
      for track in tracks(self.book):
        box.add(TrackElement(track))
        count += 1
      padding = 17
      height = 24
      scroller_height = count * height + padding
      if scroller_height > 500:
        scroller_height = 500
      scroller.set_size_request(-1, scroller_height)

    self.popover.connect("closed", self.__on_popover_close)

    self.popover.add(scroller)
    scroller.add_with_viewport(box)
    scroller.show_all()

  def __on_button_press(self, eventbox, event):
    self.selected = True
    if Gtk.get_minor_version() > 20:
        self.popover.popup()
    else:
        self.popover.show_all()
    pass

  def _on_enter_notify(self, widget, event):
    """
    On enter notify change overlay opacity
    :param widget: as Gtk.EventBox
    :param event: as Gdk.Event
    """
    self.overlay.set_opacity(0.8)
    self.play_revealer.set_reveal_child(True)

  def _on_leave_notify(self, widget, event):
    """
    On leave notify change overlay opacity
    :param widget: as Gtk.EventBox (can be None)
    :param event: as Gdk.Event (can be None)
    """
    if not self.selected:
      self.overlay.set_opacity(1.0)
      self.play_revealer.set_reveal_child(False)

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
    track = get_track_for_playback(self.book)
    current_track = get_current_track()

    if current_track is not None and current_track.book.id == self.book.id:
      play_pause(None)
      if get_gst_player_state() == Gst.State.PLAYING:
        jump_to_ns(track.position)
    else:
      load_file(track)
      play_pause(None)
      self.wait_to_seek = True
      pos = int(track.position)
      self.ui.progress_scale.set_value(int(pos / 1000000000))

    return True
  
  def __on_gst_message(self, bus, message):
    """
    Handle gst messages from the player.
    Here we seek to the last position after a new track was loaded into the player.
    """
    if not self.wait_to_seek:
      return

    t = message.type
    if t == Gst.MessageType.STATE_CHANGED:
      state = get_gst_player_state()
      if state == Gst.State.PLAYING or state == Gst.State.PAUSED:
        query = Gst.Query.new_seeking(Gst.Format.TIME)
        if get_playbin().query(query):
          fmt, seek_enabled, start, end = query.parse_seeking()
          if seek_enabled:
            jump_to_ns(get_current_track().position)
            self.wait_to_seek = False

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

    # This box contains all content
    self.box = Gtk.Box()
    self.box.set_orientation(Gtk.Orientation.HORIZONTAL)
    self.box.set_spacing(3)
    self.box.set_halign(Gtk.Align.FILL)
    self.box.set_valign(Gtk.Align.CENTER)

    # These are the widgets that contain data
    self.play_img = Gtk.Image()
    no_label = Gtk.Label()
    title_label = Gtk.Label()
    dur_label = Gtk.Label()

    self.play_img.set_margin_right(5)
    self.play_img.props.width_request = 16

    no_label.set_text(str(self.track.number))
    no_label.props.margin = 4
    no_label.set_margin_right(7)
    no_label.set_margin_left(0)
    no_label.set_size_request(30, -1)
    no_label.set_xalign(1)

    title_label.set_text((self.track.name[:MAX_TRACK_LENGTH] + '...') if len(self.track.name) > MAX_TRACK_LENGTH else self.track.name)
    title_label.set_halign(Gtk.Align.START)
    title_label.props.margin = 4
    title_label.props.hexpand = True
    title_label.props.hexpand_set = True
    title_label.set_margin_right(7)
    title_label.props.width_request = 100
    title_label.props.xalign = 0.0

    dur_label.set_text(seconds_to_str(self.track.length))
    dur_label.set_halign(Gtk.Align.END)
    dur_label.props.margin = 4

    self.box.add(self.play_img)
    self.box.add(no_label)
    self.box.pack_start(title_label, True, True, 0)
    self.box.pack_end(dur_label, False, False, 0)

    self.add(self.box)

  def __on_button_press(self, eventbox, event):
    """
    Play the selected track.
    TODO Jump to last position
    """
    play_pause(self.track)
    Book.update(position=self.track).where(Book.id == self.track.book.id).execute()
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
