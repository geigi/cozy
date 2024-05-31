from gi.repository import Adw, Gtk

from cozy.ext import inject
from cozy.model.book import Book
from cozy.ui.widgets.book_row import BookRow


class DeleteBookView(Adw.AlertDialog):
    main_window = inject.attr("MainWindow")

    def __init__(self, callback, book: Book):
        super().__init__(
            heading=_("Delete Audiobook?"),
            body=_("The audiobook will be removed from your disk and from Cozy's library."),
            default_response="cancel",
            close_response="cancel",
        )

        self.add_response("cancel", _("Cancel"))
        self.add_response("delete", _("Remove Audiobook"))
        self.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        list_box = Gtk.ListBox(margin_top=12, css_classes=["boxed-list"])
        list_box.append(BookRow(book))
        self.set_extra_child(list_box)

        self.connect("response", callback, book)

    def present(self) -> None:
        super().present(self.main_window.window)
