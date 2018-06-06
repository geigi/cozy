import os
import base64
import urllib
import urllib.parse
import shutil
import errno
import logging
import mutagen
import zlib
import time
import traceback
import contextlib
import wave

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from gi.repository import Gdk, GLib, Gst

import cozy.db as db
import cozy.artwork_cache as artwork_cache
import cozy.tools as tools
from cozy.offline_cache import OfflineCache

log = logging.getLogger("importer")


class TrackContainer:
    def __init__(self, track, path):
        self.mutagen = track
        self.path = path

class TrackData:
    name = None
    track_number = None
    position = 0
    book = None
    book_name = None
    file = None
    disk = None
    length = None
    modified = None
    crc32 = None
    author = None
    reader = None
    cover = None

    def __init__(self, file):
        self.file = file

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
    paths = []
    for location in db.Storage.select():
        if os.path.exists(location.path):
            paths.append(location.path)

    # clean artwork cache
    artwork_cache.delete_artwork_cache()

    # are UI buttons currently blocked?
    player_blocked, importer_blocked = ui.get_ui_buttons_blocked()

    i = 0
    percent_counter = 0
    file_count = 0
    for path in paths:
        file_count += sum([len(files) for r, d, files in os.walk(path)])
    
    percent_threshold = file_count / 1000
    failed = ""
    tracks_to_import = []
    # Tracks which changed and need to be updated if they are cached
    tracks_cache_update = []
    start = time.time()
    for path in paths:
        for directory, subdirectories, files in os.walk(path):
            for file in files:
                if file.lower().endswith(('.mp3', '.ogg', '.flac', '.m4a', '.wav')):
                    path = os.path.join(directory, file)

                    imported = True
                    try:
                        # Is the track already in the database?
                        if db.Track.select().where(db.Track.file == path).count() < 1:
                            imported, track_data = import_file(file, directory, path)
                            if track_data:
                                tracks_to_import.append(track_data)
                        # Has the track changed on disk?
                        elif tools.get_glib_settings().get_boolean("use-crc32"):
                            crc = __crc32_from_file(path)
                            # Is the value in the db already crc32 or is the crc changed?
                            if (db.Track.select().where(db.Track.file == path).first().modified != crc or 
                              db.Track.select().where(db.Track.file == path).first().crc32 != True):
                                imported, ignore = import_file(
                                    file, directory, path, True, crc)
                                tracks_cache_update.append(path)
                        # Has the modified date changed or is the value still a crc?
                        elif (db.Track.select().where(db.Track.file == path).first().modified < os.path.getmtime(path) or 
                          db.Track.select().where(db.Track.file == path).first().crc32 != False):
                            imported, ignore = import_file(file, directory, path, update=True)
                            tracks_cache_update.append(path)

                        if not imported:
                            failed += path + "\n"
                    except Exception as e:
                        log.warning("Could not import file: " + path)
                        log.warning(traceback.format_exc())
                        failed += path + "\n"

                    i = i + 1

                    if len(tracks_to_import) > 100:
                        write_tracks_to_db(tracks_to_import)
                        tracks_to_import = []

                    # don't flood gui updates
                    if percent_counter < percent_threshold:
                        percent_counter = percent_counter + 1
                    else:
                        percent_counter = 1
                        Gdk.threads_add_idle(
                            GLib.PRIORITY_DEFAULT_IDLE, ui.titlebar.progress_bar.set_fraction, i / file_count)
                        Gdk.threads_add_idle(
                            GLib.PRIORITY_DEFAULT_IDLE, ui.titlebar.update_progress_bar.set_fraction, i / file_count)


    write_tracks_to_db(tracks_to_import)
    end = time.time()
    log.info("Total import time: " + str(end - start))

    # remove entries from the db that are no longer existent
    db.remove_invalid_entries()
    artwork_cache.generate_artwork_cache()

    Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.refresh_content)
    Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.switch_to_playing)
    Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.check_for_tracks)

    if len(failed) > 0:
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE,
                             ui.display_failed_imports, failed)

    OfflineCache().update_cache(tracks_cache_update)
    OfflineCache()._process_queue()

def write_tracks_to_db(tracks):
    """
    """
    if tracks is None or len(tracks) < 1:
        return

    fields = [db.Track.name, db.Track.number, db.Track.disk, db.Track.position, db.Track.book, db.Track.file, db.Track.length, db.Track.modified, db.Track.crc32]
    data = list((t.name, t.track_number, t.disk, t.position, t.book, t.file, t.length, t.modified, t.crc32) for t in tracks)
    db.Track.insert_many(data, fields=fields).execute()

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
        db.StorageBlackList.update(path=newFilePath).where(db.StorageBlackList.path == track.file).execute()
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE,
                             ui.titlebar.update_progress_bar.set_fraction, currentTrackCount / trackCount)
        currentTrackCount = currentTrackCount + 1

    Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.switch_to_playing)


def import_file(file, directory, path, update=False, crc=None):
    """
    Imports all information about a track into the database.
    Note: This creates also a new album object when it doesnt exist yet.
    Note: This does not check whether the file is already imported.
    :return: True if file was imported, otherwise False
    :return: Track object to be imported when everything passed successfully and track is not in the db already.
    """
    if db.is_blacklisted(path):
        return True, None

    media_type = tools.__get_media_type(path)
    track = TrackContainer(None, path)
    cover = None
    reader = None
    track_number = None
    track_data = None
    
    # getting the some data is file specific
    ### MP3 ###
    if media_type == "audio/mpeg":
        track_data = _get_mp3_tags(track, path)

    ### FLAC ###
    elif media_type == "audio/flac":
        track_data = _get_flac_tags(track, path)

    ### OGG ###
    elif media_type == "audio/ogg":
        track_data = _get_ogg_tags(track, path)

    ### MP4 ###
    elif media_type == "audio/mp4" or media_type == "audio/x-m4a":
        track_data = _get_mp4_tags(track, path)

    ### WAV ###
    elif media_type == "audio/wav" or media_type == "audio/x-wav":
        track_data = TrackData(path)
        track_data.length = __get_wav_track_length(path)

    ### File will not be imported ###
    else:
        log.warning("Skipping file " + path + " because of mime type " + media_type + ".")
        return False, None

    track_data.modified = __get_last_modified(crc, path)

    # try to get all the remaining tags
    try:
        if track_data.track_number is None:
            # The track number can contain the total number of tracks
            track_text = str(__get_common_tag(track, "tracknumber"))
            track_data.track_number = int(track_text.split("/")[0])
    except Exception as e:
        log.debug(e)
        track_data.track_number = 0

    if track_data.book_name is None:
        track_data.book_name = __guess_book_name(directory)
    if track_data.author is None or track_data.author == "":
        if track_data.reader and len(track_data.reader) > 0:
            track_data.author = track_data.reader
            track_data.reader = ""
        else:
            track_data.author = _("Unknown Author")
    if track_data.reader is None or track_data.reader == "":
        track_data.reader = _("Unknown Reader")
    if track_data.name is None:
        track_data.name = __guess_title(file)
    if not track_data.disk:
        track_data.disk = 1
    if not track_data.length:
        # Try to get the length by using gstreamer
        success, track_data.length = get_gstreamer_length(file)
        if not success:
            return False, None

    track_data.crc32 = tools.get_glib_settings().get_boolean("use-crc32")

    if update:
        if db.Book.select().where(db.Book.name == track_data.book_name).count() < 1:
            track_data.book = db.Book.create(name=track_data.book_name,
                                  author=track_data.author,
                                  reader=track_data.reader,
                                  position=0,
                                  rating=-1,
                                  cover=track_data.cover)
        else:
            track_data.book = db.Book.select().where(db.Book.name == track_data.book_name).get()
            db.Book.update(name=track_data.book_name,
                           author=track_data.author,
                           reader=track_data.reader,
                           cover=track_data.cover).where(db.Book.id == track_data.book.id).execute()

        db.Track.update(name=track_data.name,
                        number=track_data.track_number,
                        book=track_data.book,
                        disk=track_data.disk,
                        length=track_data.length,
                        modified=track_data.modified,
                        crc32=track_data.crc32).where(db.Track.file == track_data.file).execute()
    else:
        # create database entries
        if db.Book.select().where(db.Book.name == track_data.book_name).count() < 1:
            track_data.book = db.Book.create(name=track_data.book_name,
                                  author=track_data.author,
                                  reader=track_data.reader,
                                  position=0,
                                  rating=-1,
                                  cover=track_data.cover)
        else:
            track_data.book = db.Book.select().where(db.Book.name == track_data.book_name).get()

        return True, track_data

    return True, None

def get_gstreamer_length(path):
    """
    This function determines the length of an audio file using gstreamer.
    This should be used as last resort if mutagen doesn't help us.
    """
    player = Gst.ElementFactory.make("playbin", "player")
    player.set_property("uri", "file://" + path)
    player.set_state(Gst.State.PAUSED)
    suc, state, pending = player.get_state(Gst.CLOCK_TIME_NONE)
    while state != Gst.State.PAUSED:
        suc, state, pending = player.get_state(Gst.CLOCK_TIME_NONE)
    success, duration = player.query_duration(Gst.Format.TIME)
    player.set_state(Gst.State.NULL)
    return success, int(duration / 1000000000)

def __get_last_modified(crc, path):
    global settings
    if tools.get_glib_settings().get_boolean("use-crc32"):
        import binascii
        if crc is None:
            crc = __crc32_from_file(path)
        modified = crc
    else:
        modified = os.path.getmtime(path)
    return modified


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
                                 ui.titlebar.update_progress_bar.set_fraction, cur / count)

    Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.scan, None, False)


def copy_to_audiobook_folder(path):
    """
    Copies the given path (folder or file) to the audio book folder.
    """
    try:
        name = os.path.basename(os.path.normpath(path))
        shutil.copytree(path, db.Storage.select().where(db.Storage.default == True).get().path + "/" + name)
    except OSError as exc:
        if exc.errno == errno.ENOTDIR:
            try:
                shutil.copy(path, db.Storage.select().where(db.Storage.default == True).get().path)
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


def _get_mp3_tags(track, path):
    """
    Tries to load embedded tags from given file.
    :return: TrackData object
    """
    track_data = TrackData(path)
    log.debug("Importing mp3 " + track.path)
    try:
        track.mutagen = ID3(path)
    except Exception as e:
        log.warning("Track " + track.path +
                    " has no mp3 tags. Now guessing from file and folder name...")
        return track_data

    mp3 = TrackContainer(MP3(track.path), path)
    track_data.cover = __get_mp3_tag(track, "APIC")
    track_data.length = __get_common_track_length(mp3)
    track_data.disk = __get_mp3_tag(track, "TPOS")

    # for mp3 we are using the easyid3 functionality
    # because its syntax compatible to the rest
    track.mutagen = EasyID3(path)
    track_data.author = __get_mp3_tag(mp3, "TCOM")
    track_data.reader = __get_mp3_tag(mp3, "TPE1")
    track_data.book_name = __get_common_tag(track, "album")
    track_data.name = __get_common_tag(track, "title")

    # other fields for the author and reader
    if track_data.author is None or track_data.author == "":
        track_data.author = __get_mp3_tag(mp3, "TPE1")
        track_data.reader = __get_mp3_tag(mp3, "TPE2")

    return track_data


def _get_flac_tags(track, path):
    """
    Tries to load embedded tags from given file.
    :return: TrackData object
    """
    track_data = TrackData(path)
    log.debug("Importing flac " + track.path)
    try:
        track.mutagen = FLAC(path)
    except Exception as e:
        log.warning("Track " + track.path +
                    " has no valid tags. Now guessing from file and folder name...")
        return track_data

    track_data.disk = int(__get_common_disk_number(track))
    track_data.length = float(__get_common_track_length(track))
    track_data.cover = __get_flac_cover(track)
    track_data.author = __get_common_tag(track, "composer")
    track_data.reader = track.mutagen["artist"][0]
    track_data.book_name = __get_common_tag(track, "album")
    track_data.name = __get_common_tag(track, "title")

    return track_data


def _get_ogg_tags(track, path):
    """
    Tries to load embedded tags from given file.
    :return: TrackData object
    """
    track_data = TrackData(path)
    log.debug("Importing ogg " + track.path)
    try:
        track.mutagen = OggVorbis(path)
    except Exception as e:
        log.warning("Track " + track.path +
                    " has no valid tags. Now guessing from file and folder name...")
        return track_data

    track_data.disk = int(__get_common_disk_number(track))
    track_data.length = float(__get_common_track_length(track))
    track_data.cover = __get_ogg_cover(track)
    track_data.author = __get_common_tag(track, "composer")
    track_data.reader = __get_common_tag(track, "artist")
    track_data.book_name = __get_common_tag(track, "album")
    track_data.name = __get_common_tag(track, "title")

    return track_data


def _get_mp4_tags(track, path):
    """
    Tries to load embedded tags from given file.
    :return: TrackData object
    """
    track_data = TrackData(path)
    log.debug("Importing mp4 " + track.path)
    try:
        track.mutagen = MP4(path)
    except Exception as e:
        log.warning("Track " + track.path +
                    " has no valid tags. Now guessing from file and folder name...")
        log.warning(e)
        return track_data

    try:
        track_data.disk = int(track.mutagen["disk"][0][0])
    except Exception as e:
        log.debug(e)
        track_data.disk = 0
    track_data.length = float(track.mutagen.info.length)
    track_data.cover = __get_mp4_cover(track)
    track_data.author = __get_common_tag(track, "\xa9wrt")
    track_data.reader = __get_common_tag(track, "\xa9ART")
    try:
        track_data.track_number = int(track.mutagen["trkn"][0][0])
    except Exception as e:
        log.debug(e)
        track_data.track_number = 0
    track_data.book_name = __get_common_tag(track, "\xa9alb")
    track_data.name = __get_common_tag(track, "\xa9nam")

    return track_data


def __guess_title(file):
    """
    Guess the track title based on the filename.
    """
    return os.path.splitext(file)[0]


def __guess_book_name(directory):
    """
    Guess the book title based on the directory name.
    """
    return os.path.basename(os.path.normpath(directory))


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


def __get_wav_track_length(path):
    """
    Calculates the length of a wav file.
    :return: track length as float
    """
    with contextlib.closing(wave.open(path, 'r')) as f:
        frames = f.getnframes()
        rate = f.getframerate()
        duration = frames / float(rate)

        return duration

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
    elif tag == "TPE2":
        value = ""

    try:
        if tag == "TPE1" or tag == "TCOM" or tag == "TPE2":
            value = track.mutagen[tag]
        elif tag == "TPOS":
            disks = str(track.mutagen[tag])
            disk = disks.split("/")[0]
            value = int(disk)
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

    try:
        value = track.mutagen[tag][0]
    except Exception as e:
        log.info("Could not get tag " + tag + " for file " + track.path)
        log.info(e)

    return value



# thanks to oleg-krv
def __crc32_from_file(filename):
    crc_file = 0
    try:
        prev = 0
        for eachLine in open(filename, 'rb'):
            prev = zlib.crc32(eachLine, prev)
        crc_file = (prev & 0xFFFFFFFF)
    except Exception as e:
        log.warning(e)
    
    return crc_file