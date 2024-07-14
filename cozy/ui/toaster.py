from gi.repository import Adw, Gtk

import inject


class ToastNotifier:
    _builder: Gtk.Builder = inject.attr("MainWindowBuilder")

    def __init__(self) -> None:
        super().__init__()

        self.overlay: Adw.ToastOverlay = self._builder.get_object("toast_overlay")

    def show(self, message: str) -> None:
        self.overlay.add_toast(Adw.Toast(title=message, timeout=2))

