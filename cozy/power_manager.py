import logging

import inject
from gi.repository import Gtk

from cozy.media.player import Player

log = logging.getLogger("power_mgr")


class PowerManager:
    _player: Player = inject.attr(Player)
    _gtk_app = inject.attr("GtkApp")

    def __init__(self):
        self._inhibit_cookie = None

        self._player.add_listener(self._on_player_changed)

    def _on_player_changed(self, event: str, data):
        if event in ["pause", "stop"]:
            if self._inhibit_cookie:
                log.info("Uninhibited standby.")
                self._gtk_app.uninhibit(self._inhibit_cookie)
                self._inhibit_cookie = None

        elif event == "play":
            if self._inhibit_cookie:
                return

            self._inhibit_cookie = self._gtk_app.inhibit(None, Gtk.ApplicationInhibitFlags.SUSPEND,
                                                         "Playback of audiobook")
            log.info("Inhibited standby.")
