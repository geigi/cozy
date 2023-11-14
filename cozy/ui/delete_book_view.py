import gi

from cozy.ext import inject

from gi.repository import Gtk, Adw


@Gtk.Template(resource_path='/com/github/geigi/cozy/delete_book_dialog.ui')
class DeleteBookView(Adw.MessageDialog):
    __gtype_name__ = 'DeleteBookDialog'

    main_window = inject.attr("MainWindow")

    def __init__(self, callback, book):
        super().__init__(modal=True, transient_for=self.main_window.window)
        self.add_response("cancel", _("Cancel"))
        self.add_response("delete", _("Remove Audiobook"))
        self.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        self.connect("response", callback, book)
        self.present()

