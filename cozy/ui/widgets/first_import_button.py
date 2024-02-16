from gi.repository import Adw, Gtk, GObject

from .storages import ask_storage_location

from typing import Callable


@Gtk.Template.from_resource('/com/github/geigi/cozy/first_import_button.ui')
class FirstImportButton(Gtk.Button):
    __gtype_name__ = "FirstImportButton"

    stack: Gtk.Stack = Gtk.Template.Child()
    label: Adw.ButtonContent = Gtk.Template.Child()
    spinner: Gtk.Spinner = Gtk.Template.Child()

    def __init__(self, callback: Callable[[str], None], initial_folder: str) -> None:
        super().__init__()

        self.connect("clicked", lambda *_: ask_storage_location(callback, initial_folder))

    def disable(self) -> None:
        self.set_sensitive(False)
        self.spinner.set_spinning(True)
        self.stack.set_visible_child(self.spinner)
