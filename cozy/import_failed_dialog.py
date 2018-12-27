from gi.repository import Gtk

import cozy.ui


class ImportFailedDialog():
    """
    Dialog that displays failed files on import.
    """

    def __init__(self, files):
        self.parent = cozy.ui.CozyUI()
        self.builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/import_failed.ui")
        self.dialog = self.builder.get_object("dialog")
        self.dialog.set_transient_for(self.parent.window)
        self.text = self.builder.get_object("files_buffer")

        self.text.set_text(files)

        locate_button = self.builder.get_object("ok_button")
        locate_button.connect("clicked", self.ok)

    def show(self):
        """
        show this dialog
        """
        self.dialog.show()

    def ok(self, button):
        """
        Close this dialog and destroy it.
        """
        self.parent.dialog_open = False
        self.dialog.destroy()
