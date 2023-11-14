import gi

from cozy.ext import inject

from gi.repository import Adw


class DeleteBookView(Adw.MessageDialog):
    main_window = inject.attr("MainWindow")

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

        self.connect("response", callback, book)
        self.present()

