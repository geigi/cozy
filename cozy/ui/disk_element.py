from gi.repository import Gtk


class DiskElement(Gtk.Box):
    """
    This class represents a small disk number header for the book overview track list.
    """

    def __init__(self, disc_number):
        super().__init__()
        self.add_css_class("dim-label")

        if disc_number > 1:
            self.set_margin_top(18)
        self.set_margin_bottom(3)
        self.set_margin_start(6)

        image = Gtk.Image.new_from_icon_name("media-optical-cd-audio-symbolic")
        self.append(image)

        label = Gtk.Label(margin_start=5)
        text = _("Disc") + " " + str(disc_number)  # TODO: use formatted translation string here
        label.set_markup(f"<b>{text}</b>")
        self.append(label)

