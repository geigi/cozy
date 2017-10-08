import gi
import logging
gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)

def __on_gst_message(bus, message):
  """
  Handle messages from gst.
  """

  t = message.type
  if t == Gst.MessageType.EOS:
    # Play next file
    # Set play position to 0
    # Check if audiobook is finished
    pass
  elif t == Gst.MessageType.ERROR:
    err, debug = message.parse_error()
    logging.error(err)
    logging.debug(debug)
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