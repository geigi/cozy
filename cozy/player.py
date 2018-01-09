import threading
from gi.repository import Gst

import gi
gi.require_version('Gst', '1.0')
import logging
log = logging.getLogger("player")

import cozy.db as db

Gst.init(None)

__speed = 1.0
__set_speed = False
__current_track = None
__listeners = []
__wait_to_seek = False
__player = None
__bus = None


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
        else:
            __player.set_state(Gst.State.PLAYING)
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

    if __player is not None:
        dispose()
        __player = None

    __player = Gst.ElementFactory.make("playbin", "player")
    __scaletempo = Gst.ElementFactory.make("scaletempo", "scaletempo")
    __scaletempo.sync_state_with_parent()

    __audiobin = Gst.Bin("audioline")
    __audiobin.add(__scaletempo)

    __audiosink = Gst.ElementFactory.make("autoaudiosink", "audiosink")
    __audiobin.add(__audiosink)

    __scaletempo.link(__audiosink)
    __pad = __scaletempo.get_static_pad("sink")
    __audiobin.add_pad(Gst.GhostPad("sink", __pad))

    __player.set_property("audio-sink", __audiobin)

    __bus = __player.get_bus()
    __bus.add_signal_watch()
    __bus.connect("message", __on_gst_message)


init()


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


def get_current_duration():
    """
    Current duration of track
    :returns: duration in ns
    """
    global __player
    duration = __player.query_position(Gst.Format.TIME)[1]
    return duration


def get_current_duration_ui():
    """
    current duration to display in ui
    :return m: minutes
    :return s: seconds
    """
    s, ns = divmod(get_current_duration(), 1000000000)
    m, s = divmod(s, 60)
    return m, s


def get_current_track():
    """
    Get the currently loaded track object.
    :return: currently loaded track object
    """
    global __current_track
    if __current_track is not None:
        return db.Track.select().where(db.Track.id == __current_track.id).get()
    else:
        return None


def add_player_listener(function):
    """
    Add a listener to listen to changes from the player.
    """
    global __listeners
    __listeners.append(function)


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
            emit_event("play")
    else:
        load_file(track)
        __player.set_state(Gst.State.PLAYING)
        emit_event("play")

    __set_speed = True


def next_track():
    """
    Play the next track of the current book.
    Stops playback if there isn't any.
    """
    global __current_track

    album_tracks = db.tracks(get_current_track().book)
    current = get_current_track()
    index = list(album_tracks).index(current)
    next_track = None
    if index + 1 < len(album_tracks):
        next_track = album_tracks[index + 1]

    play_pause(None)
    save_current_track_position(0)

    if next_track is not None:
        save_current_book_position(next_track)
        play_pause(next_track)
    else:
        stop()
        save_current_book_position(current, 0)
        __player.set_state(Gst.State.NULL)
        __current_track = None
        db.Settings.update(last_played_book=None).execute()
        emit_event("stop")


def prev_track():
    """
    Play the previous track of the current book.
    Plays the same track again when it is the first of the book.
    """
    global __player
    global __current_track
    album_tracks = db.tracks(get_current_track().book)
    current = get_current_track()
    index = list(album_tracks).index(current)
    previous = None
    if index > -1:
        previous = album_tracks[index - 1]

    save_current_track_position()

    if previous is not None:
        save_current_book_position(previous)
        play_pause(previous)
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
        # TODO: Go back to previous track
        seek = 0
    __player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, seek)
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
    t.start()


def __on_playback_speed_timer():
    """
    Get's called after the playback speed changer timer is over.
    """
    global __speed
    global __playback_speed_timer_running
    __playback_speed_timer_running = False

    position = get_current_duration()
    __player.seek(__speed, Gst.Format.TIME, Gst.SeekFlags.FLUSH |
                  Gst.SeekFlags.ACCURATE, Gst.SeekType.SET, position, Gst.SeekType.NONE, 0)


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

    __player.set_property("uri", "file://" + track.file)
    __player.set_state(Gst.State.PAUSED)
    save_current_book_position(__current_track)
    db.Settings.update(last_played_book=__current_track.book).execute()
    emit_event("track-changed")


def load_last_book():
    """
    Load the last played book into the player.
    """
    global __current_track
    global __player

    last_book = db.Settings.get().last_played_book

    if last_book is not None and last_book.position != 0:

        query = db.Track.select().where(db.Track.id == last_book.position)
        if query.exists():
            last_track = query.get()

            if last_track is not None:
                __player.set_state(Gst.State.NULL)
                __player.set_property("uri", "file://" + last_track.file)
                __player.set_state(Gst.State.PAUSED)
                __current_track = last_track
                emit_event("track-changed")


def save_current_book_position(track, pos=None):
    """
    Saves the given track to it's book as the current position to the db.
    :param track: track object
    """
    if pos is None:
        pos = track.id
    db.Book.update(position=pos).where(
        db.Book.id == track.book.id).execute()


def save_current_track_position(pos=None):
    """
    Saves the current track position to the db.
    """
    if pos is None:
        pos = get_current_duration()
    db.Track.update(position=pos).where(
        db.Track.id == get_current_track().id).execute()


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
    __player.set_state(Gst.State.NULL)
