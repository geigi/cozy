from typing import Callable

import inject
from gi.repository import Adw, Gtk

from cozy.control.artwork_cache import ArtworkCache
from cozy.model.book import Book

BOOK_ICON_SIZE = 52


class BookRow(Adw.ActionRow):
    _artwork_cache: ArtworkCache = inject.attr(ArtworkCache)

    def __init__(
        self, book: Book, on_click: Callable[[Book], None] | None = None
    ) -> None:
        super().__init__(
            title=book.name, subtitle=book.author, selectable=False, use_markup=False
        )

        if on_click is not None:
            self.connect("activated", lambda *_: on_click(book))
            self.set_activatable(True)
            self.set_tooltip_text(_("Play this book"))

        paintable = self._artwork_cache.get_cover_paintable(
            book, self.get_scale_factor(), BOOK_ICON_SIZE
        )
        if paintable:
            album_art = Gtk.Picture.new_for_paintable(paintable)
            album_art.add_css_class("round-6")
            album_art.set_overflow(True)
        else:
            album_art = Gtk.Image.new_from_icon_name("cozy.book-open-symbolic")
            album_art.set_pixel_size(BOOK_ICON_SIZE)

        album_art.set_size_request(BOOK_ICON_SIZE, BOOK_ICON_SIZE)
        album_art.set_margin_top(6)
        album_art.set_margin_bottom(6)

        clamp = Adw.Clamp(maximum_size=BOOK_ICON_SIZE)
        clamp.set_child(album_art)

        self.add_prefix(clamp)
