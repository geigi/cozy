from math import pi as PI

import cairo
from gi.repository import Gdk, Gio, GObject, Graphene, Gtk

from cozy.control.artwork_cache import ArtworkCache
from cozy.ext import inject
from cozy.model.book import Book

ALBUM_ART_SIZE = 200
STROKE_WIDTH = 4


class BookCardPlayButton(Gtk.Button):
    __gtype_name__ = "BookCardPlayButton"

    progress = GObject.Property(type=float, default=0.0)

    def __init__(self) -> None:
        super().__init__()

        self.connect("notify::progress", self.redraw)

    def redraw(self, *_) -> None:
        self.queue_draw()

    def set_playing(self, playing: bool):
        if playing:
            self.set_icon_name("media-playback-pause-symbolic")
        else:
            self.set_icon_name("media-playback-start-symbolic")

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        Gtk.Button.do_snapshot(self, snapshot)

        if self.progress == 0.0:
            return

        size = self.get_allocated_height()
        radius = (size - STROKE_WIDTH) / 2.0

        context = snapshot.append_cairo(Graphene.Rect().init(0, 0, size, size))

        context.set_source_rgb(1.0, 1.0, 1.0)
        context.set_line_width(STROKE_WIDTH)
        context.set_line_cap(cairo.LineCap.ROUND)

        context.arc(size / 2, size / 2, radius, -0.5 * PI, self.progress * 2 * PI - (0.5 * PI))
        context.stroke()


@Gtk.Template.from_resource('/com/github/geigi/cozy/ui/book_card.ui')
class BookCard(Gtk.FlowBoxChild):
    __gtype_name__ = "BookCard"

    title = GObject.Property(type=str, default=_("Unknown"))
    author = GObject.Property(type=str, default=_("Unknown"))

    artwork: Gtk.Picture = Gtk.Template.Child()
    fallback_icon: Gtk.Image = Gtk.Template.Child()
    stack: Gtk.Stack = Gtk.Template.Child()
    button: Gtk.Stack = Gtk.Template.Child()
    menu_button: Gtk.MenuButton = Gtk.Template.Child()
    play_revealer: Gtk.Revealer = Gtk.Template.Child()
    menu_revealer: Gtk.Revealer = Gtk.Template.Child()
    play_button: BookCardPlayButton = Gtk.Template.Child()

    artwork_cache: ArtworkCache = inject.attr(ArtworkCache)

    __gsignals__ = {
        "play-pause-clicked": (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (object,)),
        "open-book-overview": (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (object,)),
        "remove-book": (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (object,)),
    }

    def __init__(self, book: Book):
        super().__init__()

        self.book = book

        self.title = book.name
        self.author = book.author

        paintable = self.artwork_cache.get_cover_paintable(book, 1, ALBUM_ART_SIZE)

        if paintable:
            self.artwork.set_paintable(paintable)
            self.artwork.set_size_request(ALBUM_ART_SIZE, ALBUM_ART_SIZE)
            self.stack.set_visible_child(self.artwork)
        else:
            self.fallback_icon.set_from_icon_name("book-open-variant-symbolic")
            self.stack.set_visible_child(self.fallback_icon)

        self.menu_button.connect("notify::active", self._on_leave)
        self.set_cursor(Gdk.Cursor.new_from_name("pointer"))

        self._install_event_controllers()
        self.update_progress()

    def _install_event_controllers(self):
        hover_controller = Gtk.EventControllerMotion()
        hover_controller.connect("enter", self._on_enter)
        hover_controller.connect("leave", self._on_leave)

        long_press_gesture = Gtk.GestureLongPress()
        long_press_gesture.connect("pressed", self._on_long_tap)

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect("key-pressed", self._on_key_press_event)

        self.add_controller(hover_controller)
        self.add_controller(long_press_gesture)
        self.add_controller(key_event_controller)

    def set_playing(self, is_playing):
        self.play_button.set_playing(is_playing)

    def update_progress(self):
        self.play_button.progress = self.book.progress / self.book.duration

    def remove(self) -> None:
        self.emit("remove-book", self.book)

    def mark_as_read(self) -> None:
        self.book.position = -1
        self.update_progress()

    def jump_to_folder(self) -> None:
        track = self.book.chapters[0]

        file_launcher = Gtk.FileLauncher(file=Gio.File.new_for_path(track.file))
        dummy_callback = lambda d, r: d.open_containing_folder_finish(r)
        file_launcher.open_containing_folder(None, None, dummy_callback)

    @Gtk.Template.Callback()
    def _play_pause(self, *_):
        self.emit("play-pause-clicked", self.book)

    @Gtk.Template.Callback()
    def _open_book_overview(self, *_):
        self.emit("open-book-overview", self.book)

    def _on_enter(self, *_) -> None:
        self.play_revealer.set_reveal_child(True)
        self.menu_revealer.set_reveal_child(True)

        inject.instance("GtkApp").selected_book = self

    def _on_leave(self, *_) -> None:
        if not self.menu_button.get_active():
            self.play_revealer.set_reveal_child(False)
            self.menu_revealer.set_reveal_child(False)

    def _on_long_tap(self, gesture: Gtk.Gesture, *_):
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

        device = gesture.get_device()
        if device and device.get_source() == Gdk.InputSource.TOUCHSCREEN:
            self.menu_button.emit("activate")

    def _on_key_press_event(self, controller, keyval, *_):
        if keyval == Gdk.KEY_Return:
            self.emit("open-book-overview", self.book)
