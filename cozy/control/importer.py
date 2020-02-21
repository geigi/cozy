import os
import base64
import urllib
import urllib.parse
import shutil
import errno
import logging
import time
import traceback
import contextlib
import wave

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis
from peewee import __version__ as PeeweeVersion
from gi.repository import Gdk, GLib, Gst

import cozy.control.artwork_cache as artwork_cache
import cozy.tools as tools
import cozy.control.player
from cozy.control.db import is_blacklisted, remove_invalid_entries
from cozy.control.offline_cache import OfflineCache
from cozy.model.book import Book
from cozy.model.storage import Storage
from cozy.model.storage_blacklist import StorageBlackList
from cozy.model.track import Track
from cozy.report import reporter

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


def update_database(ui, force=False):
    """
    Scans the audio book directory for changes and new files.
    Also removes entries from the db that are no longer existent.
    """
    paths = []
    for location in Storage.select():
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
                if file.lower().endswith(('.mp3', '.ogg', '.flac', '.m4a', '.wav', '.opus')):
                    path = os.path.join(directory, file)

                    imported = True
                    try:
                        if force:
                            imported, ignore = import_file(file, directory, path, True)
                            tracks_cache_update.append(path)
                        # Is the track already in the database?
                        elif Track.select().where(Track.file == path).count() < 1:
                            imported, track_data = import_file(file, directory, path)
                            if track_data:
                                tracks_to_import.append(track_data)
                        # Has the modified date changed?
                        elif (Track.select().where(
                                Track.file == path).first().modified < os.path.getmtime(path)):
                            imported, ignore = import_file(file, directory, path, update=True)
                            tracks_cache_update.append(path)

                        if not imported:
                            failed += path + "\n"
                    except UnicodeEncodeError as e:
                        log.warning("Could not import file because of invalid path or filename: " + path)
                        reporter.exception("importer", e)
                        failed += path + "\n"
                    except Exception as e:
                        log.warning("Could not import file: " + path)
                        log.warning(traceback.format_exc())
                        reporter.exception("importer", e)
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
    remove_invalid_entries()
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

    if PeeweeVersion[0] == '2':
        data = list({"name": t.name, "number": t.track_number, "disk": t.disk, "position": t.position, "book": t.book,
                     "file": t.file, "length": t.length, "modified": t.modified} for t in tracks)
        Track.insert_many(data).execute()
    else:
        fields = [Track.name, Track.number, Track.disk,
                  Track.position, Track.book, Track.file,
                  Track.length, Track.modified]
        data = list((t.name, t.track_number, t.disk, t.position, t.book, t.file, t.length, t.modified) for t in tracks)
        Track.insert_many(data, fields=fields).execute()


def rebase_location(ui, oldPath, newPath):
    """
    This gets called when a user changes the location of the audio book folder.
    Every file in the database updated with the new path.
    Note: This does not check for the existence of those files.
    """
    trackCount = Track.select().count()
    currentTrackCount = 0
    for track in Track.select():
        newFilePath = track.file.replace(oldPath, newPath)
        Track.update(file=newFilePath).where(
            Track.id == track.id).execute()
        StorageBlackList.update(path=newFilePath).where(
            StorageBlackList.path == track.file).execute()
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE,
                             ui.titlebar.update_progress_bar.set_fraction, currentTrackCount / trackCount)
        currentTrackCount = currentTrackCount + 1

    Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.switch_to_playing)


def import_file(file, directory, path, update=False):
    """
    Imports all information about a track into the database.
    Note: This creates also a new album object when it doesnt exist yet.
    Note: This does not check whether the file is already imported.
    :return: True if file was imported, otherwise False
    :return: Track object to be imported when everything passed successfully and track is not in the db already.
    """
    if is_blacklisted(path):
        return True, None

    media_type = tools.__get_media_type(path)
    track = TrackContainer(None, path)
    cover = None
    reader = None
    track_number = None
    track_data = None

    # getting the some data is file specific
    ### MP3 ###
    if "audio/mpeg" in media_type:
        track_data = _get_mp3_tags(track, path)

    ### FLAC ###
    elif "audio/flac" in media_type or "audio/x-flac" in media_type:
        track_data = _get_flac_tags(track, path)

    ### OGG ###
    elif "audio/ogg" in media_type or "audio/x-ogg" in media_type:
        track_data = _get_ogg_tags(track, path)

    ### OPUS ###
    elif "audio/opus" in media_type or "audio/x-opus" in media_type or "codecs=opus" in media_type:
        track_data = _get_opus_tags(track, path)

    ### MP4 ###
    elif "audio/mp4" in media_type or "audio/x-m4a" in media_type:
        track_data = _get_mp4_tags(track, path)

    ### WAV ###
    elif "audio/wav" in media_type or "audio/x-wav" in media_type:
        track_data = TrackData(path)
        track_data.length = __get_wav_track_length(path)

    ### File will not be imported ###
    else:
        log.warning("Skipping file " + path + " because of mime type " + media_type + ".")
        reporter.warning("importer", "skipping file because of mime type: " + media_type)
        return False, None

    track_data.modified = __get_last_modified(path)

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
        success, track_data.length = get_gstreamer_length(path)
        if not success:
            return False, None

    if update:
        if Book.select().where(Book.name == track_data.book_name).count() < 1:
            track_data.book = Book.create(name=track_data.book_name,
                                                          author=track_data.author,
                                                          reader=track_data.reader,
                                                          position=0,
                                                          rating=-1,
                                                          cover=track_data.cover)
        else:
            track_data.book = Book.select().where(
                Book.name == track_data.book_name).get()
            Book.update(name=track_data.book_name,
                                        author=track_data.author,
                                        reader=track_data.reader,
                                        cover=track_data.cover).where(
                Book.id == track_data.book.id).execute()

        Track.update(name=track_data.name,
                                     number=track_data.track_number,
                                     book=track_data.book,
                                     disk=track_data.disk,
                                     length=track_data.length,
                                     modified=track_data.modified).where(
            Track.file == track_data.file).execute()
    else:
        # create database entries
        if Book.select().where(Book.name == track_data.book_name).count() < 1:
            track_data.book = Book.create(name=track_data.book_name,
                                                          author=track_data.author,
                                                          reader=track_data.reader,
                                                          position=0,
                                                          rating=-1,
                                                          cover=track_data.cover)
        else:
            track_data.book = Book.select().where(
                Book.name == track_data.book_name).get()

        return True, track_data

    return True, None


def get_gstreamer_length(path):
    """
    This function determines the length of an audio file using gstreamer.
    This should be used as last resort if mutagen doesn't help us.
    """
    player = Gst.ElementFactory.make("playbin", "player")
    bus = player.get_bus()
    bus.add_signal_watch()
    handler_id = bus.connect("message", cozy.control.player.__on_gst_message)
    player.set_property("uri", "file://" + path)
    player.set_state(Gst.State.PAUSED)
    suc, state, pending = player.get_state(Gst.CLOCK_TIME_NONE)
    limit = 0
    while state != Gst.State.PAUSED and limit < 100:
        suc, state, pending = player.get_state(Gst.CLOCK_TIME_NONE)
        limit += 1
    success, duration = player.query_duration(Gst.Format.TIME)
    player.set_state(Gst.State.NULL)
    bus.disconnect(handler_id)
    bus.remove_signal_watch()
    if success:
        return success, int(duration / 1000000000)
    else:
        success, None


def __get_last_modified(path: str):
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
        shutil.copytree(path, Storage.select().where(
            Storage.default == True).get().path + "/" + name)
    except OSError as exc:
        reporter.exception("importer", exc)
        if exc.errno == errno.ENOTDIR:
            try:
                shutil.copy(path, Storage.select().where(
                    Storage.default == True).get().path)
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
                    " has no mp3 tags. Now guessing from file and folder name…")
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
                    " has no valid tags. Now guessing from file and folder name…")
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
                    " has no valid ogg tags. Trying opus…")
        track_data = _get_opus_tags(track, path)
        return track_data

    track_data.disk = int(__get_common_disk_number(track))
    track_data.length = float(__get_common_track_length(track))
    track_data.cover = __get_ogg_cover(track)
    track_data.author = __get_common_tag(track, "composer")
    track_data.reader = __get_common_tag(track, "artist")
    track_data.book_name = __get_common_tag(track, "album")
    track_data.name = __get_common_tag(track, "title")

    return track_data


def _get_opus_tags(track, path):
    """
    Tries to load embedded tags from given file.
    :return: TrackData object
    """
    track_data = TrackData(path)
    log.debug("Importing ogg " + track.path)
    try:
        track.mutagen = OggOpus(path)
    except Exception as e:
        log.warning("Track " + track.path +
                    " has no valid tags. Now guessing from file and folder name…")
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
                    " has no valid tags. Now guessing from file and folder name…")
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
    try:
        disk = int(track.mutagen["disk"][0])
        return disk
    except:
        pass

    try:
        disk = int(track.mutagen["discnumber"][0])
        return disk
    except:
        pass

    log.debug("Could not find disk number for file " + track.path)

    return 0


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
        base64_string = track.mutagen.get("metadata_block_picture", [])[0]
        decoded = b64tobinary(base64_string)
        pic = Picture(decoded)
        cover = pic.data
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

