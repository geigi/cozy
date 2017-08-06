import os
import mutagen
import base64

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.flac import FLAC

from cozy.db import *
from cozy.ui import *

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

def Import(ui):
  """
  Import all supported audio files from the location set by the user in settings

  :param ui: main ui to update the throbber status
  """
  ui.throbber.start()
  for directory, subdirectories, files in os.walk(Settings.get().path):
    for file in files:
      if file.lower().endswith(('.mp3', '.wav', '.flac', '.mp4', '.m4v')):
        path = os.path.join(directory, file)

        # Is the track already in the database?
        if (Track.select().where(Track.file == path).count() < 1):
          track = mutagen.File(path)

          cover = None

          # getting the cover data is file specific
          ### MP3 ###
          if file.lower().endswith('.mp3'):
            track = ID3(path)
            try:
              cover = track.getall("APIC")[0].data
              pass
            except Exception as e:
              pass

            # for mp3 we are using the easyid3 functionality
            # because its syntax compatible to the rest
            track = EasyID3(path)
          ### FLAC ###
          elif file.lower().endswith('.flac'):
            track = FLAC(path)
            try:
              cover = track.pictures[0].data
            except Exception as e:
              print("Could not load cover for file " + path)
              print(e)
              pass
          ### OGG ###
          elif file.lower().endswith('.ogg'):
            track = OggVorbis(path)
            try:
              cover = track.get("metadata_block_picture", [])[0]
            except Exception as e:
              print("Could not load cover for file " + path)
              print(e)
              pass

          book_name = "Nameless Book"
          author = "No Name"
          reader = "No Name"
          track_name = "Nameless Track"
          track_number = 0
          disk = 0

          # try to get all the tags
          try:
            book_name = track["album"][0]
            pass
          except Exception:
            pass

          try:
            author = track["composer"][0]
            pass
          except Exception:
            pass

          try:
            reader = track["author"][0]
            pass
          except Exception:
            pass

          try:
            track_name = track["title"][0]
            pass
          except Exception:
            pass

          try:
            track_number = int(track["tracknumber"][0])
            pass
          except Exception as e:
            print(e)
            pass

          # TODO: disk number
          try:
            disk = int(track["disk"][0])
            pass
          except Exception as e:
            print(e)
            pass

          # create database entries
          if (Book.select().where(Book.name == book_name).count() < 1):
            book = Book.create(name=book_name, 
                        author=author, 
                        reader=reader, 
                        position=0, 
                        rating=-1,
                        cover=cover)

          Track.create(name=track_name, 
                       number=track_number, 
                       position=0, 
                       book=book, 
                       file=path,
                       disk=disk)
  
  ui.refresh_content()
  ui.throbber.stop()