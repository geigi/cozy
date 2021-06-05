import logging
import math

import cairo

from cozy.control.artwork_cache import ArtworkCache
from cozy.extensions.gtk_widget import set_hand_cursor
from cozy.model.book import Book
from cozy.ext import inject

from gi.repository import Gtk, GObject, Gdk

ALBUM_ART_SIZE = 200
PLAY_BUTTON_ICON_SIZE = Gtk.IconSize.SMALL_TOOLBAR
STROKE_WIDTH = 2

log = logging.getLogger("album_element")


@Gtk.Template.from_resource('/com/github/geigi/cozy/album_element.ui')
class AlbumElement(Gtk.Box):
    __gtype_name__ = "AlbumElement"

    artwork_cache: ArtworkCache = inject.attr(ArtworkCache)

    button_image: Gtk.Image = Gtk.Template.Child()
    album_art_image: Gtk.Image = Gtk.Template.Child()
    play_button: Gtk.Button = Gtk.Template.Child()
    progress_drawing_area: Gtk.DrawingArea = Gtk.Template.Child()
    album_art_drawing_area: Gtk.DrawingArea = Gtk.Template.Child()
    album_art_overlay_revealer: Gtk.Revealer = Gtk.Template.Child()
    play_button_revealer: Gtk.Revealer = Gtk.Template.Child()

    def __init__(self, book: Book):
        super().__init__()

        self._book: Book = book
        pixbuf = self.artwork_cache.get_cover_pixbuf(book, self.get_scale_factor(), ALBUM_ART_SIZE)

        if pixbuf:
            self.album_art_image.set_from_pixbuf(pixbuf)
        else:
            self.album_art_image.set_from_icon_name("book-open-variant-symbolic", Gtk.IconSize.DIALOG)
            self.album_art_image.props.pixel_size = ALBUM_ART_SIZE

        self.play_button.connect("button-release-event", self._on_play_button_press)

        self.progress_drawing_area.connect("draw", self._draw_progress)
        self.album_art_drawing_area.connect("draw", self._draw_album_hover)
        self.album_art_overlay_revealer.connect("enter-notify-event", self._on_revealer_enter_event)
        self.play_button_revealer.connect("enter-notify-event", self._on_revealer_enter_event)

    def set_playing(self, playing: bool):
        if playing:
            self.button_image.set_from_icon_name("media-playback-pause-symbolic", PLAY_BUTTON_ICON_SIZE)
        else:
            self.button_image.set_from_icon_name("media-playback-start-symbolic", PLAY_BUTTON_ICON_SIZE)

    def set_hover(self, hover: bool):
        self.album_art_overlay_revealer.set_reveal_child(hover)
        self.play_button_revealer.set_reveal_child(hover)

    def _on_play_button_press(self, _, __):
        self.emit("play-pause-clicked", self._book)
        return True

    def _draw_album_hover(self, area: Gtk.DrawingArea, context: cairo.Context):
        context.rectangle(0, 0, area.get_allocated_width(), area.get_allocated_height())
        context.set_source_rgba(1, 1, 1, 0.15)
        context.fill()

    def _draw_progress(self, area: Gtk.DrawingArea, context: cairo.Context):
        width = area.get_allocated_width()
        height = area.get_allocated_height()
        button_size = self.play_button.get_allocated_width()
        self.radius = (button_size + STROKE_WIDTH) / 2.0

        self.draw_background(area, context)

        book_progress = self._book.progress / self._book.duration

        progress_circle_end = book_progress * math.pi * 2.0
        context.arc(width / 2.0, height / 2.0, self.radius, math.pi * -0.5,
                    progress_circle_end - (math.pi * 0.5))
        if book_progress == 1.0:
            context.set_source_rgb(0.2, 0.82, 0.478)
        else:
            context.set_source_rgb(0.894, 0.471, 0.208)
        context.set_line_width(2)
        context.stroke()

    def draw_background(self, area: Gtk.DrawingArea, context: cairo.Context):
        width = area.get_allocated_width()
        height = area.get_allocated_height()

        context.arc(width / 2.0, height / 2.0, self.radius, 0, math.pi * 2.0)
        context.set_source_rgba(0, 0, 0, 0.5)
        context.set_line_width(2)
        context.stroke()

    def update_progress(self):
        self.progress_drawing_area.queue_draw()

    def _on_revealer_enter_event(self, widget, _):
        # Somehow the GTK Revealer steals the mouse events from the parent
        # Maybe this is a bug in GTK but for now we have to handle hover in here as well
        self.set_hover(True)
        set_hand_cursor(widget)
        return True


GObject.type_register(AlbumElement)
GObject.signal_new('play-pause-clicked', AlbumElement, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))
