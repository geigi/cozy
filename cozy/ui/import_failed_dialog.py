from gi.repository import Gtk

import cozy.ui


class ImportFailedDialog():
    """
    Dialog that displays failed files on import.
    """

    def __init__(self, files):
        self.parent = cozy.ui.main_view.CozyUI()
        self.builder = Gtk.Builder.new_from_resource(
            "/com/github/geigi/cozy/import_failed.ui")
        self.dialog = self.builder.get_object("dialog")
        self.dialog.set_transient_for(self.parent.window)
        self.text = self.builder.get_object("files_buffer")

        files_string = "\n".join(files)
        self.text.set_text(files_string.encode("utf-8", "replace").decode("utf-8"))

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
