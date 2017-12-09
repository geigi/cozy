from gi.repository import Gtk, Gdk, GdkPixbuf, Pango

from cozy.db import *
from cozy.player import *

MAX_BOOK_LENGTH = 60
MAX_TRACK_LENGTH = 40


class AlbumElement(Gtk.EventBox):
    """
    This class represents a clickable album art widget for a book.
    """

    def __init__(self, book, size, bordered=False, square=False):
        """
        :param size: the size for the longer side of the image
        :param bordered: should there be a border around the album art?
        :param square: should the widget be always a square?
        """
        super().__init__()

        self.book = book
        self.selected = False
        self.signal_ids = []
        self.play_signal_ids = []

        # scale the book cover to a fix size.
        pixbuf = get_cover_pixbuf(book, size)

        # box is the main container for the album art
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        # connect mouse events to the event box
        self.signal_ids.append(self.connect(
            "enter-notify-event", self._on_enter_notify))
        self.signal_ids.append(self.connect(
            "leave-notify-event", self._on_leave_notify))

        # img contains the album art
        img = Gtk.Image()
        img.set_halign(Gtk.Align.CENTER)
        img.set_valign(Gtk.Align.CENTER)
        if bordered:
            img.get_style_context().add_class("bordered")
        if square:
            img.set_size_request(size, size)
        img.set_from_pixbuf(pixbuf)

        self.play_box = Gtk.EventBox()

        # we want to change the mouse cursor if the user is hovering over the play button
        self.play_signal_ids.append(self.play_box.connect(
            "enter-notify-event", self._on_play_enter_notify))
        self.play_signal_ids.append(self.play_box.connect(
            "leave-notify-event", self._on_play_leave_notify))
        # on click we want to play the audio book
        self.play_signal_ids.append(self.play_box.connect(
            "button-press-event", self._on_play_button_press))
        self.play_box.set_property("halign", Gtk.Align.CENTER)
        self.play_box.set_property("valign", Gtk.Align.CENTER)
        self.play_box.set_tooltip_text(_("Play this book"))

        # play_color is an overlay for the play button
        # with this it should be visible on any album art color
        play_image = GdkPixbuf.Pixbuf.new_from_resource(
            "/de/geigi/cozy/play_background.svg")
        if square:
            play_image = play_image.scale_simple(
                size - 10, size - 10, GdkPixbuf.InterpType.BILINEAR)
        self.play_button = Gtk.Image.new_from_pixbuf(play_image)
        self.play_button.set_property("halign", Gtk.Align.CENTER)
        self.play_button.set_property("valign", Gtk.Align.CENTER)

        # this is the main overlay for the album art
        # we need to create field for the overlays
        # to change the opacity of them on mouse over/leave events
        self.overlay = Gtk.Overlay.new()

        # this is the play symbol overlay
        self.play_overlay = Gtk.Overlay.new()

        # this is for the play button animation
        self.play_revealer = Gtk.Revealer()
        self.play_revealer.set_transition_type(
            Gtk.RevealerTransitionType.CROSSFADE)
        self.play_revealer.set_transition_duration(300)
        self.play_revealer.add(self.play_overlay)

        # this grid has a background color to act as a visible overlay
        color = Gtk.Grid()
        color.set_property("halign", Gtk.Align.CENTER)
        color.set_property("valign", Gtk.Align.CENTER)

        # assemble play overlay
        self.play_box.add(self.play_button)
        self.play_overlay.add(self.play_box)

        # assemble overlay with album art
        self.overlay.add(img)
        self.overlay.add_overlay(self.play_revealer)

        # assemble overlay color
        color.add(self.overlay)
        self.add(color)

    def disconnect_signals(self):
        """
        Disconnect all signals from this element.
        """
        [self.disconnect(sig) for sig in self.signal_ids]
        [self.play_box.disconnect(sig) for sig in self.play_signal_ids]

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

    def _on_play_enter_notify(self, widget, event):
        """
        Change the cursor to pointing hand
        """
        self.props.window.set_cursor(Gdk.Cursor.new(Gdk.CursorType.HAND2))

    def _on_play_leave_notify(self, widget, event):
        """
        Reset the cursor.
        """
        self.props.window.set_cursor(None)

    def _on_play_button_press(self, widget, event):
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
            play_pause(None, True)

        return True


class BookElement(Gtk.Box):
    """
    This class represents a book with big artwork in the book viewer.
    """
    book = None
    ui = None
    selected = False
    wait_to_seek = False
    playing = False

    def __init__(self, b, ui):
        self.book = b
        self.ui = ui

        super(Gtk.Box, self).__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(7)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.START)
        self.set_margin_top(10)
        self.set_tooltip_text(_("Open book overview"))

        # label contains the book name and is limited to x chars
        title_label = Gtk.Label.new("")
        title = (self.book.name[:MAX_BOOK_LENGTH] + '...') if len(
            self.book.name) > MAX_BOOK_LENGTH else self.book.name
        title_label.set_markup("<b>" + title + "</b>")
        title_label.set_xalign(0.5)
        title_label.set_line_wrap(Pango.WrapMode.WORD_CHAR)
        title_label.props.max_width_chars = 30
        title_label.props.justify = Gtk.Justification.CENTER

        author_label = Gtk.Label.new((self.book.author[:MAX_BOOK_LENGTH] + '...') if len(
            self.book.author) > MAX_BOOK_LENGTH else self.book.author)
        author_label.set_xalign(0.5)
        author_label.set_line_wrap(Pango.WrapMode.WORD_CHAR)
        author_label.props.max_width_chars = 30
        author_label.props.justify = Gtk.Justification.CENTER

        self.connect("button-press-event", self.__on_button_press)

        self.art = AlbumElement(self.book, 180, True)

        # assemble finished element
        self.add(self.art)
        self.add(title_label)
        self.add(author_label)

        # create track list popover
        self.__create_popover()

    def __create_popover(self):
        self.popover = Gtk.Popover.new(self)
        self.popover.set_position(Gtk.PositionType.BOTTOM)

        # We need to scroll when there are many tracks in a Book
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # This box contains all content
        self.track_box = Gtk.Box()
        self.track_box.set_orientation(Gtk.Orientation.VERTICAL)
        self.track_box.set_halign(Gtk.Align.CENTER)
        self.track_box.set_valign(Gtk.Align.START)
        self.track_box.props.margin = 8

        count = 0
        for track in tracks(self.book):
            self.track_box.add(TrackElement(track, self.ui))
            count += 1

        if Gtk.get_minor_version() > 20:
            scroller.set_propagate_natural_height(True)
            scroller.set_max_content_height(500)
        else:
            padding = 17
            height = 24
            scroller_height = count * height + padding
            if scroller_height > 500:
                scroller_height = 500
            scroller.set_size_request(-1, scroller_height)

        self.popover.connect("closed", self.__on_popover_close)

        self.popover.add(scroller)
        scroller.add_with_viewport(self.track_box)
        scroller.show_all()

        self._mark_current_track()

    def __on_button_press(self, eventbox, event):
        self.art.selected = True
        if Gtk.get_minor_version() > 20:
            self.popover.popup()
        else:
            self.popover.show_all()
        pass

    def __on_popover_close(self, popover):
        """
        On popover close deselect this element and hide the overlay.
        """
        self.art.selected = False
        self.art._on_leave_notify(None, None)

    def _mark_current_track(self):
        """
        Mark the current track position in the popover.
        """
        book = Book.select().where(Book.id == self.book.id).get()

        if book.position < 1:
            return

        for track_element in self.track_box.get_children():
            if track_element.track.id == book.position:
                track_element.select()
            else:
                track_element.deselect()

    def set_playing(self, is_playing):
        if is_playing:
            self.art.play_button.set_from_resource(
                "/de/geigi/cozy/pause_background.svg")
        else:
            self.art.play_button.set_from_resource(
                "/de/geigi/cozy/play_background.svg")


class TrackElement(Gtk.EventBox):
    """
    An element to display a track in a book popover.
    """
    track = None
    selected = False
    ui = None

    def __init__(self, t, ui):
        self.track = t
        self.ui = ui

        super(Gtk.EventBox, self).__init__()
        self.connect("enter-notify-event", self._on_enter_notify)
        self.connect("leave-notify-event", self._on_leave_notify)
        self.connect("button-press-event", self.__on_button_press)
        self.set_tooltip_text(_("Play this track"))

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

        title_label.set_text((self.track.name[:MAX_TRACK_LENGTH] + '...') if len(
            self.track.name) > MAX_TRACK_LENGTH else self.track.name)
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
        current_track = get_current_track()

        if current_track is not None and current_track.id == self.track.id:
            play_pause(None)
            if get_gst_player_state() == Gst.State.PLAYING:
                jump_to_ns(Track.select().where(
                    Track.id == self.track.id).get().position)
        else:
            load_file(Track.select().where(Track.id == self.track.id).get())
            play_pause(None, True)
            Book.update(position=self.track).where(
                Book.id == self.track.book.id).execute()

    def _on_enter_notify(self, widget, event):
        """
        On enter notify add css hover class
        :param widget: as Gtk.EventBox
        :param event: as Gdk.Event
        """
        if self.ui.current_track_element is not self and not self.selected:
            self.play_img.set_from_icon_name(
                "media-playback-start-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        self.box.get_style_context().add_class("box_hover")
        self.play_img.get_style_context().add_class("box_hover")

    def _on_leave_notify(self, widget, event):
        """
        On leave notify remove css hover class
        :param widget: as Gtk.EventBox (can be None)
        :param event: as Gdk.Event (can be None)
        """
        self.box.get_style_context().remove_class("box_hover")
        self.play_img.get_style_context().remove_class("box_hover")
        if self.ui.current_track_element is not self and not self.selected:
            self.play_img.clear()

    def select(self):
        """
        Select this track as the current position of the audio book. 
        Permanently displays the play icon.
        """
        self.selected = True
        self.play_img.set_from_icon_name(
            "media-playback-start-symbolic", Gtk.IconSize.SMALL_TOOLBAR)

    def deselect(self):
        """
        Deselect this track.
        """
        self.selected = False
        self.play_img.clear()
