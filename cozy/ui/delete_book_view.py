import inject
from gi.repository import Adw, Gtk

from cozy.model.book import Book
from cozy.ui.widgets.book_row import BookRow


class DeleteBookView(Adw.AlertDialog):
    main_window = inject.attr("MainWindow")

    def __init__(self, callback, book: Book):
        super().__init__(
            heading=_("Remove Audiobook From Library?"),
            body=_("This audiobook will be removed from Cozy's library. To be able to listen to it again, you will need to remove, and re-add its storage location."),
            default_response="cancel",
            close_response="cancel",
        )

        self.add_response("cancel", _("Cancel"))
        self.add_response("remove", _("Remove"))
        self.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)

        list_box = Gtk.ListBox(margin_top=12, css_classes=["boxed-list"])
        list_box.append(BookRow(book))
        self.set_extra_child(list_box)

        self.connect("response", callback, book)

    def present(self) -> None:
        super().present(self.main_window.window)
