from gi.repository import Gtk, Pango


class ListBoxRowWithData(Gtk.ListBoxRow):
    """
    This class represents a listboxitem for an author/reader.
    """
    LABEL_MARGIN = 8
    ROW_MARGIN = 4

    def __init__(self, data, bold=False, **properties):
        super().__init__(**properties)
        self.data = data

        self.set_margin_top(self.ROW_MARGIN)
        self.set_margin_bottom(self.ROW_MARGIN)
        self.set_margin_start(self.ROW_MARGIN)
        self.set_margin_end(self.ROW_MARGIN)

        self.get_style_context().add_class("filter-list-box-row")

        label: Gtk.Label = Gtk.Label.new(data)
        if bold:
            label.set_markup("<b>" + data + "</b>")
        label.set_xalign(0.0)
        label.set_margin_top(self.LABEL_MARGIN)
        label.set_margin_bottom(self.LABEL_MARGIN)
        label.set_margin_start(7)
        label.set_max_width_chars(30)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        self.add(label)
        self.set_tooltip_text(data)
