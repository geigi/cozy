import logging
import time


from cozy.control.db_updater import update_db
from cozy.db.artwork_cache import ArtworkCache
from cozy.db.book import Book
from cozy.db.collation import collate_natural
from cozy.db.file import File
from cozy.db.model_base import get_sqlite_database
from cozy.db.offline_cache import OfflineCache
from cozy.db.settings import Settings
from cozy.db.storage import Storage
from cozy.db.storage_blacklist import StorageBlackList
from cozy.db.track import Track
from cozy.db.track_to_file import TrackToFile
from cozy.report import reporter

log = logging.getLogger("db")

_db = get_sqlite_database()


def init_db():
    _connect_db(_db)

    sqlite_version = ".".join([str(num) for num in _db.server_version])
    log.info("SQLite version: %s", sqlite_version)

    if Settings.table_exists():
        update_db()
        _db.stop()
        _db.start()
    else:
        _db.create_tables(
            [Track, Book, Settings, ArtworkCache, Storage, StorageBlackList, OfflineCache, TrackToFile, File])
        _db.stop()
        _db.start()

    while not _db.table_exists("settings"):
        time.sleep(0.01)

    _db.bind([Book, Track, Settings, ArtworkCache, StorageBlackList, OfflineCache, Storage, TrackToFile, File],
             bind_refs=False,
             bind_backrefs=False)

    _db.register_collation(collate_natural)

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
        log.error("Could not connect to database: %s", e)


def books():
    """
    Find all books in the database

    :return: all books
    """
    return Book.select()


def get_tracks(book):
    """
    Find all tracks that belong to a given book

    :param book: the book object
    :return: all tracks belonging to the book object
    """
    return Track.select().join(Book).where(Book.id == book.id).order_by(Track.disk, Track.number, Track.name)


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
        track = get_tracks(book)[0] if len(track_items) > 0 else None
    elif query.exists():
        track = query.get()
    else:
        track = None
    return track


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


def get_db():
    global _db
    return _db


def close_db():
    global _db

    log.info("Closing.")
    _db.close()
