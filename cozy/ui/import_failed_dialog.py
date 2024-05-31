from gettext import gettext as _

from gi.repository import Adw, Gtk

from cozy.ext import inject

HEADER = _("This can have multiple reasons:")
POSSIBILITIES = "\n     • ".join((  # yes, it is a hack, because \t would be too wide
    "",
    _("The audio format is not supported"),
    _("The path or filename contains non utf-8 characters"),
    _("The file(s) are no valid audio files"),
    _("The file(s) are corrupt"),
))

message = HEADER + POSSIBILITIES


class ImportFailedDialog(Adw.AlertDialog):
    """
    Dialog that displays failed files on import.
    """
    main_window = inject.attr("MainWindow")

    def __init__(self, files: list[str]):
        super().__init__(
            heading=_("Some files could not be imported"),
            default_response="cancel",
            close_response="cancel",
        )

        self.add_response("cancel", _("Ok"))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        body_label = Gtk.Label(label=message)

        text_buffer = Gtk.TextBuffer(
            text="\n".join(files).encode("utf-8", errors="replace").decode("utf-8")
        )
        text_view = Gtk.TextView(
            buffer=text_buffer,
            editable=False,
            cursor_visible=False,
            css_classes=["card", "failed-import-card", "monospace"]
        )

        scroller = Gtk.ScrolledWindow(
            max_content_height=200,
            propagate_natural_height=True,
            child=text_view
        )

        box.append(body_label)
        box.append(scroller)
        self.set_extra_child(box)

    def present(self) -> None:
        super().present(self.main_window.window)

