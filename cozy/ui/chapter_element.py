from gi.repository import Adw, GObject, Gtk

from cozy.control.string_representation import seconds_to_str
from cozy.model.chapter import Chapter


@Gtk.Template.from_resource("/com/github/geigi/cozy/ui/chapter_element.ui")
class ChapterElement(Adw.ActionRow):
    __gtype_name__ = "ChapterElement"

    icon_stack: Gtk.Stack = Gtk.Template.Child()
    play_icon: Gtk.Image = Gtk.Template.Child()
    number_label: Gtk.Label = Gtk.Template.Child()
    duration_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, chapter: Chapter):
        super().__init__()

        self.chapter = chapter

        self.connect("activated", self._on_button_press)

        self.set_title(self.chapter.name)
        self.duration_label.set_label(seconds_to_str(self.chapter.length))
        self.number_label.set_text(str(self.chapter.number))

    @GObject.Signal(arg_types=(object,))
    def play_pause_clicked(self, *_): ...

    def _on_button_press(self, *_):
        self.emit("play-pause-clicked", self.chapter)

    def select(self):
        self.icon_stack.set_visible_child_name("icon")

    def deselect(self):
        self.icon_stack.set_visible_child_name("number")

    def set_playing(self, playing):
        if playing:
            self.play_icon.set_from_icon_name("media-playback-pause-symbolic")
        else:
            self.play_icon.set_from_icon_name("media-playback-start-symbolic")

