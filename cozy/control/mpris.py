# Forked from https://github.com/gnumdk/lollypop/blob/master/lollypop/mpris.py
# copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# copyright (c) 2016 Gaurav Narula
# copyright (c) 2016 Felipe Borges <felipeborges@gnome.org>
# copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# copyright (c) 2017 Julian Geywitz <cozy@geigi.de>
# copyright (c) 2023 Benedek Dévényi <rdbende@proton.me>

import logging
import re
import time
from dataclasses import dataclass

import inject
from gi.repository import Gio, GLib

from cozy.control.artwork_cache import ArtworkCache
from cozy.media.player import Player
from cozy.model.book import Book
from cozy.report import reporter
from cozy.settings import ApplicationSettings

log = logging.getLogger("mpris")

CamelCasePattern = re.compile(r"(?<!^)(?=[A-Z])")

NS_TO_US = 1e3


def to_snake_case(name: str) -> str:
    return CamelCasePattern.sub("_", name).lower()


@dataclass(kw_only=True, frozen=True, slots=True)
class Metadata:
    track_id: str
    track_number: int
    title: str
    album: str
    artist: list[str]
    length: int
    url: str
    artwork_uri: str

    def to_dict(self) -> dict[str, GLib.Variant]:
        data = {}
        data["mpris:trackid"] = GLib.Variant("o", self.track_id)
        data["xesam:trackNumber"] = GLib.Variant("i", self.track_number)
        data["xesam:title"] = GLib.Variant("s", self.title)
        data["xesam:album"] = GLib.Variant("s", self.album)
        data["xesam:artist"] = GLib.Variant("as", self.artist)
        data["mpris:length"] = GLib.Variant("x", self.length)
        data["xesam:url"] = GLib.Variant("s", self.url)

        if self.artwork_uri:
            data["mpris:artUrl"] = GLib.Variant("s", "file://" + self.artwork_uri)

        return data

    @staticmethod
    def no_track() -> dict[str, GLib.Variant]:
        no_track_path = GLib.Variant("o", "/org/mpris/MediaPlayer2/TrackList/NoTrack")
        return {"mpris:trackid": no_track_path}


class Server:
    def __init__(self, connection: Gio.DBusConnection, path: str) -> None:
        self.method_outargs = {}
        self.method_inargs = {}

        for interface in Gio.DBusNodeInfo.new_for_xml(self.__doc__).interfaces:
            for method in interface.methods:
                self.method_inargs[method.name] = tuple(arg.signature for arg in method.in_args)
                out_sig = [arg.signature for arg in method.out_args]
                self.method_outargs[method.name] = "(" + "".join(out_sig) + ")"

            try:
                connection.register_object(
                    object_path=path,
                    interface_info=interface,
                    method_call_closure=self.on_method_call,
                )
            except Exception:
                log.error("MPRIS is already connected from another Cozy process.")

    def on_method_call(
        self,
        connection: Gio.DBusConnection,
        sender: str,
        object_path: str,
        interface_name: str,
        method_name: str,
        parameters: GLib.Variant,
        invocation: Gio.DBusMethodInvocation,
    ) -> None:
        args = list(parameters.unpack())
        for i, sig in enumerate(self.method_inargs[method_name]):
            if sig == "h":
                msg = invocation.get_message()
                fd_list = msg.get_unix_fd_list()
                args[i] = fd_list.get(args[i])

        snake_method = to_snake_case(method_name)
        try:
            result = getattr(self, snake_method)(*args)
        except AttributeError:
            invocation.return_dbus_error(
                f"{interface_name}.Error.NotSupported", "Unsupported property"
            )
        except Exception as e:
            log.error(e)
            reporter.exception("mpris", e)
            reporter.error("mpris", f"MPRIS method call failed with method name: {method_name}")
            invocation.return_dbus_error(
                f"{interface_name}.Error.Failed", "Internal exception occurred"
            )
        else:
            # out_args is at least (signature1).
            # We therefore always wrap the result as a tuple.
            # Reference:
            # https://bugzilla.gnome.org/show_bug.cgi?id=765603
            result = (result,)

            out_args = self.method_outargs[method_name]
            if out_args != "()" and result[0] is not None:
                variant = GLib.Variant(out_args, result)
                invocation.return_value(variant)
            else:
                invocation.return_value(None)


class MPRIS(Server):
    """
    <node xmlns:doc="http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
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
        <signal name="PropertiesChanged">
          <arg name="interface_name" type="s" />
          <arg name="changed_properties" type="a{sv}" />
          <arg name="invalidated_properties" type="as" />
        </signal>
      </interface>
      <interface name="org.mpris.MediaPlayer2">
        <method name="Raise"/>
        <method name="Quit"/>
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
        <property name="Metadata" type="a{sv}" access="read"/>
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

    MEDIA_PLAYER2_INTERFACE = "org.mpris.MediaPlayer2"
    MEDIA_PLAYER2_PLAYER_INTERFACE = "org.mpris.MediaPlayer2.Player"

    _player: Player = inject.attr(Player)
    _artwork_cache: ArtworkCache = inject.attr(ArtworkCache)
    _app_settings: ApplicationSettings = inject.attr(ApplicationSettings)

    def __init__(self, app) -> None:
        self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        Gio.bus_own_name_on_connection(
            self._bus,
            "org.mpris.MediaPlayer2.com.github.geigi.cozy",
            Gio.BusNameOwnerFlags.NONE,
            None,
            None,
        )
        super().__init__(self._bus, "/org/mpris/MediaPlayer2")

        self._application = app
        self._metadata = self._get_new_metadata()

        self._player.add_listener(self._on_player_changed)
        self._app_settings.add_listener(self._on_app_setting_changed)

    def introspect(self):
        return self.__doc__

    def quit(self):
        self._application.quit()

    def next(self):
        self._player.forward()

    def previous(self):
        self._player.rewind()

    def play(self):
        self._player.play_pause()

    def pause(self):
        self._player.pause()

    def play_pause(self):
        self._player.play_pause()

    def stop(self):
        self._player.destroy()

    def set_position(self, track_id: str, position: int):
        self._player.position = position * NS_TO_US

    def seek(self, offset: int):
        self._player.position = self._player.position + offset * NS_TO_US

    def get(self, interface: str, property_name: str) -> GLib.Variant:
        if property_name in {"CanQuit", "CanControl"}:
            return GLib.Variant("b", True)
        elif property_name in {"CanRaise", "HasTrackList"}:
            return GLib.Variant("b", False)
        elif property_name in {"CanGoNext", "CanGoPrevious", "CanPlay", "CanPause", "CanSeek"}:
            return GLib.Variant("b", self._player.loaded_book is not None)
        elif property_name in {"SupportedUriSchemes", "SupportedMimeTypes"}:
            return GLib.Variant("as", [])

        # Might raise an AttributeError. We handle that in Server.on_method_call
        return getattr(self, to_snake_case(property_name))

    def get_all(self, interface) -> dict[str, GLib.Variant]:
        if interface == self.MEDIA_PLAYER2_INTERFACE:
            properties = (
                "CanQuit",
                "CanRaise",
                "HasTrackList",
                "Identity",
                "DesktopEntry",
                "SupportedUriSchemes",
                "SupportedMimeTypes",
            )
        elif interface == self.MEDIA_PLAYER2_PLAYER_INTERFACE:
            properties = (
                "PlaybackStatus",
                "Metadata",
                "Position",
                "CanGoNext",
                "CanGoPrevious",
                "CanPlay",
                "CanPause",
                "CanSeek",
                "CanControl",
                "Volume",
            )
        else:
            return {}

        return {property: self.get(interface, property) for property in properties}

    def set(self, interface: str, property_name: str, value) -> None:
        # Might raise an AttributeError. We handle that in Server.on_method_call
        return setattr(self, to_snake_case(property_name), value)

    def properties_changed(self, iface_name, changed_props, invalidated_props):
        self._bus.emit_signal(
            None,
            "/org/mpris/MediaPlayer2",
            "org.freedesktop.DBus.Properties",
            "PropertiesChanged",
            GLib.Variant.new_tuple(
                GLib.Variant("s", iface_name),
                GLib.Variant("a{sv}", changed_props),
                GLib.Variant("as", invalidated_props),
            ),
        )

    @property
    def desktop_entry(self):
        return GLib.Variant("s", "com.github.geigi.cozy")

    @property
    def identity(self):
        return GLib.Variant("s", "Cozy")

    @property
    def playback_status(self):
        if self._player.playing:
            return GLib.Variant("s", "Playing")
        elif not self._player.loaded_book:
            return GLib.Variant("s", "Stopped")
        else:
            return GLib.Variant("s", "Paused")

    @property
    def metadata(self):
        return GLib.Variant("a{sv}", self._metadata)

    @property
    def position(self):
        return GLib.Variant("x", round(self._player.position / 1e3))

    @property
    def volume(self):
        return GLib.Variant("d", self._player.volume)

    @volume.setter
    def volume(self, new_value: float) -> None:
        self._player.volume = new_value

    def _get_track_id(self) -> float:
        """
        Track IDs must be unique even up to the point that if a song
        is repeated in a playlist it must have a different TrackId.
        """
        return time.time() * 1e10 % 1e10

    def _get_new_metadata(self, book: Book | None = None) -> dict[str, GLib.Variant]:
        if book is None:
            return Metadata.no_track()

        track_path_template = "/com/github/geigi/cozy/TrackId/{id:.0f}"
        uri_template = "file://{path}"

        metadata = Metadata(
            track_id=track_path_template.format(id=self._get_track_id()),
            track_number=book.current_chapter.number,
            title=book.current_chapter.name,
            album=book.name,
            artist=[book.author],
            length=book.current_chapter.length / NS_TO_US,
            url=uri_template.format(path=book.current_chapter.file),
            artwork_uri=self._artwork_cache.get_album_art_path(book, 256),
        )
        return metadata.to_dict()

    def _on_player_changed(self, event: str, _) -> None:
        if event == "position":
            self.properties_changed(
                self.MEDIA_PLAYER2_PLAYER_INTERFACE, {"Position": self.position}, []
            )
        elif event == "chapter-changed":
            self._on_current_changed()
        elif event == "play":
            self._on_status_changed("Playing")
        elif event == "pause":
            self._on_status_changed("Paused")
        elif event == "stop":
            self._on_status_changed("Stopped")

    def _on_app_setting_changed(self, event: str, _):
        if event == "swap-author-reader":
            self._on_current_changed()

    def _on_current_changed(self) -> None:
        if not self._player.loaded_book:
            return

        self._metadata = self._get_new_metadata(self._player.loaded_book)

        properties = {
            "Metadata": GLib.Variant("a{sv}", self._metadata),
            "CanPlay": GLib.Variant("b", True),
            "CanPause": GLib.Variant("b", True),
            "CanGoNext": GLib.Variant("b", True),
            "CanGoPrevious": GLib.Variant("b", True),
        }

        self.properties_changed(self.MEDIA_PLAYER2_PLAYER_INTERFACE, properties, [])

    def _on_status_changed(self, status: str) -> None:
        properties = {"PlaybackStatus": GLib.Variant("s", status)}
        self.properties_changed(self.MEDIA_PLAYER2_PLAYER_INTERFACE, properties, [])
