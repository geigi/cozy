import os
import mutagen
import base64
import logging
log = logging.getLogger("importer")

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.flac import FLAC
from mutagen.mp3 import MP3

from gi.repository import Gdk, GLib

from cozy.db import *
from cozy.ui import *

class TrackContainer:
  def __init__(self, track, path):
    self.mutagen = track
    self.path = path

def b64tobinary(b64):
  """
  Decode base64 to binary data

  :param b64: base64 data
  :return: decoded data
  """
  data = None
  try:
    data = base64.b64decode(b64)
  except (TypeError, ValueError) as e:
    log.error(e)
    pass

  return data

# TODO: If file can not be found on playback ask for location of file. If provided, update location in db.
# TODO: Drag & Drop files: Create folders and copy to correct location. Then import to db.
# TODO: Some sort of first import loading screen

def UpdateDatabase(ui):
  """
  Scans the audio book directory for changes and new files. 
  Also removes entries from the db that are no longer existent.
  """
  i = 0
  percent_counter = 0
  file_count = sum([len(files) for r, d, files in os.walk(Settings.get().path)])
  percent_threshold = file_count / 1000
  for directory, subdirectories, files in os.walk(Settings.get().path):
    for file in files:
      if file.lower().endswith(('.mp3', '.ogg', '.flac')):
        path = os.path.join(directory, file)

        # Is the track already in the database?
        if (Track.select().where(Track.file == path).count() < 1):
          __importFile(file, path)
        # Has the track changed on disk?
        elif Track.select().where(Track.file == path).first().modified < os.path.getmtime(path):
          __importFile(file, path, update=True)
        
        i = i + 1

        # don't flood gui updates
        if percent_counter < percent_threshold:
          percent_counter = percent_counter + 1
        else:
          percent_counter = 1
          Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.progress_bar.set_fraction, i / file_count)
          Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.update_progress_bar.set_fraction, i / file_count)

  # remove entries from the db that are no longer existent
  for track in Track.select():
    if not os.path.exists(track.file):
      track.delete_instance()

  # remove all books that have no tracks
  for book in Book.select():
    if Track.select().where(Track.book == book).count() < 1:
      book.delete_instance()

  Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.refresh_content)
  Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.switch_to_playing)

def RebaseLocation(ui, oldPath, newPath):
  """
  This gets called when a user changes the location of the audio book folder.
  Every file in the database updated with the new path.
  Note: This does not check for the existence of those files.
  """
  trackCount = Track.select().count()
  currentTrackCount = 0
  for track in Track.select():
    newFilePath = track.file.replace(oldPath, newPath)
    Track.update(file=newFilePath).where(Track.id == track.id).execute()
    Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.update_progress_bar.set_fraction, currentTrackCount / trackCount)
    currentTrackCount = currentTrackCount + 1;
  
  Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.switch_to_playing)

def __importFile(file, path, update=False):
  """
  Imports all information about a track into the database.
  Note: This creates also a new album object when it doesnt exist yet. 
  Note: This does not check whether the file is already imported.
  """

  track = TrackContainer(mutagen.File(path), path)
  cover = None
  reader = None

  # getting the some data is file specific
  ### MP3 ###
  if file.lower().endswith('.mp3'):
    log.debug("Importing mp3 " + track.path)
    try:
      track.mutagen = ID3(path)
    except Exception as e:
      log.warning("Track " + track.path + " has no ID3 Tags")
      return

    mp3 = TrackContainer(MP3(track.path), path)
    cover = __getMP3Tag(track, "APIC")
    length = __getCommonTrackLength(mp3)
    disk = __getMP3Tag(track, "TPOS")

    # for mp3 we are using the easyid3 functionality
    # because its syntax compatible to the rest
    track.mutagen = EasyID3(path)
    author = __getMP3Tag(mp3, "TCOM")
    reader = __getMP3Tag(mp3, "TPE1")

  ### FLAC ###
  elif file.lower().endswith('.flac'):
    log.debug("Importing flac " + track.path)
    track.mutagen = FLAC(path)
    disk = int(__getCommonDiskNumber(track))
    length = float(__getCommonTrackLength(track))
    cover = __getFLACCover(track)
    author = __getCommonTag(track, "composer")
    flac = FLAC(path)
    reader = flac["artist"][0]

  ### OGG ###
  elif file.lower().endswith('.ogg'):
    log.debug("Importing ogg " + track.path)
    track.mutagen = OggVorbis(path)
    disk = int(__getCommonDiskNumber(track))
    length = float(__getCommonTrackLength(track))
    cover = __getOGGCover(track)
    author = __getCommonTag(track, "composer")
    reader = __getCommonTag(track, "author")

  modified = os.path.getmtime(path)

  # try to get all the tags
  book_name = __getCommonTag(track, "album")
  track_name = __getCommonTag(track, "title")
  try:
    track_number = int(__getCommonTag(track, "tracknumber"))
  except ValueError:
    track_number = 0
    pass

  if book_name == None: book_name = os.path.basename(os.path.normpath(directory))
  if author == None: author = _("Unknown Author")
  if reader == None: reader = _("Unknown Reader")
  if track_name == None: track_name = os.path.splitext(file)[0]

  if update:
    if (Book.select().where(Book.name == book_name).count() < 1):
      book = Book.create(name=book_name, 
                  author=author, 
                  reader=reader, 
                  position=0, 
                  rating=-1,
                  cover=cover)
    else:
      book = Book.select().where(Book.name == book_name).get()
      Book.update(name=book_name,
                  author=author,
                  reader=reader,
                  cover=cover).where(Book.id == book.id).execute()

    Track.update(name=track_name, 
                 number=track_number,
                 book=book,
                 disk=disk,
                 length=length,
                 modified=modified).where(Track.file == path).execute()
  else:
    # create database entries
    if (Book.select().where(Book.name == book_name).count() < 1):
      book = Book.create(name=book_name, 
                  author=author, 
                  reader=reader, 
                  position=0, 
                  rating=-1,
                  cover=cover)
    else:
      book = Book.select().where(Book.name == book_name).get()

    Track.create(name=track_name, 
                 number=track_number,
                 position=0, 
                 book=book, 
                 file=path,
                 disk=disk,
                 length=length,
                 modified=modified)

def __removeFile(path):
  """
  Removes a file from the database. This also removes the 
  book entry when there are no tracks in the database anymore.
  """
  pass

def __getCommonDiskNumber(track):
  """
  Get the disk number for most files.
  
  :param track: Track object
  """
  disk = 0
  try:
    disk = int(track.mutagen["disk"][0])
  except Exception as e:
    log.debug("Could not find disk number for file " + track.path)
    log.debug(e)
    pass

  return disk

def __getCommonTrackLength(track):
  """
  Get the track length for most files.
  
  :param track: Track object
  """
  length = 0.0
  try:
    length = float(track.mutagen.info.length)
  except Exception as e:
    log.debug("Could not get length for file " + track.path)
    log.debug(e)
    pass

  return length

def __getOGGCover(track):
  """
  Get the cover of an OGG file.
  
  :param track: Track object
  """
  try:
    cover = track.mutagen.get("metadata_block_picture", [])[0]
  except Exception as e:
    log.debug("Could not load cover for file " + track.path)
    log.debug(e)
    pass

  return cover

def __getFLACCover(track):
  """
  Get the cover of a FLAC file.
  
  :param track: Track object
  """
  try:
    cover = track.mutagen.pictures[0].data
  except Exception as e:
    log.debug("Could not load cover for file " + track.path)
    log.debug(e)
    pass

  return cover

def __getMP3Tag(track, tag):
  """
  Get the first value of a id3 tag.
  
  :param track: Track object
  :param tag: Tag to be searched
  """
  if tag == "APIC":
    value = None
  elif tag == "TLEN":
    value = 0.0
  elif tag == "TPOS":
    value = 0
  elif tag == "TPE1":
    value = ""
  elif tag == "TCOM":
    value = ""

  try:
    if tag == "TPE1" or tag == "TCOM":
      value = track.mutagen[tag]
    else:
      value = track.mutagen.getall(tag)[0].data
    pass
  except Exception as e:
    log.debug("Could not get mp3 tag " + tag + " for file " + track.path)
    log.debug(e)
    pass

  return value

def __getCommonTag(track, tag):
  """
  Get the first value of a tag for most of the file types.

  :param track: Track object
  :param tag: Tag to be searched
  """
  value = None

  try:
    value = track.mutagen[tag][0]
    pass
  except Exception as e:
    log.debug("Could not get tag " + tag + " for file " + track.path)
    log.debug(e)
    pass

  return value