from gi.repository import Gst

import gi
gi.require_version('Gst', '1.0')
import logging
log = logging.getLogger("player")

import cozy.db as db

Gst.init(None)


def __on_gst_message(bus, message):
    """
    Handle messages from gst.
    """

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


__player = Gst.ElementFactory.make("playbin", "player")
__bus = __player.get_bus()
__bus.add_signal_watch()
__bus.connect("message", __on_gst_message)
__current_track = None
__listeners = []
__wait_to_seek = False


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


def play_pause(track, jump=False):
    """
    Play a new file or pause/play if the file is already loaded.
    :param track: Track object that will be played/paused.
    """
    global __current_track
    global __player
    global __wait_to_seek

    __wait_to_seek = jump

    if __current_track == track or track is None:
        # Track is already selected, only play/pause
        if get_gst_player_state() == Gst.State.PLAYING:
            __player.set_state(Gst.State.PAUSED)
            emit_event("pause")
            db.Track.update(position=get_current_duration()).where(
                db.Track.id == get_current_track().id).execute()
        else:
            __player.set_state(Gst.State.PLAYING)
            emit_event("play")
    else:
        load_file(track)
        __player.set_state(Gst.State.PLAYING)
        emit_event("play")


def next_track():
    # try to load the next track of the book.
    # Stop playback if there isn't any
    global __current_track

    album_tracks = db.tracks(get_current_track().book)
    current = get_current_track()
    index = list(album_tracks).index(current)
    next_track = None
    if index + 1 < len(album_tracks):
        next_track = album_tracks[index + 1]

    play_pause(None)
    db.Track.update(position=0).where(db.Track.id == current.id).execute()

    if next_track is not None:
        db.Book.update(position=next_track.id).where(
            db.Book.id == next_track.book.id).execute()
        play_pause(next_track)
    else:
        stop()
        db.Book.update(position=0).where(db.Book.id == current.book.id).execute()
        __player.set_state(Gst.State.NULL)
        __current_track = None
        db.Settings.update(last_played_book=None).execute()
        emit_event("stop")


def prev_track():
    # try to load the next track of the book.
    # Stop playback if there isn't any
    global __player
    global __current_track
    album_tracks = db.tracks(get_current_track().book)
    current = get_current_track()
    index = list(album_tracks).index(current)
    previous = None
    if index > -1:
        previous = album_tracks[index - 1]

    db.Track.update(position=0).where(db.Track.id == current.id).execute()

    if previous is not None:
        db.Book.update(position=previous.id).where(
            db.Book.id == previous.book.id).execute()
        play_pause(previous)
    else:
        first_track = __current_track
        __player.set_state(Gst.State.NULL)
        __current_track = None
        play_pause(first_track)
        db.Book.update(position=0).where(db.Book.id == current.book.id).execute()


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
    db.Track.update(position=seek).where(db.Track.id == __current_track.id).execute()


def jump_to(seconds):
    """
    Jumps to the given second. Caps at 0 and the file length
    :param seconds: time in seconds
    """
    global __player

    new_position = int(seconds) * 1000000000
    if seconds < 0:
        new_position = 0
    elif int(seconds) > get_current_track().length:
        new_position = int(get_current_track().length) * 1000000000

    __player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, new_position)
    db.Track.update(position=new_position).where(
        db.Track.id == __current_track.id).execute()


def jump_to_ns(ns):
    """
    Jumps to the given ns. Caps at 0 and the file length
    :param ns: time in ns
    """
    global __player

    new_position = ns
    if ns < 0:
        new_position = 0
    elif int(ns / 1000000000) > get_current_track().length:
        new_position = int(get_current_track().length) * 1000000000

    __player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, new_position)
    db.Track.update(position=new_position).where(
        db.Track.id == __current_track.id).execute()


def auto_jump():
    """
    Automatically jump to the last playback position if posible
    """
    global __wait_to_seek
    if __wait_to_seek:
        query = Gst.Query.new_seeking(Gst.Format.TIME)
        if get_playbin().query(query):
            fmt, seek_enabled, start, end = query.parse_seeking()
            if seek_enabled:
                jump_to_ns(get_current_track().position)
                __wait_to_seek = False

def load_file(track):
    """
    Loads a given track into the player.
    :param track: track to be loaded
    """
    global __current_track
    global __player

    if get_gst_player_state() == Gst.State.PLAYING:
        db.Track.update(position=get_current_duration()).where(
            db.Track.id == get_current_track().id).execute()
        db.Book.update(position=__current_track.id).where(
            db.Book.id == __current_track.book.id).execute()

    __current_track = track
    emit_event("stop")
    __player.set_state(Gst.State.NULL)
    __player.set_property("uri", "file://" + track.file)
    __player.set_state(Gst.State.PAUSED)
    db.Book.update(position=__current_track.id).where(
        db.Book.id == __current_track.book.id).execute()
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


def emit_event(event, message=None):
    """
    This function is used to notify listeners of player state changes.
    """
    for function in __listeners:
        function(event, message)
