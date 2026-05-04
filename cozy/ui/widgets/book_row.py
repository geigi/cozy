from typing import Callable
from gi.repository import Adw, Gtk, GObject
from cozy.control.artwork_cache import ArtworkCache
from cozy.ext import inject
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

        self._book = book
        self._cover_loaded = False

        if on_click is not None:
            self.connect("activated", lambda *_: on_click(book))
            self.set_activatable(True)
            self.set_tooltip_text(_("Play this book"))

        # Set placeholder - cover will be loaded on realize when scale factor is available
        self._album_art = Gtk.Image.new_from_icon_name("book-open-variant-symbolic")
        self._album_art.set_pixel_size(BOOK_ICON_SIZE)
        self._album_art.set_size_request(BOOK_ICON_SIZE, BOOK_ICON_SIZE)
        self._album_art.set_margin_top(6)
        self._album_art.set_margin_bottom(6)

        self.add_prefix(self._album_art)
        self.connect("realize", self._load_cover_on_realize)

    def _load_cover_on_realize(self, widget):
        """Load cover image after widget is realized to get correct scale factor."""
        if self._cover_loaded:
            return
        self._cover_loaded = True

        paintable = self._artwork_cache.get_cover_paintable(
            self._book, self.get_scale_factor(), BOOK_ICON_SIZE
        )
        if paintable:
            # Replace the placeholder with the actual cover
            self.remove(self._album_art)
            album_art = Gtk.Picture.new_for_paintable(paintable)
            album_art.add_css_class("round-6")
            album_art.set_overflow(True)
            album_art.set_size_request(BOOK_ICON_SIZE, BOOK_ICON_SIZE)
            album_art.set_margin_top(6)
            album_art.set_margin_bottom(6)
            self.add_prefix(album_art)
            self._album_art = album_art
