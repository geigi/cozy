import logging

from gi.repository import Gtk, Gdk

log = logging.getLogger("gtk_widget")


def set_hand_cursor(widget: Gtk.Widget):
    try:
        widget.props.window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
    except:
        log.error("Broken mouse theme, failed to set cursor.")


def reset_cursor(widget: Gtk.Widget):
    widget.props.window.set_cursor(None)
