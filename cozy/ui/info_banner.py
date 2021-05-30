import gi

gi.require_version('Granite', '1.0')

from gi.repository import Gtk, Granite

from cozy.ext import inject


class InfoBanner:
    _builder: Gtk.Builder = inject.attr("MainWindowBuilder")

    def __init__(self):
        super(InfoBanner, self).__init__()

        self._overlay: Gtk.Overlay = self._builder.get_object("banner_overlay")
        self._toast: Granite.WidgetsToast = Granite.WidgetsToast.new("")
        self._toast.show_all()
        self._overlay.add_overlay(self._toast)
        self._banner_displayed: bool = False

    def show(self, message: str):
        self._toast.set_property("title", message)
        self._toast.set_reveal_child(True)
