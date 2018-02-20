from cozy.event_sender import EventSender
import cozy.player as player
import cozy.db as db

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class PlaybackSpeed(EventSender):
    """
    Contains the playback speed logic.
    """
    ui = None
    speed = 1.0

    def __init__(self, ui):
        self.ui = ui

        self.builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/playback_speed_popover.ui")

        self.speed_scale = self.builder.get_object("playback_speed_scale")
        self.speed_label = self.builder.get_object("playback_speed_label")
        self.popover = self.builder.get_object("speed_popover")

        self.speed_scale.add_mark(1.0, Gtk.PositionType.RIGHT, None)
        self.speed_scale.set_increments(0.02, 0.05)
        self.speed_scale.connect("value-changed", self.__set_playback_speed)

        player.add_player_listener(self.__player_changed)

    def get_popover(self):
        return self.popover

    def get_speed(self):
        return self.speed

    def set_speed(self, speed):
        self.speed_scale.set_value(speed)
        self.__set_playback_speed(None)

    def __set_playback_speed(self, widget):
        """
        Set the playback speed.
        Update playback speed label.
        """
        self.speed = round(self.speed_scale.get_value(), 2)
        self.speed_label.set_text('{speed:3.1f} x'.format(speed=self.speed))
        
        player.set_playback_speed(self.speed)

        self.emit_event("playback-speed-changed", self.speed)

    def __player_changed(self, event, message):
        """
        Listen to and handle all gst player messages that are important for the ui.
        """
        if event == "track-changed":
            track = message
            speed = db.Book.select().where(db.Book.id == track.book.id).get().playback_speed
            self.speed_scale.set_value(speed)
            self.__set_playback_speed(None)