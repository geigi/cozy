import os
from threading import Thread
import time

import cozy.tools as tools
import cozy.control.player as player
import cozy.ui

import gi

# from cozy.magic.magic import platform as osplatform

gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gst, Gdk, GLib

import logging
log = logging.getLogger("sleep_timer")

class SleepTimer:
    """
    This class contains all timer logic.
    """
    ui = None
    sleep_timer = None
    current_timer_time = 0
    fadeout_thread = None

    def __init__(self):
        self.ui = cozy.ui.main_view.CozyUI()

        self.builder = Gtk.Builder.new_from_resource( "/de/geigi/cozy/timer_popover_power.ui")
        # self.builder = Gtk.Builder.new_from_resource( "/de/geigi/cozy/timer_popover.ui")

        self.timer_popover = self.builder.get_object("timer_popover")
        self.timer_scale = self.builder.get_object("timer_scale")
        self.timer_label = self.builder.get_object("timer_label")
        self.timer_grid = self.builder.get_object("timer_grid")
        self.chapter_switch = self.builder.get_object("chapter_switch")
        self.chapter_switch.connect("state-set", self.__chapter_switch_changed)
        self.timer_image = self.ui.get_object("timer_image")
        self.min_label = self.builder.get_object("min_label")

        # enable system power control
        self.power_control_switch = self.builder.get_object("power_control_switch")
        self.power_control_switch.connect("state-set", self.__power_options_switch_changed)
        self.power_control_options = self.builder.get_object("power_control_options")

        # radio buttons for sleep and shutdown
        self.system_shutdown_radiob = self.builder.get_object("system_shutdown_radiob")
        self.system_suspend_radiob = self.builder.get_object("system_suspend_radiob")
        # self.radiob_system_shutdown.connect("toggled", self.on_button_toggled, "1")


        # text formatting
        self.timer_scale.connect("value-changed", self.__on_timer_changed)

        # add marks to timer scale
        for i in range(0, 121, 30):
            self.timer_scale.add_mark(i, Gtk.PositionType.RIGHT, None)

        # initialize timer ui
        self.__on_timer_changed(None)

        player.add_player_listener(self.__player_changed)

    def get_builder(self):
        return self.builder

    def get_popover(self):
        return self.timer_popover

    def start(self, force=False):
        """
        Start the sleep timer but only when it is enabled by the user.
        """
        if self.chapter_switch.get_state() and not force:
            return
        
        adjustment = self.timer_scale.get_adjustment()
        countdown = int(adjustment.get_value())
        if countdown > 0:
            self.set_time(countdown)
            self.sleep_timer = tools.IntervalTimer(1, self.__sleep_timer_fired)
            self.sleep_timer.start()

    def stop(self):
        """
        Stop the sleep timer.
        """
        if self.sleep_timer:
            self.sleep_timer.stop()
        
        self.sleep_timer = None

    def set_time(self, value):
        """
        Sets the timer to the new given value respecting the fadeout setting.
        :param value: Time in minutes.
        """
        fadeout = 0
        if tools.get_glib_settings().get_boolean("sleep-timer-fadeout"):
            fadeout = tools.get_glib_settings().get_int("sleep-timer-fadeout-duration")
        self.current_timer_time = value * 60 - fadeout

    def is_running(self):
        """
        Is the sleep timer currently running?
        :return: Boolean
        """

    def set_icon(self, running):
        """
        Set the running/stopped timer icon.
        :param running: Boolean
        """
        if running:
            icon = "timer-on-symbolic"
        else:
            icon = "timer-off-symbolic"

        self.timer_image.set_from_icon_name(icon, Gtk.IconSize.BUTTON)

    def __on_timer_changed(self, spinner):
        """
        Start/Stop the timer depending on the current adjustment value.
        """
        adjustment = self.timer_scale.get_adjustment()
        value = adjustment.get_value()

        if value > 0:
            if not self.sleep_timer or not self.sleep_timer.isAlive():
                self.set_icon(True)
                if player.get_gst_player_state() == Gst.State.PLAYING:
                    self.start(force=True)

                self.timer_label.set_visible(True)
                self.min_label.set_text(_("min"))
            else:
                self.set_time(value)
        else:
            self.set_icon(False)
            if self.sleep_timer:
                self.sleep_timer.stop()
            
            self.min_label.set_text(_("Off"))
            self.timer_label.set_visible(False)
            return

        if self.sleep_timer and not self.sleep_timer.isAlive:
            tools.get_glib_settings().set_int("timer", int(value))

        text = str(int(value))
        self.timer_label.set_text(text)

    def __sleep_timer_fired(self):
        """
        The sleep timer gets called every second. Here we do the countdown stuff
        aswell as stop the playback / suspend the machine.
        """
        self.current_timer_time = self.current_timer_time - 1
        adjustment = self.timer_scale.get_adjustment()
        adjustment.set_value(int(self.current_timer_time / 60) + 1)
        if self.current_timer_time < 1:
            self.fadeout_thread = Thread(target=self.__stop_playback, name="SleepTimerFadeoutThread")
            self.fadeout_thread.start()
            self.sleep_timer.stop()
            self.__handle_system_power_event()





    def __handle_system_power_event(self):
        platform = tools.system_platform()

        if self.power_control_switch.get_state():
            if self.system_shutdown_radiob.get_active():
                log.info("system will attempt to shutdown now!")
                if platform is tools.Platform.Linux:
                    os.system("systemctl poweroff")
                else:
                    os.system("shutdown -h now")
            elif self.system_suspend_radiob.get_active():
                log.info("system will attempt to suspend now!")
                if platform is tools.Platform.Linux:
                    os.system("systemctl suspend")
                else:
                    pass

    def __power_options_switch_changed(self, widget, state):
        self.power_control_options.set_sensitive(state)

    def __chapter_switch_changed(self, widget, state):
        """
        Enable/disable stop after chapter mode.
        """
        self.timer_grid.set_sensitive(not state)
        if state:
            if self.sleep_timer and self.sleep_timer.isAlive():
                self.sleep_timer.stop()
            
            self.set_icon(True)
            player.set_play_next(False)
        else:
            self.__on_timer_changed(None)

    def __stop_playback(self):
        """
        Stops playback after gradually fading out (if enabled).
        """
        if tools.get_glib_settings().get_boolean("sleep-timer-fadeout"):
            duration = tools.get_glib_settings().get_int("sleep-timer-fadeout-duration") * 20
            current_vol = player.get_volume()
            for i in range(0, duration):
                player.set_volume(current_vol - (i / duration))
                time.sleep(0.05)

            player.set_volume(current_vol)

        if player.get_gst_player_state() == Gst.State.PLAYING:
            player.play_pause(None)

        self.__handle_system_power_event()

        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, self.timer_scale.get_adjustment().set_value, 0.0)


    def __player_changed(self, event, message):
        """
        Listen to and handle all gst player messages that are important for the ui.
        """
        if event == "track-changed":
            if self.chapter_switch.get_active():
                self.chapter_switch.set_active(False)