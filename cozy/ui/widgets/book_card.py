from math import pi as PI

import cairo
import inject
from gi.repository import Gdk, Gio, GLib, GObject, Graphene, Gtk

from cozy.control.artwork_cache import ArtworkCache
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


@Gtk.Template.from_resource("/com/github/geigi/cozy/ui/book_card.ui")
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

    first_menu_section: Gio.MenuModel = Gtk.Template.Child()
    second_menu_section: Gio.MenuModel = Gtk.Template.Child()

    artwork_cache: ArtworkCache = inject.attr(ArtworkCache)

    __gsignals__ = {
        "play-pause-clicked": (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (object,)),
        "open-book-overview": (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (object,)),
        "jump-to-folder": (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (object,)),
        "remove-book": (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (object,)),
    }

    def __init__(self, book: Book):
        super().__init__()

        self.book = book
        self.title = book.name
        self.author = book.author

        paintable = self.artwork_cache.get_cover_paintable(
            book, self.get_scale_factor(), ALBUM_ART_SIZE
        )

        if paintable:
            self.artwork.set_paintable(paintable)
            self.artwork.set_size_request(ALBUM_ART_SIZE, ALBUM_ART_SIZE)
            self.stack.set_visible_child(self.artwork)
        else:
            self.fallback_icon.set_from_icon_name("cozy.book-open-symbolic")
            self.stack.set_visible_child(self.fallback_icon)

        self.menu_button.connect("notify::active", self._on_leave)
        self.set_cursor(Gdk.Cursor.new_from_name("pointer"))

        self._install_event_controllers()

        self.book.bind_to("position", self._on_position_updated)

        self._setup_menu()

    def _setup_menu(self):
        remove_recents_item = Gio.MenuItem.new(_("Remove from Recents"))
        open_in_files_item = Gio.MenuItem.new(_("Open in Files"))
        remove_item = Gio.MenuItem.new(_("Remove from Library"))

        remove_recents_item.set_action_and_target_value(
            "app.reset_book", GLib.Variant.new_int16(self.book.id)
        )
        open_in_files_item.set_action_and_target_value(
            "app.jump_to_book_folder", GLib.Variant.new_int16(self.book.id)
        )
        remove_item.set_action_and_target_value(
            "app.remove_book", GLib.Variant.new_int16(self.book.id)
        )

        self.first_menu_section.append_item(remove_recents_item)
        self.first_menu_section.append_item(open_in_files_item)
        self.second_menu_section.append_item(remove_item)

        self.mark_read_item = Gio.MenuItem.new(_("Mark as Read"))
        self.mark_read_item.set_action_and_target_value(
            "app.mark_book_as_read", GLib.Variant.new_int16(self.book.id)
        )

        self.mark_unread_item = Gio.MenuItem.new(_("Mark as Unread"))
        self.mark_unread_item.set_action_and_target_value(
            "app.mark_book_as_unread", GLib.Variant.new_int16(self.book.id)
        )

        self._on_position_updated(remove_first_menu_item=False)

    def _install_event_controllers(self):
        hover_controller = Gtk.EventControllerMotion()
        hover_controller.connect("enter", self._on_enter)
        hover_controller.connect("leave", self._on_leave)

        long_press_gesture = Gtk.GestureLongPress()
        long_press_gesture.connect("pressed", self._on_long_tap)

        self.add_controller(hover_controller)
        self.add_controller(long_press_gesture)

    def set_playing(self, is_playing):
        self.play_button.set_playing(is_playing)

    @Gtk.Template.Callback()
    def _play_pause(self, *_):
        self.emit("play-pause-clicked", self.book)

    @Gtk.Template.Callback()
    def _open_book_overview(self, *_):
        self.emit("open-book-overview", self.book)

    def _on_enter(self, *_) -> None:
        self.play_revealer.set_reveal_child(True)
        self.menu_revealer.set_reveal_child(True)

    def _on_leave(self, *_) -> None:
        if not self.menu_button.get_active():
            self.play_revealer.set_reveal_child(False)
            self.menu_revealer.set_reveal_child(False)

    def _on_long_tap(self, gesture: Gtk.Gesture, *_):
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

        device = gesture.get_device()
        if device and device.get_source() == Gdk.InputSource.TOUCHSCREEN:
            self.menu_button.emit("activate")

    def update_progress(self):
        if self.book.duration:
            self.play_button.progress = self.book.progress / self.book.duration

    def _on_position_updated(self, *, remove_first_menu_item: bool = True) -> None:
        self.update_progress()

        if remove_first_menu_item:
            self.first_menu_section.remove(0)

        if self.book.position == -1:
            self.first_menu_section.prepend_item(self.mark_unread_item)
        else:
            self.first_menu_section.prepend_item(self.mark_read_item)
