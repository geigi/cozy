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
import logging
from gi.repository import Gio, GLib, Gtk

from random import randint

import cozy.ui
from cozy.application_settings import ApplicationSettings
from cozy.control.artwork_cache import ArtworkCache
from cozy.ext import inject
from cozy.media.player import Player
from cozy.model.book import Book
from cozy.report import reporter

log = logging.getLogger("offline_cache")


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

            try:
                con.register_object(object_path=path,
                                    interface_info=interface,
                                    method_call_closure=self.on_method_call)
            except:
                log.error("MPRIS is already connected from another cozy process.")

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
            if sig == "h":
                msg = invocation.get_message()
                fd_list = msg.get_unix_fd_list()
                args[i] = fd_list.get(args[i])

        out_args = None
        try:
            result = getattr(self, method_name)(*args)

            # out_args is atleast (signature1).
            # We therefore always wrap the result as a tuple.
            # Refer to https://bugzilla.gnome.org/show_bug.cgi?id=765603
            result = (result,)

            out_args = self.method_outargs[method_name]
            if out_args and out_args != "()" and result[0]:
                variant = GLib.Variant(out_args, result)
                invocation.return_value(variant)
            else:
                invocation.return_value(None)
        except Exception as e:
            log.error(e)
            reporter.exception("mpris", e)
            reporter.error("mpris", "MPRIS method call failed with method name: {}".format(method_name))
            if out_args:
                reporter.error("mpris", "MPRIS method call failed with out_args: {}".format(out_args))
            invocation.return_value(None)


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
            <property name="Volume" type="d" access="readwrite"/>
        </interface>
    </node>
    """
    __MPRIS_IFACE = "org.mpris.MediaPlayer2"
    __MPRIS_PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"
    __MPRIS_RATINGS_IFACE = "org.mpris.MediaPlayer2.ExtensionSetRatings"
    __MPRIS_COZY = "org.mpris.MediaPlayer2.Cozy"
    __MPRIS_PATH = "/org/mpris/MediaPlayer2"
    _player: Player = inject.attr(Player)
    _artwork_cache: ArtworkCache = inject.attr(ArtworkCache)
    _app_settings: ApplicationSettings = inject.attr(ApplicationSettings)

    def __init__(self, app):
        self.__app = app
        self.__ui = cozy.ui.main_view.CozyUI()
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

        self._player.add_listener(self._on_player_changed)
        self._app_settings.add_listener(self._on_app_setting_changed)

    def Raise(self):
        try:
            self.__app.ui.window.present_with_time(Gtk.get_current_event_time())
        except Exception as e:
            reporter.exception("mpris", e)

    def Quit(self):
        self.__app.quit()

    def Next(self):
        self._player.forward()

    def Previous(self):
        self._player.rewind()

    def Pause(self):
        self._player.pause()

    def PlayPause(self):
        self._player.play_pause()

    def Stop(self):
        self._player.destroy()

    def Play(self):
        self._player.play_pause()

    def SetPosition(self, track_id, position):
        self._player.position = position * 10**3

    def Seek(self, offset):
        # convert milliseconds to seconds
        offset_sec=offset / 10**6
        if offset_sec > 0:
            self._player.forward(offset_sec)
        elif offset_sec < 0:
            self._player.rewind(-offset_sec)

    def Seeked(self, position):
        self.__bus.emit_signal(
            None,
            self.__MPRIS_PATH,
            "org.freedesktop.DBus.Properties",
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
                round(self._player.position * 10**-3))
        elif property_name in ["CanGoNext", "CanGoPrevious",
                               "CanPlay", "CanPause"]:
            return GLib.Variant("b", self._player.loaded_book is not None)
        elif property_name == "Volume":
             return GLib.Variant("d", self._player.volume)
        else:
            reporter.warning("mpris", "MPRIS required an unknown information: {}".format(property_name))
            return None

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
        if property_name == "Volume":
            self._player.volume = new_value

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
        return GLib.Variant("o", "/com/github/geigi/cozy/TrackId/%s" % track_id)

    def __get_status(self):
        if self._player.playing:
            return "Playing"
        elif not self._player.loaded_book:
            return "Stopped"
        else:
            return "Paused"

    def _on_player_changed(self, event, message):
        if event == "chapter-changed":
            self._on_current_changed()
        elif event == "play":
            self.__on_status_changed("Playing")
        elif event == "pause":
            self.__on_status_changed("Paused")
        elif event == "stop":
            self.__on_status_changed("Stopped")

    def _on_app_setting_changed(self, event, _):
        if event == "swap-author-reader":
            self._on_current_changed()

    def __update_metadata(self, book: Book):
        # if track is None:
        #     track = get_current_track()
        if book is None:
            self.__metadata = {"mpris:trackid": GLib.Variant(
                "o",
                "/org/mpris/MediaPlayer2/TrackList/NoTrack")}
        else:
            self.__metadata["mpris:trackid"] = self.__track_id
            track_number = book.current_chapter.number

            self.__metadata["xesam:trackNumber"] = GLib.Variant("i",
                                                                track_number)
            self.__metadata["xesam:title"] = GLib.Variant(
                "s",
                book.current_chapter.name)
            self.__metadata["xesam:album"] = GLib.Variant(
                "s",
                book.name)
            self.__metadata["xesam:artist"] = GLib.Variant(
                "as",
                [book.author])
            self.__metadata["mpris:length"] = GLib.Variant(
                "x",
                book.current_chapter.length * 1000 * 1000)
            self.__metadata["xesam:url"] = GLib.Variant(
                "s",
                "file:///" + book.current_chapter.file)

            path = self._artwork_cache.get_album_art_path(book, 180)
            if path:
                self.__metadata["mpris:artUrl"] = GLib.Variant(
                    "s",
                    "file://" + path)

    def __on_seeked(self, player, position):
        self.Seeked(position * (1000 * 1000))

    def _on_current_changed(self):
        if not self._player.loaded_book:
            return

        current_track_id = self._player.loaded_chapter.id
        if current_track_id and current_track_id >= 0:
            self.__cozy_id = current_track_id
        else:
            self.__cozy_id = 0
        self.__track_id = self.__get_media_id(self.__cozy_id)
        self.__rating = None
        self.__update_metadata(self._player.loaded_book)
        properties = {"Metadata": GLib.Variant("a{sv}", self.__metadata),
                      "CanPlay": GLib.Variant("b", True),
                      "CanPause": GLib.Variant("b", True),
                      "CanGoNext": GLib.Variant("b", True),
                      "CanGoPrevious": GLib.Variant("b", True)}
        try:
            self.PropertiesChanged(self.__MPRIS_PLAYER_IFACE, properties, [])
        except Exception as e:
            print("MPRIS::__on_current_changed(): %s" % e)

    def __on_status_changed(self, status, data=None):
        properties = {"PlaybackStatus": GLib.Variant("s", status)}
        self.PropertiesChanged(self.__MPRIS_PLAYER_IFACE, properties, [])
