from pathlib import Path

from gi.repository import Adw, Gio, GLib, Gtk

from cozy.ext import inject
from cozy.media.importer import Importer
from cozy.model.chapter import Chapter


class FileNotFoundDialog(Adw.AlertDialog):
    main_window = inject.attr("MainWindow")
    _importer: Importer = inject.attr(Importer)

    def __init__(self, chapter: Chapter):
        self.missing_chapter = chapter

        super().__init__(
            heading=_("File not found"),
            body=_("This file could not be found. Do you want to locate it manually?"),
            default_response="locate",
            close_response="cancel",
        )

        self.add_response("cancel", _("Cancel"))
        self.add_response("locate", _("Locate"))
        self.set_response_appearance("locate", Adw.ResponseAppearance.SUGGESTED)

        label = Gtk.Label(label=chapter.file, margin_top=12, wrap=True)
        label.add_css_class("monospace")
        self.set_extra_child(label)

        self.connect("response", self._on_locate)

    def _on_locate(self, __, response):
        if response == "locate":
            file_dialog = Gtk.FileDialog(title=_("Locate Missing File"))

            extension = Path(self.missing_chapter.file).suffix[1:]
            current_extension_filter = Gtk.FileFilter(name=_("{ext} files").format(ext=extension))
            current_extension_filter.add_suffix(extension)

            audio_files_filter = Gtk.FileFilter(name=_("Audio files"))
            audio_files_filter.add_mime_type("audio/*")

            filters = Gio.ListStore.new(Gtk.FileFilter)
            filters.append(current_extension_filter)
            filters.append(audio_files_filter)

            file_dialog.set_filters(filters)
            file_dialog.set_default_filter(current_extension_filter)
            file_dialog.open(self.main_window.window, None, self._file_dialog_open_callback)

    def _file_dialog_open_callback(self, dialog, result):
        try:
            file = dialog.open_finish(result)
        except GLib.GError:
            pass
        else:
            if file is not None:
                self.missing_chapter.file = file.get_path()
                self._importer.scan()

    def present(self) -> None:
        super().present(self.main_window.window)

