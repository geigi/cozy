import gi

from cozy.ext import inject

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk


@Gtk.Template(resource_path='/com/github/geigi/cozy/delete_book_dialog.ui')
class DeleteBookView(Gtk.Dialog):
    __gtype_name__ = 'DeleteBookDialog'

    main_window = inject.attr("MainWindow")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_modal(self.main_window.window)

    def get_delete_book(self):
        response = self.run()

        if response == Gtk.ResponseType.APPLY:
            return True
        else:
            return False
