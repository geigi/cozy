import threading
import time
from gi.repository import Gst

import gi
gi.require_version('Gst', '1.0')
import logging
log = logging.getLogger("player")

import cozy.control.db
from cozy.control.offline_cache import OfflineCache
import cozy.control.filesystem_monitor

Gst.init(None)

__speed = 1.0
__set_speed = False
__current_track = None
__listeners = []
__wait_to_seek = False
__player = None
__bus = None
__play_next = True


def __on_gst_message(bus, message):
    """
    Handle messages from gst.
    """
    global __speed
    global __set_speed

    t = message.type
    if t == Gst.MessageType.BUFFERING:
        if (message.percentage < 100):
            __player.set_state(Gst.State.PAUSED)
            log.info("Buffering…")
        else:
            __player.set_state(Gst.State.PLAYING)
            log.info("Buffering finished.")
    elif t == Gst.MessageType.EOS:
        next_track()
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        log.error(err)
        log.debug(debug)
        emit_event("error", err)
    elif t == Gst.MessageType.STATE_CHANGED:
        state = get_gst_player_state()
        if state == Gst.State.PLAYING or state == Gst.State.PAUSED:
            auto_jump()


def init():
    global __player
    global __bus

    if __player:
        dispose()
        __player = None

    __player = Gst.ElementFactory.make("playbin", "player")
    __scaletempo = Gst.ElementFactory.make("scaletempo", "scaletempo")
    __scaletempo.sync_state_with_parent()

    __audiobin = Gst.ElementFactory.make("bin", "audiosink")
    __audiobin.add(__scaletempo)

    __audiosink = Gst.ElementFactory.make("autoaudiosink", "audiosink")
    __audiobin.add(__audiosink)

    __scaletempo.link(__audiosink)
    __pad = __scaletempo.get_static_pad("sink")
    __ghost_pad = Gst.GhostPad.new("sink", __pad)
    __audiobin.add_pad(__ghost_pad)

    __player.set_property("audio-sink", __audiobin)

    __bus = __player.get_bus()
    __bus.add_signal_watch()
    __bus.connect("message", __on_gst_message)

    cozy.control.filesystem_monitor.FilesystemMonitor().add_listener(__on_storage_changed)


def get_gst_bus():
    """
    Get the global gst bus.
    :return: gst bus
    """
    global __bus
    return __bus


def get_playbin():
    """
    Get the global gst playbin.
    :return: playbin
    """
    global __player
    return __player


def get_gst_player_state():
    """
    Get the current state of the gst player.
    :return: gst player state
    """
    global __player
    success, state, pending = __player.get_state(50)
    return state


def get_current_duration(wait=False):
    """
    Current duration of track
    :returns: duration in ns
    """
    global __current_track
    global __player

    res = __player.query_position(Gst.Format.TIME)

    if wait:
        while not res[0] and __current_track:
            time.sleep(0.1)
            res = __player.query_position(Gst.Format.TIME)

    return res[1]


def get_current_duration_ui():
    """
    current duration to display in ui
    :return m: minutes
    :return s: seconds
    """
    global __speed
    s, ns = divmod(get_current_duration() / __speed, 1000000000)
    m, s = divmod(s, 60)
    return m, s


def get_current_track():
    """
    Get the currently loaded track object.
    :return: currently loaded track object
    """
    global __current_track
    if __current_track:
        query = cozy.control.db.Track.select().where(cozy.control.db.Track.id == __current_track.id)
        if query.exists():
            return query.get()
        else:
            __current_track = None
            return None
    else:
        return None


def add_player_listener(function):
    """
    Add a listener to listen to changes from the player.
    """
    global __listeners
    __listeners.append(function)


def get_volume():
    """
    Get the player volume. 
    :returns: 0.0 is 0%, 1.0 is 100%
    """
    global __player
    return __player.get_property("volume")


def set_volume(volume):
    """
    Set the player volume. 
    :param volume: 0.0 is 0%, 1.0 is 100%
    """
    global __player
    __player.set_property("volume", volume)


def set_mute(mute):
    """
    Mute the player.
    :param mute: Boolean
    """
    global __player
    __player.set_property("mute", mute)


def play_pause(track, jump=False):
    """
    Play a new file or pause/play if the file is already loaded.
    :param track: Track object that will be played/paused.
    """
    global __current_track
    global __player
    global __wait_to_seek
    global __set_speed

    __wait_to_seek = jump

    if __current_track == track or track is None:
        # Track is already selected, only play/pause
        if get_gst_player_state() == Gst.State.PLAYING:
            __player.set_state(Gst.State.PAUSED)
            emit_event("pause")
            save_current_track_position()
        else:
            __player.set_state(Gst.State.PLAYING)
            emit_event("play", cozy.control.db.Track.get(cozy.control.db.Track.id == __current_track.id))
    else:
        load_file(track)
        __player.set_state(Gst.State.PLAYING)
        emit_event("play", cozy.control.db.Track.get(cozy.control.db.Track.id == __current_track.id))

    __set_speed = True


def next_track():
    """
    Play the next track of the current book.
    Stops playback if there isn't any.
    """
    global __current_track
    global __play_next

    album_tracks = cozy.control.db.get_tracks(get_current_track().book)
    current = get_current_track()
    index = list(album_tracks).index(current)
    next_track = None
    if index + 1 < len(album_tracks):
        next_track = album_tracks[index + 1]

    play_pause(None)
    save_current_track_position(0)

    if next_track:
        save_current_book_position(next_track)
        save_current_track_position(0, next_track)
        if __play_next:
            play_pause(next_track)
        else:
            load_file(next_track)
            __play_next = True
    else:
        stop()
        save_current_book_position(current, -1)
        unload()
        cozy.control.db.Settings.update(last_played_book=None).execute()
        emit_event("stop")


def unload():
    global __player
    global __current_track

    __player.set_state(Gst.State.NULL)
    __current_track = None


def prev_track():
    """
    Play the previous track of the current book.
    Plays the same track again when it is the first of the book.
    """
    global __player
    global __current_track
    album_tracks = cozy.control.db.get_tracks(get_current_track().book)
    current = get_current_track()
    index = list(album_tracks).index(current)
    previous = None
    if index > -1:
        previous = album_tracks[index - 1]

    save_current_track_position()

    if previous:
        play_pause(previous)
        save_current_track_position(track=current, pos=0)
        save_current_book_position(previous)
    else:
        first_track = __current_track
        __player.set_state(Gst.State.NULL)
        __current_track = None
        play_pause(first_track)
        save_current_book_position(current, 0)


def stop():
    """
    Stop playback.
    """
    global __player
    __player.set_state(Gst.State.PAUSED)


def rewind(seconds):
    """
    Seek seconds back in time. Caps at 0 seconds.
    :param seconds: time in seconds
    """
    global __player
    duration = get_current_duration()
    seek = duration - (seconds * 1000000000)
    if seek < 0:
        prev_track()
        seek = get_current_track().length * 1000000000 + seek
    __player.seek(__speed, Gst.Format.TIME, Gst.SeekFlags.FLUSH,
                  Gst.SeekType.SET, seek, Gst.SeekType.NONE, 0)
    save_current_track_position(seek)


def jump_to(seconds):
    """
    Jumps to the given second. Caps at 0 and the file length
    :param seconds: time in seconds
    """
    global __player
    global __speed

    new_position = int(seconds) * 1000000000
    if seconds < 0:
        new_position = 0
    elif int(seconds) > get_current_track().length:
        new_position = int(get_current_track().length) * 1000000000

    __player.seek(__speed, Gst.Format.TIME, Gst.SeekFlags.FLUSH,
                  Gst.SeekType.SET, new_position, Gst.SeekType.NONE, 0)
    save_current_track_position(new_position)


def jump_to_ns(ns):
    """
    Jumps to the given ns. Caps at 0 and the file length
    :param ns: time in ns
    """
    global __player
    global __speed

    new_position = ns
    if ns < 0:
        new_position = 0
    elif int(ns / 1000000000) > get_current_track().length:
        new_position = int(get_current_track().length) * 1000000000

    __player.seek(__speed, Gst.Format.TIME, Gst.SeekFlags.FLUSH,
                  Gst.SeekType.SET, new_position, Gst.SeekType.NONE, 0)
    save_current_track_position(new_position)


__playback_speed_timer_running = False


def auto_jump():
    """
    Automatically jump to the last playback position if posible
    """
    global __wait_to_seek
    global __speed
    global __set_speed

    if __wait_to_seek or __set_speed:
        query = Gst.Query.new_seeking(Gst.Format.TIME)
        if get_playbin().query(query):
            fmt, seek_enabled, start, end = query.parse_seeking()
            if seek_enabled:
                jump_to_ns(get_current_track().position)
                __wait_to_seek = False
                __set_speed = False
            if __set_speed:
                set_playback_speed(__speed)
                __set_speed = False


def set_playback_speed(speed):
    """
    Sets the playback speed in the gst player.
    Uses a timer to avoid crackling sound.
    """
    global __player
    global __speed
    global __playback_speed_timer_running

    __speed = speed
    if __playback_speed_timer_running:
        return

    __playback_speed_timer_running = True
    
    t = threading.Timer(0.2, __on_playback_speed_timer)
    t.name = "PlaybackSpeedDelayTimer"
    t.start()


def set_play_next(play_next):
    """
    True continues the playback after the current file.
    False stops playback after the current file.
    :param play_next: Boolean
    """
    global __play_next
    __play_next = play_next


def __on_playback_speed_timer():
    """
    Get's called after the playback speed changer timer is over.
    """
    global __speed
    global __playback_speed_timer_running

    position = get_current_duration(wait=True)
    __player.seek(__speed, Gst.Format.TIME, Gst.SeekFlags.FLUSH |
                  Gst.SeekFlags.ACCURATE, Gst.SeekType.SET, position, Gst.SeekType.NONE, 0)
    
    __playback_speed_timer_running = False


def __on_storage_changed(event, message):
    """
    """
    global __player

    if event == "storage-offline":
        if get_current_track() and message in get_current_track().file:
            cached_path = OfflineCache().get_cached_path(get_current_track())
            if not cached_path:
                stop()
                unload()
                emit_event("stop")


def load_file(track):
    """
    Loads a given track into the player.
    :param track: track to be loaded
    """
    global __current_track
    global __player

    if get_gst_player_state() == Gst.State.PLAYING:
        save_current_track_position()
        save_current_book_position(__current_track)

    __current_track = track
    emit_event("stop")
    __player.set_state(Gst.State.NULL)

    init()

    if cozy.control.filesystem_monitor.FilesystemMonitor().is_track_online(track):
        path = track.file
    else:
        path = OfflineCache().get_cached_path(track)
        if not path:
            path = track.file
    __player.set_property("uri", "file://" + path)
    __player.set_state(Gst.State.PAUSED)
    save_current_book_position(__current_track)
    cozy.control.db.Settings.update(last_played_book=__current_track.book).execute()
    cozy.control.db.Book.update(last_played=int(time.time())).where(
        cozy.control.db.Book.id == __current_track.book.id).execute()
    emit_event("track-changed", track)


def load_last_book():
    """
    Load the last played book into the player.
    """
    global __current_track
    global __player

    last_book = cozy.control.db.Settings.get().last_played_book

    if last_book and last_book.position != 0:

        query = cozy.control.db.Track.select().where(cozy.control.db.Track.id == last_book.position)
        if query.exists():
            last_track = query.get()

            if last_track:
                __player.set_state(Gst.State.NULL)
                if cozy.control.filesystem_monitor.FilesystemMonitor().is_track_online(last_track):
                    path = last_track.file
                else:
                    path = OfflineCache().get_cached_path(last_track)
                    if not path:
                        path = last_track.file
                __player.set_property("uri", "file://" + path)
                __player.set_state(Gst.State.PAUSED)
                __current_track = last_track

                cozy.control.db.Book.update(last_played=int(time.time())).where(
                    cozy.control.db.Book.id == last_book.id).execute()

                emit_event("track-changed", last_track)


def save_current_playback_speed(book=None, speed=None):
    """
    Save the current or given playback speed to the cozy.db.
    :param book: Optional: Save for the given book
    :param speed: Optional: Save the given speed
    """
    global __speed
    if book is None:
        book = get_current_track().book
    if speed is None:
        speed = __speed

    cozy.control.db.Book.update(playback_speed=speed).where(cozy.control.db.Book.id == book.id).execute()


def save_current_book_position(track, pos=None):
    """
    Saves the given track to it's book as the current position to the cozy.db.
    :param track: track object
    """
    if pos is None:
        pos = track.id
    cozy.control.db.Book.update(position=pos).where(
        cozy.control.db.Book.id == track.book.id).execute()


def save_current_track_position(pos=None, track=None):
    """
    Saves the current track position to the cozy.db.
    """
    if pos is None:
        pos = get_current_duration()

    if track is None:
        track = get_current_track()
    
    cozy.control.db.Track.update(position=pos).where(
        cozy.control.db.Track.id == track.id).execute()


def emit_event(event, message=None):
    """
    This function is used to notify listeners of player state changes.
    """
    for function in __listeners:
        function(event, message)


def dispose():
    """
    Sets the Gst player state to NULL.
    """
    global __player

    log.info("Closing.")
    __player.set_state(Gst.State.NULL)
