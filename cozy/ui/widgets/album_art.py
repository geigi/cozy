import math

import cairo
from gi.repository import Gtk, GdkPixbuf, Gdk

RADIUS = 5


class AlbumArt(Gtk.DrawingArea):
    def __init__(self, **properties):
        super().__init__(**properties)

        self.art = None

        self.set_visible(True)
        self.set_draw_func(self._on_draw)

    def set_art(self, art: GdkPixbuf):
        self.art = art
        scale = self.get_scale_factor()
        self.set_size_request(art.get_width() / scale, art.get_height() / scale)
        self.queue_draw()

    def _draw_rounded_path(self, context: cairo.Context):
        degrees = math.pi / 180.0

        context.new_sub_path()
        context.arc(self.width - RADIUS, RADIUS, RADIUS, -90 * degrees, 0 * degrees)
        context.arc(self.width - RADIUS, self.height - RADIUS, RADIUS, 0 * degrees, 90 * degrees)
        context.arc(RADIUS, self.height - RADIUS, RADIUS, 90 * degrees, 180 * degrees)
        context.arc(RADIUS, RADIUS, RADIUS, 180 * degrees, 270 * degrees)
        context.close_path()

    def _on_draw(self, area: Gtk.DrawingArea, context: cairo.Context):
        self.height = area.get_allocated_height()
        self.width = area.get_allocated_width()

        self._draw_rounded_path(context)

        if self.art:
            surface = Gdk.cairo_surface_create_from_pixbuf(self.art, self.get_scale_factor(), None)
            context.set_source_surface(surface, 0, 0)
            context.clip()

        context.paint()
        return False
