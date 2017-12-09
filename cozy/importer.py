import os
import base64
import urllib, urllib.parse
import shutil
import errno
import logging
import mutagen

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from gi.repository import Gdk, GLib

import cozy.db as db
log = logging.getLogger("importer")


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

    return data


def update_database(ui):
    """
    Scans the audio book directory for changes and new files.
    Also removes entries from the db that are no longer existent.
    """
    if not os.path.exists(db.Settings.get().path):
        # TODO: Notify the user about this
        return

    i = 0
    percent_counter = 0
    file_count = sum([len(files)
                      for r, d, files in os.walk(db.Settings.get().path)])
    percent_threshold = file_count / 1000
    failed = ""
    for directory, subdirectories, files in os.walk(db.Settings.get().path):
        for file in files:
            if file.lower().endswith(('.mp3', '.ogg', '.flac', '.m4a')):
                path = os.path.join(directory, file)

                imported = True
                # Is the track already in the database?
                if db.Track.select().where(db.Track.file == path).count() < 1:
                    imported = import_file(file, directory, path)
                # Has the track changed on disk?
                elif db.Track.select().where(db.Track.file == path).first().modified < os.path.getmtime(path):
                    imported = import_file(file, directory, path, update=True)

                if not imported:
                    failed += path + "\n"

                i = i + 1

                # don't flood gui updates
                if percent_counter < percent_threshold:
                    percent_counter = percent_counter + 1
                else:
                    percent_counter = 1
                    Gdk.threads_add_idle(
                        GLib.PRIORITY_DEFAULT_IDLE, ui.progress_bar.set_fraction, i / file_count)
                    Gdk.threads_add_idle(
                        GLib.PRIORITY_DEFAULT_IDLE, ui.update_progress_bar.set_fraction, i / file_count)

    # remove entries from the db that are no longer existent
    for track in db.Track.select():
        if not os.path.exists(track.file):
            track.delete_instance()

    # remove all books that have no tracks
    for book in db.Book.select():
        if db.Track.select().where(db.Track.book == book).count() < 1:
            book.delete_instance()

    Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.refresh_content)
    Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.switch_to_playing)
    Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.check_for_tracks)

    if len(failed) > 0:
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE,
                             ui.display_failed_imports, failed)


def rebase_location(ui, oldPath, newPath):
    """
    This gets called when a user changes the location of the audio book folder.
    Every file in the database updated with the new path.
    Note: This does not check for the existence of those files.
    """
    trackCount = db.Track.select().count()
    currentTrackCount = 0
    for track in db.Track.select():
        newFilePath = track.file.replace(oldPath, newPath)
        db.Track.update(file=newFilePath).where(
            db.Track.id == track.id).execute()
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE,
                             ui.update_progress_bar.set_fraction, currentTrackCount / trackCount)
        currentTrackCount = currentTrackCount + 1

    Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.switch_to_playing)


def import_file(file, directory, path, update=False):
    """
    Imports all information about a track into the database.
    Note: This creates also a new album object when it doesnt exist yet.
    Note: This does not check whether the file is already imported.
    :return: True if file was imported, otherwise False
    """

    media_type = __get_media_type(path)
    mutagen.File
    track = TrackContainer(None, path)
    cover = None
    reader = None
    track_number = None

    # getting the some data is file specific
    ### MP3 ###
    if media_type is "mp3":
        log.debug("Importing mp3 " + track.path)
        try:
            track.mutagen = ID3(path)
        except Exception as e:
            log.warning("Track " + track.path +
                        " is no valid MP3 file. Skipping...")
            return False

        mp3 = TrackContainer(MP3(track.path), path)
        cover = __get_mp3_tag(track, "APIC")
        length = __get_common_track_length(mp3)
        disk = __get_mp3_tag(track, "TPOS")

        # for mp3 we are using the easyid3 functionality
        # because its syntax compatible to the rest
        track.mutagen = EasyID3(path)
        author = __get_mp3_tag(mp3, "TCOM")
        reader = __get_mp3_tag(mp3, "TPE1")
        book_name = __get_common_tag(track, "album")
        track_name = __get_common_tag(track, "title")

    ### FLAC ###
    elif media_type is "flac":
        log.debug("Importing flac " + track.path)
        try:
            track.mutagen = FLAC(path)
        except Exception as e:
            log.warning("Track " + track.path +
                        " is not a valid FLAC file. Skipping...")
            return False

        disk = int(__get_common_disk_number(track))
        length = float(__get_common_track_length(track))
        cover = __get_flac_cover(track)
        author = __get_common_tag(track, "composer")
        reader = track.mutagen["artist"][0]
        book_name = __get_common_tag(track, "album")
        track_name = __get_common_tag(track, "title")

    ### OGG ###
    elif media_type is "ogg":
        log.debug("Importing ogg " + track.path)
        try:
            track.mutagen = OggVorbis(path)
        except Exception as e:
            log.warning("Track " + track.path +
                        " is not a valid OGG file. Skipping...")
            return False

        disk = int(__get_common_disk_number(track))
        length = float(__get_common_track_length(track))
        cover = __get_ogg_cover(track)
        author = __get_common_tag(track, "composer")
        reader = __get_common_tag(track, "author")
        book_name = __get_common_tag(track, "album")
        track_name = __get_common_tag(track, "title")

    ### MP4 ###
    elif media_type is "mp4":
        log.debug("Importing mp4 " + track.path)
        try:
            track.mutagen = MP4(path)
        except Exception as e:
            log.warning("Track " + track.path +
                        " is not a valid MP4 file. Skipping...")
            log.warning(e)
            return False

        try:
            disk = int(track.mutagen["disk"][0][0])
        except Exception as e:
            log.debug(e)
            disk = 0
        length = float(track.mutagen.info.length)
        cover = __get_mp4_cover(track)
        author = __get_common_tag(track, "\xa9wrt")
        reader = __get_common_tag(track, "\xa9ART")
        try:
            track_number = int(track.mutagen["trkn"][0][0])
        except Exception as e:
            log.debug(e)
            track_number = 0
        book_name = __get_common_tag(track, "\xa9alb")
        track_name = __get_common_tag(track, "\xa9nam")

    ### File will not be imported ###
    else:
        log.warning("Skipping file: " + path)
        return False

    modified = os.path.getmtime(path)

    # try to get all the remaining tags
    try:
        if track_number is None:
            track_number = int(__get_common_tag(track, "tracknumber"))
    except Exception as e:
        log.debug(e)
        track_number = 0

    if book_name is None:
        book_name = os.path.basename(os.path.normpath(directory))
    if author is None or author == "":
        author = _("Unknown Author")
    if reader is None or reader == "":
        reader = _("Unknown Reader")
    if track_name is None:
        track_name = os.path.splitext(file)[0]

    if update:
        if db.Book.select().where(db.Book.name == book_name).count() < 1:
            book = db.Book.create(name=book_name,
                                  author=author,
                                  reader=reader,
                                  position=0,
                                  rating=-1,
                                  cover=cover)
        else:
            book = db.Book.select().where(db.Book.name == book_name).get()
            db.Book.update(name=book_name,
                           author=author,
                           reader=reader,
                           cover=cover).where(db.Book.id == book.id).execute()

        db.Track.update(name=track_name,
                        number=track_number,
                        book=book,
                        disk=disk,
                        length=length,
                        modified=modified).where(db.Track.file == path).execute()
    else:
        # create database entries
        if db.Book.select().where(db.Book.name == book_name).count() < 1:
            book = db.Book.create(name=book_name,
                                  author=author,
                                  reader=reader,
                                  position=0,
                                  rating=-1,
                                  cover=cover)
        else:
            book = db.Book.select().where(db.Book.name == book_name).get()

        db.Track.create(name=track_name,
                        number=track_number,
                        position=0,
                        book=book,
                        file=path,
                        disk=disk,
                        length=length,
                        modified=modified)

    return True

def __get_media_type(path):
    """
    Tests a given file for the media type.
    :param path: Path to the file
    :return: Media type as string
    """
    try:
        fileobj = open(path, "rb")
        header = fileobj.read(128)
    except IOError as e:
        log.warning(e)
        return ""

    path = path.lower()
    
    # MP4
    if b"ftyp" in header or b"mp4" in header:
        return "mp4"
    # OGG
    elif header.startswith(b"OggS") or b"\x01vorbis" in header:
        return "ogg"
    # FLAC
    elif header.startswith(b"fLaC") or path.endswith(".flac"):
        return "flac"
    # MP3
    elif header.startswith(b"ID3") or path.endswith(".mp3") or path.endswith(".mp2") or path.endswith(".mpg") or path.endswith(".mpeg"):
        return "mp3"
    else:
        return ""

def copy(ui, selection):
    """
    Copy the selected files to the audiobook location.
    """
    selection = selection.get_uris()

    # count the work
    count = len(selection)
    cur = 0

    for uri in selection:
        parsed_path = urllib.parse.urlparse(uri)
        path = urllib.parse.unquote(parsed_path.path)
        if os.path.isfile(path) or os.path.isdir(path):
            copy_to_audiobook_folder(path)
            cur = cur + 1
            Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE,
                                 ui.update_progress_bar.set_fraction, cur / count)

    Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.scan, None, False)


def copy_to_audiobook_folder(path):
    """
    Copies the given path (folder or file) to the audio book folder.
    """
    try:
        name = os.path.basename(os.path.normpath(path))
        shutil.copytree(path, db.Settings.get().path + "/" + name)
    except OSError as exc:
        if exc.errno == errno.ENOTDIR:
            try:
                shutil.copy(path, db.Settings.get().path)
            except OSError as e:
                if e.errno == 95:
                    log.error("Could not import file " + path)
                    log.error(exc)
                else:
                    log.error(e)
        elif exc.errno == errno.ENOTSUP:
            log.error("Could not import file " + path)
            log.error(exc)
        else:
            log.error("Could not import file " + path)
            log.error(exc)


def __remove_file(path):
    """
    Removes a file from the database. This also removes the
    book entry when there are no tracks in the database anymore.
    """
    pass


def __get_common_disk_number(track):
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

    return disk


def __get_common_track_length(track):
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

    return length


def __get_ogg_cover(track):
    """
    Get the cover of an OGG file.

    :param track: Track object
    """
    cover = None

    try:
        cover = track.mutagen.get("metadata_block_picture", [])[0]
    except Exception as e:
        log.debug("Could not load cover for file " + track.path)
        log.debug(e)

    return cover


def __get_mp4_cover(track):
    """
    Get the cover of an MP4 file.

    :param track: Track object
    """
    cover = None

    try:
        cover = track.mutagen.tags["covr"][0]
    except Exception as e:
        log.debug("Could not load cover for file " + track.path)
        log.debug(e)

    return cover


def __get_flac_cover(track):
    """
    Get the cover of a FLAC file.

    :param track: Track object
    """
    cover = None
    
    try:
        cover = track.mutagen.pictures[0].data
    except Exception as e:
        log.debug("Could not load cover for file " + track.path)
        log.debug(e)

    return cover


def __get_mp3_tag(track, tag):
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
    except Exception as e:
        log.debug("Could not get mp3 tag " + tag + " for file " + track.path)
        log.debug(e)

    return value


def __get_common_tag(track, tag):
    """
    Get the first value of a tag for most of the file types.

    :param track: Track object
    :param tag: Tag to be searched
    """
    value = None

    try:
        value = track.mutagen[tag][0]
    except Exception as e:
        log.info("Could not get tag " + tag + " for file " + track.path)
        log.info(e)

    return value
