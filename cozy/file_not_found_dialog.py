import os

from cozy.db import *
from cozy.player import *
from gi.repository import Gtk


class FileNotFoundDialog():
    """
    Dialog that prompts the user to update a files location.
    """

    def __init__(self, file, parent):
        self.missing_file = file
        self.parent = parent
        self.builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/file_not_found.ui")
        self.dialog = self.builder.get_object("dialog")
        self.builder.get_object("file_label").set_markup(
            "<tt>" + file + "</tt>")

        cancel_button = self.builder.get_object("cancel_button")
        cancel_button.connect("clicked", self.close)
        locate_button = self.builder.get_object("locate_button")
        locate_button.connect("clicked", self.locate)

    def show(self):
        """
        show this dialog
        """
        self.dialog.show()

    def close(self, button):
        """
        Close this dialog and destroy it.
        """
        self.parent.dialog_open = False
        self.dialog.destroy()
        stop()
        get_playbin().set_state(Gst.State.NULL)
        emit_event("stop")

    def locate(self, button):
        """
        Locate the file and update the database if the user selected one.
        """
        filename = os.path.basename(self.missing_file)
        dialog = Gtk.FileChooserDialog("Please locate the file " + filename, self.parent.window,
                                       Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        path, file_extension = os.path.splitext(self.missing_file)
        filter = Gtk.FileFilter()
        filter.add_pattern("*" + file_extension)
        filter.set_name(file_extension + " files")
        dialog.add_filter(filter)
        dialog.set_local_only(False)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_location = dialog.get_filename()
            Track.update(file=new_location).where(
                Track.file == self.missing_file).execute()
            self.dialog.destroy()
            load_file(Track.select().where(Track.file == new_location).get())
            play_pause(None, True)

        dialog.destroy()
