import logging
import os
import time

from cozy.control.db_updater import update_db
from cozy.db.artwork_cache import ArtworkCache
from cozy.db.book import Book
from cozy.db.model_base import get_sqlite_database, get_data_dir
from cozy.db.offline_cache import OfflineCache
from cozy.db.settings import Settings
from cozy.db.storage import Storage
from cozy.db.storage_blacklist import StorageBlackList
from cozy.db.track import Track
from cozy.report import reporter

log = logging.getLogger("db")
from peewee import __version__ as PeeweeVersion

if PeeweeVersion[0] == '2':
    log.info("Using peewee 2 backend")
    from peewee import BaseModel

    ModelBase = BaseModel
else:
    log.info("Using peewee 3 backend")
from peewee import SqliteDatabase
from gi.repository import GLib, Gdk

_db = get_sqlite_database()


def init_db():
    tmp_db = None

    _connect_db(_db)

    if Settings.table_exists():
        update_db()
    else:
        tmp_db = SqliteDatabase(os.path.join(get_data_dir(), "cozy.db"))
        if PeeweeVersion[0] == '2':
            tmp_db.create_tables([Track, Book, Settings, ArtworkCache, Storage, StorageBlackList, OfflineCache], True)
        else:
            with tmp_db.connection_context():
                tmp_db.create_tables([Track, Book, Settings, ArtworkCache, Storage, StorageBlackList, OfflineCache])

    # this is necessary to ensure that the tables have indeed been created
    if tmp_db:
        if PeeweeVersion[0] == '2':
            while not Settings.table_exists():
                time.sleep(0.01)
        else:
            while not tmp_db.table_exists("settings"):
                time.sleep(0.01)

    _connect_db(_db)

    if PeeweeVersion[0] == '3':
        _db.bind([Book, Track, Settings, ArtworkCache, StorageBlackList, OfflineCache, Storage], bind_refs=False,
                 bind_backrefs=False)

    if (Settings.select().count() == 0):
        Settings.create(path="", last_played_book=None)

    # TODO: Properly handle errors within the database
    # Remove this later. It prevents empty book objects in the database
    clean_books()

def _connect_db(db):
    try:
        db.connect(reuse_if_open=True)
    except Exception as e:
        reporter.exception("db", e)
        log.error("Could not connect to database. ")
        log.error(e)


def books():
    """
    Find all books in the database

    :return: all books
    """
    return Book.select()


def authors():
    """
    Find all authors in the database

    :return: all authors
    """
    return Book.select(Book.author).distinct().order_by(Book.author)


def readers():
    """
    Find all readers in the database

    :return: all readers
    """
    return Book.select(Book.reader).distinct().order_by(Book.reader)


def Search(search):
    return Track.select().where(search in Track.name)


# Return ordered after Track ID / name when not available


def get_tracks(book):
    """
    Find all tracks that belong to a given book

    :param book: the book object
    :return: all tracks belonging to the book object
    """
    return Track.select().join(Book).where(Book.id == book.id).order_by(Track.disk, Track.number, Track.name)


def clean_db():
    """
    Delete everything from the database except settings.
    """
    q = Track.delete()
    q.execute()
    q = Book.delete()
    q.execute()
    q = ArtworkCache.delete()
    q.execute()


def get_track_for_playback(book):
    """
    Finds the current track to playback for a given book.
    :param book: book which the next track is required from
    :return: current track position from book db
    """
    book = Book.select().where(Book.id == book.id).get()
    query = Track.select().where(Track.id == book.position)
    if book.position < 1:
        track_items = get_tracks(book)
        if len(track_items) > 0:
            track = get_tracks(book)[0]
        else:
            track = None
    elif query.exists():
        track = query.get()
    else:
        track = None
    return track


def search_authors(search_string):
    """
    Search all authors in the db with the given substring.
    This ignores upper/lowercase and returns each author only once.
    :param search_string: substring to search for
    :return: authors matching the substring
    """
    return Book.select(Book.author).where(Book.author.contains(search_string)).distinct().order_by(Book.author)


def search_readers(search_string):
    """
    Search all readers in the db with the given substring.
    This ignores upper/lowercase and returns each reader only once.
    :param search_string: substring to search for
    :return: readers matching the substring
    """
    return Book.select(Book.reader).where(Book.reader.contains(search_string)).distinct().order_by(Book.reader)


def search_books(search_string):
    """
    Search all book names in the db with the given substring.
    This ignores upper/lowercase and returns each book name only once.
    :param search_string: substring to search for
    :return: book names matching the substring
    """
    return Book.select(Book.name, Book.cover, Book.id).where(Book.name.contains(search_string)
                                                             | Book.author.contains(search_string)
                                                             | Book.reader.contains(search_string)).distinct().order_by(
        Book.name)


def search_tracks(search_string):
    """
    Search all tracks in the db with the given substring.
    This ignores upper/lowercase.
    :param search_string: substring to search for
    :return: tracks matching the substring
    """
    return Track.select(Track.name).where(Track.name.contains(search_string)).order_by(Track.name)


def get_track_path(track):
    """
    Returns the path to the file of a given track.
    This returns the original path if online and otherwise a cached offline
    version if available.
    :param track: DB track object
    :return: Path as string
    """
    pass


# thanks to oleg-krv
def get_book_duration(book):
    """
    Get the duration of a book in seconds.
    :param book:
    :return: duration of the book
    """
    duration = 0
    for track in get_tracks(book):
        duration += track.length

    return duration


def get_book_progress(book, include_current=True):
    """
    Get the progress of a book in seconds.
    :param book:
    :param include_current: Include the progress of the current track
    :return: current progress of the book
    """
    progress = 0
    if book.position == 0:
        return 0
    for track in get_tracks(book):
        if track.id == book.position:
            if include_current:
                progress += int(track.position / 1000000000)
            return progress

        progress += track.length

    return progress


def get_book_remaining(book, include_current=True):
    """
    Get the remaining time of a book in seconds.
    :param book:
    :param include_current: Include the progress of the current track
    :return: remaining time for the book
    """
    remaining = 0
    passed_current = False
    if book.position == 0:
        return get_book_duration(book)
    for track in get_tracks(book):
        if passed_current:
            remaining += track.length

        if track.id == book.position:
            passed_current = True
            if include_current:
                cur_remaining = track.length - (track.position / 1000000000)
                if cur_remaining > 0:
                    remaining += int(cur_remaining)

    return remaining


def get_track_from_book_time(book, seconds):
    """
    Return the track and the according time for a given book and it's time.
    This is used when the user has the whole book position slider enabled
    and is scrubbing.
    Note: the seconds must be at 1.0 speed
    :param book: 
    :param seconds: seconds as float
    :return: Track to play
    :return: According time
    """
    elapsed_time = 0.0
    current_track = None
    current_time = 0.0
    last_track = None

    for track in get_tracks(book):
        last_track = track
        if elapsed_time + track.length > seconds:
            current_track = track
            current_time = seconds - elapsed_time
            return current_track, current_time
        else:
            elapsed_time += track.length

    return last_track, last_track.length


def get_external_storage_locations():
    """
    Returns a list of all external storage locations.
    """
    directories = Storage.select().where(Storage.external == True)

    return directories


def remove_invalid_entries(ui=None, refresh=False):
    """
    Remove track entries from db that no longer exist in the filesystem.
    """
    # remove entries from the db that are no longer existent
    for track in Track.select():
        from cozy.control.filesystem_monitor import FilesystemMonitor
        if not os.path.isfile(track.file) and FilesystemMonitor().is_track_online(
                track):
            track.delete_instance()

    clean_books()

    if refresh:
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.refresh_content)


def clean_books():
    """
    Remove all books that have no tracks
    """
    for book in Book.select():
        if not get_track_for_playback(book):
            Book.update(position=0).where(Book.id == book.id).execute()
        if Track.select().where(Track.book == book).count() < 1:
            if Settings.get().last_played_book and Settings.get().last_played_book.id == book.id:
                Settings.update(last_played_book=None).execute()
            book.delete_instance()


def remove_tracks_with_path(ui, path):
    """
    Remove all tracks that contain the given path.
    """
    if path == "":
        return

    for track in Track.select():
        if path in track.file:
            track.delete_instance()

    clean_books()

    Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.refresh_content)


def blacklist_book(book):
    """
    Removes a book from the library and adds the path(s) to the track list.
    """
    book_tracks = get_tracks(book)
    data = list((t.file,) for t in book_tracks)
    chunks = [data[x:x + 500] for x in range(0, len(data), 500)]
    for chunk in chunks:
        StorageBlackList.insert_many(chunk, fields=[StorageBlackList.path]).execute()
    ids = list(t.id for t in book_tracks)
    Track.delete().where(Track.id << ids).execute()
    book.delete_instance()


def is_blacklisted(path):
    """
    Tests whether a given path is blacklisted.
    """
    if StorageBlackList.select().where(StorageBlackList.path == path).count() > 0:
        return True
    else:
        return False


def is_external(book):
    """
    Tests whether the given book is saved on external storage.
    """
    return any(storage.path in Track.select().join(Book).where(Book.id == book.id).first().file for storage in
               Storage.select().where(Storage.external == True))


def close_db():
    global _db

    log.info("Closing.")
    _db.close()
