import logging

import gi

from cozy.ui.media_controller_big import MediaControllerBig
from cozy.ui.media_controller_small import MediaControllerSmall

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Adw

log = logging.getLogger("MediaController")


class MediaController:
    def __init__(self, main_window_builder: Gtk.Builder):
        super().__init__()

        self._media_control_squeezer: Adw.Squeezer = main_window_builder.get_object("media_control_squeezer")
        self._media_controller_small: MediaControllerSmall = MediaControllerSmall()
        self._media_controller_big: MediaControllerBig = MediaControllerBig()
        self._media_control_squeezer.add(self._media_controller_big)
        self._media_control_squeezer.add(self._media_controller_small)
