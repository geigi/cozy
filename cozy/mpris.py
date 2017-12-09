# Forked from https://github.com/gnumdk/lollypop/blob/master/lollypop/mpris.py
# copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# copyright (c) 2016 Gaurav Narula
# copyright (c) 2016 Felipe Borges <felipeborges@gnome.org>
# copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# copyright (c) 2017 Julian Geywitz <cozy@geigi.de>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gio, Gst, GLib, Gtk

from random import randint

from cozy.player import *
from cozy.db import *


class Server:
    def __init__(self, con, path):
        method_outargs = {}
        method_inargs = {}
        for interface in Gio.DBusNodeInfo.new_for_xml(self.__doc__).interfaces:

            for method in interface.methods:
                method_outargs[method.name] = "(" + "".join(
                              [arg.signature for arg in method.out_args]) + ")"
                method_inargs[method.name] = tuple(
                    arg.signature for arg in method.in_args)

            con.register_object(object_path=path,
                                interface_info=interface,
                                method_call_closure=self.on_method_call)

        self.method_inargs = method_inargs
        self.method_outargs = method_outargs

    def on_method_call(self,
                       connection,
                       sender,
                       object_path,
                       interface_name,
                       method_name,
                       parameters,
                       invocation):

        args = list(parameters.unpack())
        for i, sig in enumerate(self.method_inargs[method_name]):
            if sig is "h":
                msg = invocation.get_message()
                fd_list = msg.get_unix_fd_list()
                args[i] = fd_list.get(args[i])

        try:
            result = getattr(self, method_name)(*args)

            # out_args is atleast (signature1).
            # We therefore always wrap the result as a tuple.
            # Refer to https://bugzilla.gnome.org/show_bug.cgi?id=765603
            result = (result,)

            out_args = self.method_outargs[method_name]
            if out_args != "()":
                variant = GLib.Variant(out_args, result)
                invocation.return_value(variant)
            else:
                invocation.return_value(None)
        except:
            pass


class MPRIS(Server):
    """
    <!DOCTYPE node PUBLIC
    "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
    "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
    <node>
        <interface name="org.freedesktop.DBus.Introspectable">
            <method name="Introspect">
                <arg name="data" direction="out" type="s"/>
            </method>
        </interface>
        <interface name="org.freedesktop.DBus.Properties">
            <method name="Get">
                <arg name="interface" direction="in" type="s"/>
                <arg name="property" direction="in" type="s"/>
                <arg name="value" direction="out" type="v"/>
            </method>
            <method name="Set">
                <arg name="interface_name" direction="in" type="s"/>
                <arg name="property_name" direction="in" type="s"/>
                <arg name="value" direction="in" type="v"/>
            </method>
            <method name="GetAll">
                <arg name="interface" direction="in" type="s"/>
                <arg name="properties" direction="out" type="a{sv}"/>
            </method>
        </interface>
        <interface name="org.mpris.MediaPlayer2">
            <method name="Raise">
            </method>
            <method name="Quit">
            </method>
            <property name="CanQuit" type="b" access="read" />
            <property name="Fullscreen" type="b" access="readwrite" />
            <property name="CanRaise" type="b" access="read" />
            <property name="HasTrackList" type="b" access="read"/>
            <property name="Identity" type="s" access="read"/>
            <property name="DesktopEntry" type="s" access="read"/>
            <property name="SupportedUriSchemes" type="as" access="read"/>
            <property name="SupportedMimeTypes" type="as" access="read"/>
        </interface>
        <interface name="org.mpris.MediaPlayer2.Player">
            <method name="Next"/>
            <method name="Previous"/>
            <method name="Pause"/>
            <method name="PlayPause"/>
            <method name="Stop"/>
            <method name="Play"/>
            <method name="Seek">
                <arg direction="in" name="Offset" type="x"/>
            </method>
            <method name="SetPosition">
                <arg direction="in" name="TrackId" type="o"/>
                <arg direction="in" name="Position" type="x"/>
            </method>
            <method name="OpenUri">
                <arg direction="in" name="Uri" type="s"/>
            </method>
            <signal name="Seeked">
                <arg name="Position" type="x"/>
            </signal>
            <property name="PlaybackStatus" type="s" access="read"/>
            <property name="Metadata" type="a{sv}" access="read">
            </property>
            <property name="Position" type="x" access="read"/>
            <property name="CanGoNext" type="b" access="read"/>
            <property name="CanGoPrevious" type="b" access="read"/>
            <property name="CanPlay" type="b" access="read"/>
            <property name="CanPause" type="b" access="read"/>
            <property name="CanSeek" type="b" access="read"/>
            <property name="CanControl" type="b" access="read"/>
        </interface>
    </node>
    """
    __MPRIS_IFACE = "org.mpris.MediaPlayer2"
    __MPRIS_PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"
    __MPRIS_RATINGS_IFACE = "org.mpris.MediaPlayer2.ExtensionSetRatings"
    __MPRIS_COZY = "org.mpris.MediaPlayer2.Cozy"
    __MPRIS_PATH = "/org/mpris/MediaPlayer2"

    def __init__(self, app, ui):
        self.__app = app
        self.__ui = ui
        self.__rating = None
        self.__cozy_id = 0
        self.__metadata = {"mpris:trackid": GLib.Variant(
            "o",
            "/org/mpris/MediaPlayer2/TrackList/NoTrack")}
        self.__track_id = self.__get_media_id(0)
        self.__bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        Gio.bus_own_name_on_connection(self.__bus,
                                       self.__MPRIS_COZY,
                                       Gio.BusNameOwnerFlags.NONE,
                                       None,
                                       None)
        Server.__init__(self, self.__bus, self.__MPRIS_PATH)

        bus = get_gst_bus()
        bus.connect("message", self.__on_gst_message)

        #Lp().player.connect("current-changed", self.__on_current_changed)
        #Lp().player.connect("seeked", self.__on_seeked)
        #Lp().player.connect("status-changed", self.__on_status_changed)
        #Lp().player.connect("volume-changed", self.__on_volume_changed)

    def Raise(self):
        self.__app.window.setup_window()
        self.__app.window.present_with_time(Gtk.get_current_event_time())

    def Quit(self):
        self.__app.quit()

    def Next(self):
        next_track()

    def Previous(self):
        prev_track()

    def Pause(self):
        play_pause(None)

    def PlayPause(self):
        play_pause(None)

    def Stop(self):
        stop(None)

    def Play(self):
        play_pause(None)

    def SetPosition(self, track_id, position):
        jump_to_ns(position)

    def Seek(self, offset):
        pass

    def Seeked(self, position):
        self.__bus.emit_signal(
            None,
            self.__MPRIS_PATH,
            self.__MPRIS_PLAYER_IFACE,
            "Seeked",
            GLib.Variant.new_tuple(GLib.Variant("x", position)))

    def Get(self, interface, property_name):
        if property_name in ["CanQuit", "CanRaise", "CanSeek",
                             "CanControl", "HasRatingsExtension"]:
            return GLib.Variant("b", True)
        elif property_name == "HasTrackList":
            return GLib.Variant("b", False)
        elif property_name == "Identity":
            return GLib.Variant("s", "Cozy")
        elif property_name == "DesktopEntry":
            return GLib.Variant("s", "com.github.geigi.cozy")
        elif property_name == "SupportedUriSchemes":
            return GLib.Variant("as", ["file"])
        elif property_name == "SupportedMimeTypes":
            return GLib.Variant("as", ["application/ogg",
                                       "audio/x-vorbis+ogg",
                                       "audio/x-flac",
                                       "audio/mpeg"])
        elif property_name == "PlaybackStatus":
            return GLib.Variant("s", self.__get_status())
        elif property_name == "Metadata":
            return GLib.Variant("a{sv}", self.__metadata)
        elif property_name == "Position":
            return GLib.Variant(
                "x",
                get_current_duration())
        elif property_name in ["CanGoNext", "CanGoPrevious",
                               "CanPlay", "CanPause"]:
            return GLib.Variant("b", get_current_track() is not None)

    def GetAll(self, interface):
        ret = {}
        if interface == self.__MPRIS_IFACE:
            for property_name in ["CanQuit",
                                  "CanRaise",
                                  "HasTrackList",
                                  "Identity",
                                  "DesktopEntry",
                                  "SupportedUriSchemes",
                                  "SupportedMimeTypes"]:
                ret[property_name] = self.Get(interface, property_name)
        elif interface == self.__MPRIS_PLAYER_IFACE:
            for property_name in ["PlaybackStatus",
                                  "Metadata",
                                  "Position",
                                  "CanGoNext",
                                  "CanGoPrevious",
                                  "CanPlay",
                                  "CanPause",
                                  "CanSeek",
                                  "CanControl"]:
                ret[property_name] = self.Get(interface, property_name)
        elif interface == self.__MPRIS_RATINGS_IFACE:
            ret["HasRatingsExtension"] = GLib.Variant("b", False)
        return ret

    def Set(self, interface, property_name, new_value):
        # if property_name == "Volume":
        #    Lp().player.set_volume(new_value)
        pass

    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        self.__bus.emit_signal(None,
                               self.__MPRIS_PATH,
                               "org.freedesktop.DBus.Properties",
                               "PropertiesChanged",
                               GLib.Variant.new_tuple(
                                   GLib.Variant("s", interface_name),
                                   GLib.Variant("a{sv}", changed_properties),
                                   GLib.Variant("as", invalidated_properties)))

    def Introspect(self):
        return self.__doc__

#######################
# PRIVATE             #
#######################

    def __get_media_id(self, track_id):
        """
            TrackId's must be unique even up to
            the point that if you repeat a song
            it must have a different TrackId.
        """
        track_id = track_id + randint(10000000, 90000000)
        return GLib.Variant("o", "/de/geigi/Cozy/TrackId/%s" % track_id)

    def __get_status(self):
        state = get_gst_player_state()
        if state == Gst.State.PLAYING:
            return "Playing"
        elif state == Gst.State.PAUSED:
            return "Paused"
        else:
            return "Stopped"

    def __on_gst_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.STREAM_START:
            # new track is playing
            self.__on_current_changed()
            pass
        elif t == Gst.MessageType.STATE_CHANGED:
            # handle play / pause / skip
            self.__on_status_changed()
            pass

    def __update_metadata(self):
        track = get_current_track()
        if self.__get_status() == "Stopped":
            self.__metadata = {"mpris:trackid": GLib.Variant(
                "o",
                "/org/mpris/MediaPlayer2/TrackList/NoTrack")}
        else:
            self.__metadata["mpris:trackid"] = self.__track_id
            track_number = track.number
            if track_number is None:
                track_number = 1
            self.__metadata["xesam:trackNumber"] = GLib.Variant("i",
                                                                track_number)
            self.__metadata["xesam:title"] = GLib.Variant(
                "s",
                track.name)
            self.__metadata["xesam:album"] = GLib.Variant(
                "s",
                track.book.name)
            self.__metadata["xesam:artist"] = GLib.Variant(
                "s",
                track.book.author)
            self.__metadata["mpris:length"] = GLib.Variant(
                "x",
                track.length * 1000 * 1000)
            self.__metadata["xesam:url"] = GLib.Variant(
                "s",
                "file:///" + track.file)

            cover_path = "/tmp/cozy_mpris.jpg"
            pixbuf = get_cover_pixbuf(track.book)
            if pixbuf is not None:
                pixbuf.savev(cover_path, "jpeg",
                             ["quality"], ["90"])
            if cover_path is not None:
                self.__metadata["mpris:artUrl"] = GLib.Variant(
                    "s",
                    "file://" + cover_path)

    def __on_seeked(self, player, position):
        self.Seeked(position * (1000 * 1000))

    def __on_current_changed(self):
        current_track_id = get_current_track().id
        if current_track_id and current_track_id >= 0:
            self.__cozy_id = current_track_id
        else:
            self.__cozy_id = 0
        # We only need to recalculate a new trackId at song changes.
        self.__track_id = self.__get_media_id(self.__cozy_id)
        self.__rating = None
        self.__update_metadata()
        properties = {"Metadata": GLib.Variant("a{sv}", self.__metadata),
                      "CanPlay": GLib.Variant("b", True),
                      "CanPause": GLib.Variant("b", True),
                      "CanGoNext": GLib.Variant("b", True),
                      "CanGoPrevious": GLib.Variant("b", True)}
        try:
            self.PropertiesChanged(self.__MPRIS_PLAYER_IFACE, properties, [])
        except Exception as e:
            print("MPRIS::__on_current_changed(): %s" % e)

    def __on_status_changed(self, data=None):
        properties = {"PlaybackStatus": GLib.Variant("s", self.__get_status())}
        self.PropertiesChanged(self.__MPRIS_PLAYER_IFACE, properties, [])
