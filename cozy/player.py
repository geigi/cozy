import gi
import logging
log = logging.getLogger("player")
gi.require_version('Gst', '1.0')
from gi.repository import Gst

from cozy.db import *

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
  if t == Gst.MessageType.EOS:
    # try to load the next track of the book. 
    # Stop playback if there isn't any
    tracks = Tracks(GetCurrentTrack().book)
    current = GetCurrentTrack()
    save_next = False
    next_track = None
    try:
      for track in tracks:
        if save_next:
          next_track = track
          raise StopIteration

        if current == track:
          save_next = True

    except StopIteration:
      pass

    Track.update(position=0).where(Track.id == current.id).execute()

    if next_track is not None:
      Book.update(position=next_track.id).where(Book.id == next_track.book.id).execute()
      PlayPause(next_track)
    else:
      Stop()
      Book.update(position=None).where(Book.id == current.id).execute()
      Settings.update(last_played_book=None).execute()

  elif t == Gst.MessageType.ERROR:
    err, debug = message.parse_error()
    log.error(err)
    log.debug(debug)
    pass
  pass

__player = Gst.ElementFactory.make("playbin", "player")
__bus = __player.get_bus()
__bus.add_signal_watch()
__bus.connect("message", __on_gst_message)
__current_track = None

def GetGstBus():
  """
  Get the global gst bus.
  :return: gst bus
  """
  global __bus
  return __bus

def GetGstPlayerState():
  """
  Get the current state of the gst player.
  :return: gst player state
  """
  global __player
  success, state, pending = __player.get_state(10)
  return state

def GetCurrentDuration():
  """
  Current duration of track
  :returns: duration in ns
  """
  global __player
  duration = __player.query_position(Gst.Format.TIME)[1]
  return duration

def GetCurrentDurationUi():
  """
  current duration to display in ui
  :return m: minutes
  :return s: seconds
  """
  s,ns = divmod(GetCurrentDuration(), 1000000000)
  m,s = divmod(s, 60)
  return m,s

def GetCurrentTrack():
  global __current_track
  return Track.select().where(Track.id == __current_track.id).get()

def PlayPause(track):
  """
  Play a new file or pause/play if the file is already loaded.
  :param track: Track object that will be played/paused.
  """
  global __current_track
  global __player

  if __current_track == track or track is None:
    # Track is already selected, only play/pause
    if GetGstPlayerState() == Gst.State.PLAYING:
      __player.set_state(Gst.State.PAUSED)
      Track.update(position=GetCurrentDuration()).where(Track.id == GetCurrentTrack().id).execute()
    else: 
      __player.set_state(Gst.State.PLAYING)
  else:
    __current_track = track
    __player.set_state(Gst.State.NULL)
    __player.set_property("uri", "file://" + track.file)
    __player.set_state(Gst.State.PLAYING)
    Book.update(position = __current_track.id).where(Book.id == __current_track.book.id).execute()
    Settings.update(last_played_book = __current_track.book).execute()

def Stop():
  global __player
  __player.set_state(Gst.State.PAUSED)

def Rewind(seconds):
  """
  Seek seconds back in time. Caps at 0 seconds.
  :param seconds: time in seconds
  """
  global __player
  duration = GetCurrentDuration()
  seek = duration - (seconds * 1000000000)
  if seek < 0:
    # TODO: Go back to previous track
    seek = 0
  __player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, seek)
  Track.update(position=seek).where(Track.id == __current_track.id).execute()

def JumpTo(seconds):
  """
  Jumps to the given second. Caps at 0 and the file length
  :param seconds: time in seconds
  """
  global __player

  new_position = int(seconds) * 1000000000
  if seconds < 0:
    new_position = 0
  elif int(seconds) > GetCurrentTrack().length:
    new_position =  int(GetCurrentTrack().length) * 1000000000
  
  __player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, new_position)
  Track.update(position=new_position).where(Track.id == __current_track.id).execute()

def JumpToNs(ns):
  """
  Jumps to the given ns. Caps at 0 and the file length
  :param ns: time in ns
  """
  global __player

  new_position = ns
  if ns < 0:
    new_position = 0
  elif int(ns / 1000000000) > GetCurrentTrack().length:
    new_position =  int(GetCurrentTrack().length) * 1000000000
  
  __player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, new_position)
  Track.update(position=new_position).where(Track.id == __current_track.id).execute()

def LoadLastBook():
  global __current_track
  global __player

  last_book = Settings.get().last_played_book

  if last_book is not None and last_book.position != 0:

    query = Track.select().where(Track.id == last_book.position)
    if query.exists():
      last_track = query.get()

      if last_track is not None:
        __player.set_state(Gst.State.NULL)
        __player.set_property("uri", "file://" + last_track.file)
        __player.set_state(Gst.State.PAUSED)
        __current_track = last_track