from gi.repository import Gtk, Gdk, GdkPixbuf, Gst, GObject

from cozy.control import artwork_cache as artwork_cache, player as player
from cozy.control.db import get_track_for_playback
from cozy.model.book import Book


class AlbumElement(Gtk.Box):
    """
    This class represents a clickable album art widget for a book.
    """

    def __init__(self, book, size, scale, bordered=False, square=False):
        """
        :param size: the size for the longer side of the image
        :param bordered: should there be a border around the album art?
        :param square: should the widget be always a square?
        """
        super().__init__()
        self.props.height_request = size

        self.book: Book = book
        self.selected = False
        self.signal_ids = []
        self.play_signal_ids = []

        # the event box is used for mouse enter and leave signals
        self.event_box = Gtk.EventBox()
        self.event_box.set_property("halign", Gtk.Align.CENTER)
        self.event_box.set_property("valign", Gtk.Align.CENTER)

        # scale the book cover to a fix size.
        pixbuf = artwork_cache.get_cover_pixbuf(book.db_object, scale, size)

        # box is the main container for the album art
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)

        # img contains the album art
        img = Gtk.Image()
        img.set_halign(Gtk.Align.CENTER)
        img.set_valign(Gtk.Align.CENTER)
        if pixbuf:
            if bordered:
                img.get_style_context().add_class("bordered")
            surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, scale, None)
            img.set_from_surface(surface)
        else:
            img.set_from_icon_name("book-open-variant-symbolic", Gtk.IconSize.DIALOG)
            img.props.pixel_size = size

        self.play_box = Gtk.EventBox()

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
        if size < 100:
            self.icon_size = Gtk.IconSize.LARGE_TOOLBAR
        else:
            self.icon_size = Gtk.IconSize.DIALOG
        self.play_button = Gtk.Image.new_from_icon_name(
            "media-playback-start-symbolic", self.icon_size)
        self.play_button.set_property("halign", Gtk.Align.CENTER)
        self.play_button.set_property("valign", Gtk.Align.CENTER)
        self.play_button.get_style_context().add_class("white")

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
        self.play_revealer.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK)
        self.play_revealer.add_events(Gdk.EventMask.LEAVE_NOTIFY_MASK)

        # this grid has a background color to act as a visible overlay
        color = Gtk.Grid()
        color.set_property("halign", Gtk.Align.CENTER)
        color.set_property("valign", Gtk.Align.CENTER)

        if square:
            self.set_size_request(size, size)

            smaller_width = size - pixbuf.get_width()
            if smaller_width > 1:
                self.event_box.set_margin_left(smaller_width / 2)

        # assemble play overlay
        self.play_box.add(self.play_button)
        self.play_overlay.add(self.play_box)

        # assemble overlay with album art
        self.overlay.add(img)
        self.overlay.add_overlay(self.play_revealer)

        # assemble overlay color
        color.add(self.overlay)
        self.event_box.add(color)
        self.add(self.event_box)

        # connect signals
        self.play_signal_ids.append(self.play_box.connect(
            "enter-notify-event", self._on_play_enter_notify))
        self.play_signal_ids.append(self.play_box.connect(
            "leave-notify-event", self._on_play_leave_notify))
        # connect mouse events to the event box
        self.signal_ids.append(self.event_box.connect(
            "enter-notify-event", self._on_enter_notify))
        self.signal_ids.append(self.event_box.connect(
            "leave-notify-event", self._on_leave_notify))

    def disconnect_signals(self):
        """
        Disconnect all signals from this element.
        """
        [self.event_box.disconnect(sig) for sig in self.signal_ids]
        [self.play_box.disconnect(sig) for sig in self.play_signal_ids]

    def _on_enter_notify(self, widget, event):
        """
        On enter notify change overlay opacity
        :param widget: as Gtk.EventBox
        :param event: as Gdk.Event
        """
        self.play_revealer.set_reveal_child(True)

    def _on_leave_notify(self, widget, event):
        """
        On leave notify change overlay opacity
        :param widget: as Gtk.EventBox (can be None)
        :param event: as Gdk.Event (can be None)
        """
        if not self.selected:
            self.play_revealer.set_reveal_child(False)

    def _on_play_enter_notify(self, widget, event):
        """
        Change the cursor to pointing hand
        """
        self.props.window.set_cursor(Gdk.Cursor.new_from_name(self.get_display(), "pointer"))

    def _on_play_leave_notify(self, widget, event):
        """
        Reset the cursor.
        """
        self.props.window.set_cursor(None)

    def _on_play_button_press(self, widget, event):
        """
        Play this book.
        """
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button != 1:
            return False

        self.emit("play-pause-clicked", self.book.db_object)
        track = get_track_for_playback(self.book.db_object)
        current_track = player.get_current_track()

        if current_track and current_track.book.db_object.id == self.book.db_object.id:
            player.play_pause(None)
            if player.get_gst_player_state() == Gst.State.PLAYING:
                player.jump_to_ns(track.position)
        else:
            player.load_file(track)
            player.play_pause(None, True)

        return True


GObject.type_register(AlbumElement)
GObject.signal_new('play-pause-clicked', AlbumElement, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))
