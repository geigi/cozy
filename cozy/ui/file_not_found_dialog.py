import os

from gi.repository import Gtk

import cozy.ui
from cozy.ext import inject
from cozy.media.importer import Importer
from cozy.model.chapter import Chapter
from cozy.model.library import Library


class FileNotFoundDialog():
    _importer: Importer = inject.attr(Importer)
    _library: Library = inject.attr(Library)


    def __init__(self, chapter: Chapter):
        self.missing_chapter = chapter
        self.parent = cozy.ui.main_view.CozyUI()
        self.builder = Gtk.Builder.new_from_resource(
            "/com/github/geigi/cozy/file_not_found.ui")
        self.dialog: Gtk.Dialog = self.builder.get_object("dialog")
        self.dialog.set_modal(self.parent.window)
        self.dialog.set_transient_for(self.parent.window)
        self.builder.get_object("file_label").set_markup(
            "<tt>" + chapter.file + "</tt>")

        cancel_button = self.builder.get_object("cancel_button")
        cancel_button.connect("clicked", self.close)
        locate_button = self.builder.get_object("locate_button")
        locate_button.connect("clicked", self.locate)

    def show(self):
        self.dialog.show()

    def close(self, _):
        self.dialog.destroy()

    def locate(self, __):
        dialog = Gtk.FileChooserNative()
        dialog.set_transient_for(self.dialog)

        path, file_extension = os.path.splitext(self.missing_chapter.file)
        filter = Gtk.FileFilter()
        filter.add_pattern("*" + file_extension)
        filter.set_name(file_extension + " files")
        dialog.add_filter(filter)
        filter = Gtk.FileFilter()
        filter.add_pattern("*")
        filter.set_name(_("All files"))
        dialog.add_filter(filter)

        response = dialog.show()
        if response == Gtk.ResponseType.OK:
            new_location = dialog.get_filename()
            self.missing_chapter.file = new_location
            self._importer.scan()
            self.dialog.destroy()

        dialog.destroy()
