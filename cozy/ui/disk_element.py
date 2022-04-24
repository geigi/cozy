from gi.repository import Gtk

class DiskElement(Gtk.Box):
    """
    This class represents a small disk number header for the book overview track list.
    """
    disc_number = None
    container = None

    def __init__(self, disc_number):
        super().__init__()
        self.container = Gtk.Box()

        self.disc_number = disc_number
        if disc_number > 1:
            self.container.set_margin_top(18)

        self.container.set_margin_bottom(3)
        self.container.set_margin_start(5)
        self.container.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.container.get_style_context().add_class("dim-label")

        image = Gtk.Image.new_from_icon_name("media-optical-cd-audio-symbolic")
        self.container.add(image)
        label = Gtk.Label()
        label.set_margin_start(5)
        text = _("Disc") + " " + str(disc_number)
        label.set_markup("<b>" + text + "</b>")
        self.container.add(label)
        self.add(self.container)
