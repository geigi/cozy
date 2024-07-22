import inject
from gi.repository import Gtk

from cozy.view_model.playback_speed_view_model import PlaybackSpeedViewModel


@Gtk.Template.from_resource('/com/github/geigi/cozy/ui/playback_speed_popover.ui')
class PlaybackSpeedPopover(Gtk.Popover):
    __gtype_name__ = "PlaybackSpeedPopover"

    _view_model: PlaybackSpeedViewModel = inject.attr(PlaybackSpeedViewModel)

    playback_speed_scale: Gtk.Scale = Gtk.Template.Child()
    playback_speed_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.playback_speed_scale.add_mark(1.0, Gtk.PositionType.RIGHT, None)
        self.playback_speed_scale.set_increments(0.02, 0.05)
        self.playback_speed_scale.connect("value-changed", self._on_playback_speed_scale_changed)

        self._view_model.bind_to("playback_speed", self._on_playback_speed_changed)

        self._on_playback_speed_changed()

    def _on_playback_speed_scale_changed(self, _):
        speed = round(self.playback_speed_scale.get_value(), 2)
        self._view_model.playback_speed = speed

        self.playback_speed_label.set_markup(f"<span font_features='tnum'>{speed:3.1f} x</span>")

    def _on_playback_speed_changed(self):
        self.playback_speed_scale.set_value(self._view_model.playback_speed)
