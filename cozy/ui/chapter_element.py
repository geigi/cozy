from gi.repository import Gtk, Pango, GObject, Gdk

from cozy.control.string_representation import seconds_to_str
from cozy.model.chapter import Chapter


@Gtk.Template.from_resource('/com/github/geigi/cozy/chapter_element.ui')
class ChapterElement(Gtk.Box):
    __gtype_name__ = "ChapterElement"

    icon_stack: Gtk.Stack = Gtk.Template.Child()
    number_label: Gtk.Label = Gtk.Template.Child()
    play_icon: Gtk.Image = Gtk.Template.Child()
    title_label: Gtk.Label = Gtk.Template.Child()
    duration_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, chapter: Chapter):
        self.selected = False
        self.chapter = chapter

        super().__init__()

        gesture = Gtk.GestureClick(button=Gdk.BUTTON_PRIMARY)
        gesture.connect("released", self._on_button_press)
        self.add_controller(gesture)

        motion = Gtk.EventControllerMotion()
        motion.connect("enter", self._on_enter_notify)
        motion.connect("leave", self._on_leave_notify)
        self.add_controller(motion)

        self.number_label.set_text(str(self.chapter.number))
        self.title_label.set_text(self.chapter.name)
        self.duration_label.set_text(seconds_to_str(self.chapter.length))

    def _on_button_press(self, *_):
        self.emit("play-pause-clicked", self.chapter)

    def _on_enter_notify(self, *_):
        self.add_css_class("box_hover")
        self.play_icon.add_css_class("box_hover")

        if not self.selected:
            self.icon_stack.set_visible_child_name("play_icon")

    def _on_leave_notify(self, *_):
        self.remove_css_class("box_hover")
        self.play_icon.remove_css_class("box_hover")

        if not self.selected:
            self.icon_stack.set_visible_child_name("number")

    def select(self):
        self.selected = True
        self.icon_stack.set_visible_child_name("play_icon")

    def deselect(self):
        self.selected = False
        self.icon_stack.set_visible_child_name("number")

    def set_playing(self, playing):
        if playing:
            self.play_icon.set_from_icon_name("pause-symbolic")
        else:
            self.play_icon.set_from_icon_name("play-symbolic")


GObject.type_register(ChapterElement)
GObject.signal_new('play-pause-clicked', ChapterElement, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))
