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
        self.chapter: Chapter = chapter

        super().__init__()

        self.gesture = Gtk.GestureClick()
        self.gesture.set_button(Gdk.BUTTON_PRIMARY)
        self.gesture.connect("released", self._on_button_press)
        self.add_controller(self.gesture)

        self.motion = Gtk.EventControllerMotion()
        self.motion.connect("enter", self._on_enter_notify)
        self.motion.connect("leave", self._on_leave_notify)
        self.add_controller(self.motion)

        self.set_tooltip_text(_("Play this part"))

        # This box contains all content
        self.box = Gtk.Box()
        self.box.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.box.set_spacing(3)
        self.box.set_halign(Gtk.Align.FILL)
        self.box.set_valign(Gtk.Align.CENTER)

        # These are the widgets that contain data
        self.play_img = Gtk.Image()
        no_label = Gtk.Label()
        title_label = Gtk.Label()
        dur_label = Gtk.Label()

        self.play_img.set_margin_end(5)
        self.play_img.props.width_request = 16

        if self.chapter.number > 0:
            no_label.set_text(str(self.chapter.number))
        no_label.set_margin_top(4)
        no_label.set_margin_bottom(4)
        no_label.set_margin_end(7)
        no_label.set_margin_start(0)
        no_label.set_size_request(30, -1)
        no_label.set_xalign(1)

        self.number_label.set_text(str(self.chapter.number))
        self.title_label.set_text(self.chapter.name)
        self.duration_label.set_text(seconds_to_str(self.chapter.length))

        self._icon_stack_motion = Gtk.EventControllerMotion()
        self._icon_stack_motion.connect("enter", self._on_enter_notify)
        self._icon_stack_motion.connect("leave", self._on_leave_notify)
        self.icon_stack.add_controller(self._icon_stack_motion)

    def _on_button_press(self, *_):
        self.emit("play-pause-clicked", self.chapter)

    def _on_enter_notify(self, *_):
        if not self.selected:
            self.icon_stack.set_visible_child_name("play_icon")
        self.get_style_context().add_class("box_hover")
        self.play_icon.get_style_context().add_class("box_hover")

    def _on_leave_notify(self, *_):
        self.get_style_context().remove_class("box_hover")
        self.play_icon.get_style_context().remove_class("box_hover")

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
