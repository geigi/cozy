import os, subprocess
from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, Gst

import cozy.db as db
import cozy.player as player
import cozy.tools as tools
import cozy.artwork_cache as artwork_cache

MAX_BOOK_LENGTH = 60
MAX_TRACK_LENGTH = 40


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

        self.book = book
        self.selected = False
        self.signal_ids = []
        self.play_signal_ids = []

        # the event box is used for mouse enter and leave signals
        self.event_box = Gtk.EventBox()
        self.event_box.set_property("halign", Gtk.Align.CENTER)
        self.event_box.set_property("valign", Gtk.Align.CENTER)

        # scale the book cover to a fix size.
        pixbuf = artwork_cache.get_cover_pixbuf(book, scale, size)

        # box is the main container for the album art
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)

        # img contains the album art
        img = Gtk.Image()
        img.set_halign(Gtk.Align.CENTER)
        img.set_valign(Gtk.Align.CENTER)
        if bordered:
            img.get_style_context().add_class("bordered")
        surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, scale, None)
        img.set_from_surface(surface)

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
        # we want to change the mouse cursor if the user is hovering over the play button

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
            return

        track = db.get_track_for_playback(self.book)
        current_track = player.get_current_track()

        if current_track and current_track.book.id == self.book.id:
            player.play_pause(None)
            if player.get_gst_player_state() == Gst.State.PLAYING:
                player.jump_to_ns(track.position)
        else:
            player.load_file(track)
            player.play_pause(None, True)

        return True


class BookElement(Gtk.FlowBoxChild):
    """
    This class represents a book with big artwork in the book viewer.
    """
    book = None
    ui = None
    selected = False
    wait_to_seek = False
    playing = False
    track_box = None
    current_track_element = None
    context_menu = None

    def __init__(self, b, ui):
        self.book = b
        self.ui = ui

        super().__init__()
        self.box = Gtk.Box()
        self.box.set_orientation(Gtk.Orientation.VERTICAL)
        self.box.set_spacing(7)
        self.box.set_halign(Gtk.Align.CENTER)
        self.box.set_valign(Gtk.Align.START)
        self.box.set_margin_top(10)
        self.box.set_tooltip_text(_("Open book overview"))

        # label contains the book name and is limited to x chars
        title_label = Gtk.Label.new("")
        title = tools.shorten_string(self.book.name, MAX_BOOK_LENGTH)
        title_label.set_markup("<b>" + title + "</b>")
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

        # assemble finished element
        self.box.add(self.art)
        self.box.add(title_label)
        self.box.add(author_label)
        self.add(self.box)

        self.connect("button-press-event", self.__on_button_press_event)

    def get_book(self):
        """
        Get this book element with the newest values from the db.
        """
        return db.Book.select().where(db.Book.id == self.book.id).get()

    def set_playing(self, is_playing):
        """
        Set the UI to play/pause.
        """
        if is_playing:
            self.art.play_button.set_from_icon_name(
                "media-playback-pause-symbolic", self.art.icon_size)
        else:
            self.art.play_button.set_from_icon_name(
                "media-playback-start-symbolic", self.art.icon_size)

    def refresh_book_object(self):
        """
        Refresh the internal book object from the database.
        """
        self.book = db.Book.get_by_id(self.book.id)

    def __on_button_press_event(self, widget, event):
        """
        Handle button press events.
        This is used for the right click context menu.
        """
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            if self.context_menu is None:
                self.context_menu = self.__create_context_menu()
            self.context_menu.popup(
                None, None, None, None, event.button, event.time)
            return True

    def __create_context_menu(self):
        """
        Creates a context menu for this book element.
        """
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
        menu.attach_to_widget(self.ui.window)
        menu.show_all()
        return menu

    def __remove_book(self, widget, parameter):
        """
        Adds all tracks of a book to the blacklist and removes it from the library.
        """
        db.blacklist_book(self.book)
        self.ui.settings.blacklist_model.clear()
        self.ui.settings._init_blacklist()
        self.ui.refresh_content()

    def __mark_as_read(self, widget, parameter):
        """
        Marks a book as read.
        """
        db.Book.update(position=-1).where(db.Book.id == self.book.id).execute()

    def __jump_to_folder(self, widget, parameter):
        """
        Opens the folder containing this books files in the default file explorer.
        """
        track = db.tracks(self.book).first()
        path = os.path.dirname(track.file)
        subprocess.Popen(['xdg-open', path])


class TrackElement(Gtk.EventBox):
    """
    An element to display a track in a book popover.
    """
    track = None
    selected = False
    ui = None
    book = None

    def __init__(self, t, ui, book):
        self.track = t
        self.ui = ui
        self.book = book

        super().__init__()
        self.connect("enter-notify-event", self._on_enter_notify)
        self.connect("leave-notify-event", self._on_leave_notify)
        self.connect("button-press-event", self.__on_button_press)
        self.set_tooltip_text(_("Play this part"))
        self.props.width_request = 400

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

        dur_label.set_text(tools.seconds_to_str(self.track.length))
        dur_label.set_halign(Gtk.Align.END)
        dur_label.props.margin = 4
        dur_label.set_margin_left(60)

        self.box.add(self.play_img)
        self.box.add(no_label)
        self.box.pack_start(title_label, True, True, 0)
        self.box.pack_end(dur_label, False, False, 0)

        self.add(self.box)

    def __on_button_press(self, eventbox, event):
        """
        Play the selected track.
        """
        current_track = player.get_current_track()

        if current_track and current_track.id == self.track.id:
            player.play_pause(None)
            if player.get_gst_player_state() == Gst.State.PLAYING:
                player.jump_to_ns(db.Track.select().where(
                    db.Track.id == self.track.id).get().position)
        else:
            player.load_file(db.Track.select().where(db.Track.id == self.track.id).get())
            player.play_pause(None, True)
            db.Book.update(position=self.track).where(
                db.Book.id == self.track.book.id).execute()

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
        self.book.deselect_track_element()
        self.selected = True
        self.play_img.set_from_icon_name(
            "media-playback-start-symbolic", Gtk.IconSize.SMALL_TOOLBAR)

    def deselect(self):
        """
        Deselect this track.
        """
        self.selected = False
        self.play_img.clear()

    def set_playing(self, playing):
        """
        Update the icon of this track
        :param playing: Is currently playing?
        """
        if playing:
            self.play_img.set_from_icon_name(
                "media-playback-pause-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        else:
            self.play_img.set_from_icon_name(
                "media-playback-start-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
