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

    if next_track is not None:
      PlayPause(next_track)
    else:
      Stop()

    # Play next file
    # Set play position to 0
    # Check if audiobook is finished
    pass
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
  return __current_track

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
    else: 
      __player.set_state(Gst.State.PLAYING)
  else:
    __current_track = track
    __player.set_state(Gst.State.NULL)
    __player.set_property("uri", "file://" + track.file)
    __player.set_state(Gst.State.PLAYING)

def Stop():
  global __player
  __player.set_state(Gst.State.READY)

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

def JumpTo(seconds):
  """
  Jumps to the given second. Caps at 0 and the file length
  :param seconds: time in seconds
  """
  global __player
  if seconds < 0:
    __player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
  elif seconds > GetCurrentTrack().length:
    __player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, int(GetCurrentTrack().length) * 1000000000)
  else:
    __player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, int(seconds) * 1000000000)

