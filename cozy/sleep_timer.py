from threading import Thread
import time

import cozy.tools as tools
from cozy.tools import IntervalTimer
import cozy.player as player

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gst

class SleepTimer:
    """
    This class contains all timer logic.
    """
    ui = None
    sleep_timer = None
    current_timer_time = 0
    fadeout_thread = None

    def __init__(self, ui):
        self.ui = ui

        self.builder = Gtk.Builder.new_from_resource(
            "/de/geigi/cozy/timer_popover.ui")

        self.timer_popover = self.builder.get_object("timer_popover")
        self.timer_switch = self.builder.get_object("timer_switch")
        self.timer_scale = self.builder.get_object("timer_scale")
        self.timer_spinner = self.builder.get_object("timer_spinner")
        self.timer_buffer = self.builder.get_object("timer_buffer")
        self.timer_image = self.ui.get_object("timer_image")

        # signals
        self.timer_switch.connect("notify::active", self.__timer_switch_changed)
        # text formatting
        self.timer_spinner.connect("value-changed", self.__on_timer_changed)
        self.timer_spinner.connect("focus-out-event", self.__on_timer_focus_out)

        # add marks to timer scale
        for i in range(0, 181, 15):
            self.timer_scale.add_mark(i, Gtk.PositionType.RIGHT, None)

        # this is required otherwise the timer will not show "min" on start
        self.__init_timer_buffer()

    def __init_timer_buffer(self):
        """
        Add "min" to the timer text field on startup.
        """
        value = tools.get_glib_settings().get_int("timer")
        adjustment = self.timer_spinner.get_adjustment()
        adjustment.set_value(value)

        text = str(int(value)) + " " + _("min")
        self.timer_buffer.set_text(text, len(text))

        return True

    def get_builder(self):
        return self.builder

    def get_popover(self):
        return self.timer_popover

    def start(self):
        """
        Start the sleep timer but only when it is enabled by the user.
        """
        if self.timer_switch.get_active():
            # Enable Timer
            adjustment = self.timer_spinner.get_adjustment()
            countdown = int(adjustment.get_value())

            fadeout = 0
            if tools.get_glib_settings().get_boolean("sleep-timer-fadeout"):
                fadeout = tools.get_glib_settings().get_int("sleep-timer-fadeout-duration")
            self.current_timer_time = countdown * 60 - fadeout

            self.sleep_timer = tools.IntervalTimer(1, self.__sleep_timer_fired)
            self.sleep_timer.start()

    def stop(self):
        """
        Stop the sleep timer.
        """
        if self.sleep_timer is not None:
            self.sleep_timer.stop()

    def is_running(self):
        """
        Is the sleep timer currently running?
        :return: Boolean
        """

    def __on_timer_changed(self, spinner):
        """
        Add "min" to the timer text box on change.
        """
        if not self.timer_switch.get_active():
            self.timer_switch.set_active(True)

        adjustment = self.timer_spinner.get_adjustment()
        value = adjustment.get_value()

        if self.sleep_timer is not None and not self.sleep_timer.isAlive:
            tools.get_glib_settings().set_int("timer", int(value))

        self.current_timer_time = value * 60

        text = str(int(value)) + " " + _("min")
        self.timer_buffer.set_text(text, len(text))

    def __timer_switch_changed(self, sender, widget):
        """
        Start/Stop the sleep timer object.
        """
        if self.timer_switch.get_active():
            self.timer_image.set_from_icon_name(
                "timer-on-symbolic", Gtk.IconSize.BUTTON)
            if player.get_gst_player_state() == Gst.State.PLAYING:
                self.start()
        else:
            self.timer_image.set_from_icon_name(
                "timer-off-symbolic", Gtk.IconSize.BUTTON)
            if self.sleep_timer is not None:
                self.sleep_timer.stop()

    def __on_timer_focus_out(self, event, widget):
        """
        Do not propagate event further.
        This fixes the disappearing ' min' after the spin button looses focus.
        """
        return True

    def __sleep_timer_fired(self):
        """
        The sleep timer gets called every second. Here we do the countdown stuff
        aswell as stop the playback / suspend the machine.
        """
        self.current_timer_time = self.current_timer_time - 1
        adjustment = self.timer_spinner.get_adjustment()
        adjustment.set_value(int(self.current_timer_time / 60) + 1)
        if self.current_timer_time < 1:
            self.fadeout_thread = Thread(target=self.__stop_playback, name="SleepTimerFadeoutThread")
            self.fadeout_thread.start()
            self.sleep_timer.stop()

    def __stop_playback(self):
        if tools.get_glib_settings().get_boolean("sleep-timer-fadeout"):
            duration = tools.get_glib_settings().get_int("sleep-timer-fadeout-duration") * 20
            current_vol = player.get_volume()
            for i in range(0, duration):
                player.set_volume(current_vol - (i / duration))
                time.sleep(0.05)

            player.set_volume(current_vol)

        if player.get_gst_player_state() == Gst.State.PLAYING:
            player.play_pause(None)
        
        self.timer_switch.set_active(False)