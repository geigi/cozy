import os
import mutagen
import base64

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.flac import FLAC
from mutagen.mp3 import MP3

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
    print(e)
    pass

  return data

# TODO: Update Scan. Don't do this automatically for now. Go through all files and add new ones. Rescan files that have been changed from database. Remove entries from db that are not longer there. Important: don't forget playback position
# TODO: If file can not be found on playback ask for location of file. If provided, update location in db.
# TODO: Change folder: Media was moved. Here we need an update scan. Update the file locations of each file. Then do update scan.
# TODO: Drag & Drop files: Create folders and copy to correct location. Then import to db.
# TODO: Some sort of first import loading screen
# TODO: Refresh ui after every album?
def FirstImport(ui):
  """
  Import all supported audio files from the location set by the user in settings

  :param ui: main ui to update the throbber status
  """
  print("Starting first import...")
  for directory, subdirectories, files in os.walk(Settings.get().path):
    for file in files:
      if file.lower().endswith(('.mp3', '.ogg', '.flac')):
        path = os.path.join(directory, file)

        # Is the track already in the database?
        if (Track.select().where(Track.file == path).count() < 1):
          track = TrackContainer(mutagen.File(path), path)

          cover = None

          # getting the some data is file specific

          ### MP3 ###
          if file.lower().endswith('.mp3'):
            print("mp3")
            try:
              track.mutagen = ID3(path)
            except Exception as e:
              print("Track " + track.path + " has no ID3 Tag")
              continue

            cover = __getMP3Tag(track, "APIC")
            length = __getCommonTrackLength(TrackContainer(MP3(track.path), path))
            disk = __getMP3Tag(track, "TPOS")

            # for mp3 we are using the easyid3 functionality
            # because its syntax compatible to the rest
            track.mutagen = EasyID3(path)

          ### FLAC ###
          elif file.lower().endswith('.flac'):
            print("flac")
            track.mutagen = FLAC(path)
            disk = int(__getCommonDiskNumber(track))
            length = float(__getCommonTrackLength(track))
            cover = __getFLACCover(track)

          ### OGG ###
          elif file.lower().endswith('.ogg'):
            print("ogg")
            track.mutagen = OggVorbis(path)
            disk = int(__getCommonDiskNumber(track))
            length = float(__getCommonTrackLength(track))
            cover = __getOGGCover(track)

          modified = 0

          # try to get all the tags
          book_name = __getCommonTag(track, "album")
          author = __getCommonTag(track, "composer")
          reader = __getCommonTag(track, "author")
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

def UpdateDatabase():
  """
  Scans the audio book directory for changes and new files.
  """
  pass

def RebaseLocation():
  """
  This gets called when a user changes the location of the audio book folder.
  Every file in the database will be searched in the new location
  and the path will be updated in the database.
  """
  pass

def __importFile(path):
  """
  Imports all information about a track into the database.
  Note: This creates also a new album object when it doesnt exist yet. 
  Note: This does not check whether the file is already imported.
  """
  pass

def __updateFile(path):
  """
  Updates the information about this file in the database.
  """
  pass

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
    print("Could not find disk number for file " + track.path)
    print(e)
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
    print("Could not get length for file " + track.path)
    print(e)
    pass

  return length

def __getOGGCover(track):
  """
  Get the cover of an OGG file.
  
  :param track: Track object
  """
  try:
    cover = track.mutagen.get("metadata_block_picture", [])[0]
    print(length)
  except Exception as e:
    print("Could not load cover for file " + track.path)
    print(e)
    pass

  return cover

def __getFLACCover(track):
  """
  Get the cover of a FLAC file.
  
  :param track: Track object
  """
  try:
    cover = track.mutagen.pictures[0].data
    print(length)
  except Exception as e:
    print("Could not load cover for file " + track.path)
    print(e)
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

  try:
    value = track.mutagen.getall(tag)[0].data
    pass
  except Exception as e:
    print("Could not get mp3 tag " + tag + " for file " + track.path)
    print(e)
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
    print("Could not get tag " + tag + " for file " + track.path)
    pass

  return value