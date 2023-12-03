from gi.repository import Adw, Gtk

from cozy.ext import inject
from cozy.control.artwork_cache import ArtworkCache


class DeleteBookView(Adw.MessageDialog):
    main_window = inject.attr("MainWindow")
    artwork_cache: ArtworkCache = inject.attr(ArtworkCache)

    def __init__(self, callback, book):
        super().__init__(
            heading=_("Delete Audiobook?"),
            body=_("The audiobook will be removed from your disk and from Cozy's library."),
            default_response="cancel",
            close_response="cancel",
            transient_for=self.main_window.window,
            modal=True,
        )

        self.add_response("cancel", _("Cancel"))
        self.add_response("delete", _("Remove Audiobook"))
        self.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        book_row = Adw.ActionRow(
            title=book.name,
            subtitle=book.author,
            selectable=False,
            use_markup=False,
        )
        album_art = Gtk.Picture(margin_top=6, margin_bottom=6)

        paintable = self.artwork_cache.get_cover_paintable(book, 1, 48)
        if paintable:
            album_art.set_paintable(paintable)
            book_row.add_prefix(album_art)

        list_box = Gtk.ListBox(margin_top=12, css_classes=["boxed-list"])
        list_box.append(book_row)
        self.set_extra_child(list_box)

        self.connect("response", callback, book)

