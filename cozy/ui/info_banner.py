import gi

from gi.repository import Gtk

from cozy.ext import inject


class InfoBanner:
    _builder: Gtk.Builder = inject.attr("MainWindowBuilder")

    def __init__(self):
        super(InfoBanner, self).__init__()

        self._toast: Gtk.InfoBar = self._builder.get_object("error_info_bar")
        self._label: Gtk.Label = self._builder.get_object("error_message_label")
        self._toast.connect("response", self._on_response)

    def show(self, message: str):
        self._label.set_text(message)
        self._toast.set_revealed(True)

    def _on_response(self, _, __):
        self._toast.set_revealed(False)
