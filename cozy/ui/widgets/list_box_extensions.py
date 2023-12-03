from gi.repository import Gtk


def remove_all_children(self):
    """
    Removes all widgets from a gtk widget.
    """
    self.set_visible(False)

    child = self.get_first_child()
    while child:
        next = child.get_next_sibling()
        self.remove(child)
        child = next

    self.set_visible(True)


def extend_gtk_container():
    Gtk.Widget.remove_all_children = remove_all_children
