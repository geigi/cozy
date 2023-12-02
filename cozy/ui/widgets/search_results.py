from typing import Callable

from gi.repository import Adw, Gtk


class ArtistResultRow(Adw.ActionRow):
    def __init__(self, name: str, on_click: Callable[[str], None]) -> None:
        super().__init__(
            title=name,
            selectable=False,
            activatable=True,
            use_markup=False,
            tooltip_text=_("Jump to") + f" {name}",
        )

        self.connect("activated", lambda *_: on_click(name))

        icon = Gtk.Image.new_from_icon_name("account-symbolic")
        icon.set_pixel_size(36)
        icon.set_margin_top(6)
        icon.set_margin_bottom(6)

        self.add_prefix(icon)
