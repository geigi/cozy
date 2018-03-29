import os
import logging
import uuid

log = logging.getLogger("db")
from peewee import __version__ as PeeweeVersion
if PeeweeVersion[0] == '2':
    log.info("Using peewee 2 backend")
    from peewee import BaseModel
    ModelBase = BaseModel
else:
    log.info("Using peewee 3 backend")
    from peewee import ModelBase
from peewee import Model, CharField, IntegerField, BlobField, ForeignKeyField, FloatField, BooleanField, SqliteDatabase
from playhouse.migrate import SqliteMigrator, migrate
from gi.repository import GLib, GdkPixbuf, Gdk

import cozy.tools as tools

DB_VERSION = 4

# first we get the data home and find the database if it exists
data_dir = os.path.join(GLib.get_user_data_dir(), "cozy")
log.debug(data_dir)
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

update = None
if os.path.exists(os.path.join(data_dir, "cozy.db")):
    update = True
else:
    update = False

db = SqliteDatabase(os.path.join(data_dir, "cozy.db"), pragmas=[('journal_mode', 'wal')])

class ModelBase(Model):
    """
    The ModelBase is the base class for all db tables.
    """
    class Meta:
        """
        The Meta class encapsulates the db object
        """
        database = db


class Book(ModelBase):
    """
    Book represents an audio book in the database.
    """
    name = CharField()
    author = CharField()
    reader = CharField()
    position = IntegerField()
    rating = IntegerField()
    cover = BlobField(null=True)
    playback_speed = FloatField(default=1.0)
    last_played = IntegerField(default=0)


class Track(ModelBase):
    """
    Track represents a track from an audio book in the database.
    """
    name = CharField()
    number = IntegerField()
    disk = IntegerField()
    position = IntegerField()
    book = ForeignKeyField(Book)
    file = CharField()
    length = FloatField()
    modified = IntegerField()
    crc32 = BooleanField(default=False)


class Settings(ModelBase):
    """
    Settings contains all settings that are not saved in the gschema.
    """
    path = CharField()
    first_start = BooleanField(default=True)
    last_played_book = ForeignKeyField(Book, null=True)
    version = IntegerField(default=DB_VERSION)


class ArtworkCache(ModelBase):
    """
    The artwork cache matches uuids for scaled image files to book objects.
    """
    book = ForeignKeyField(Book)
    uuid = CharField()

class Storage(ModelBase):
    """
    Contains all locations of audiobooks.
    """
    path = CharField()
    location_type = IntegerField(default=0)
    default = BooleanField(default=False)

class StorageBlackList(ModelBase):
    """
    Contains blacklist for directories that will not be included on import scans.
    """
    path = CharField()


def init_db():
    if PeeweeVersion[0] == '3':
        db.bind([Book, Track, Settings, ArtworkCache, StorageBlackList], bind_refs=False, bind_backrefs=False)
    db.connect()

    global update
    if update:
        update_db()
    else:
        if PeeweeVersion[0] == '2':
            db.create_tables([Track, Book, Settings, ArtworkCache, Storage, StorageBlackList], True)
        else:
            db.create_tables([Track, Book, Settings, ArtworkCache, Storage, StorageBlackList])

    if (Settings.select().count() == 0):
        Settings.create(path="", last_played_book=None)


def get_db():
    global db
    return db


def books():
    """
    Find all books in the database

    :return: all books
    """
    with db.atomic():
        return Book.select()


def authors():
    """
    Find all authors in the database

    :return: all authors
    """
    with db.atomic():
        return Book.select(Book.author).distinct().order_by(Book.author)


def readers():
    """
    Find all readers in the database

    :return: all readers
    """
    with db.atomic():
        return Book.select(Book.reader).distinct().order_by(Book.reader)


def Search(search):
    with db.atomic():
        return Track.select().where(search in Track.name)

# Return ordered after Track ID / name when not available


def tracks(book):
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
    if book.position < 1:
        track = tracks(book)[0]
    else:
        track = Track.select().where(Track.id == book.position).get()
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
                                                             | Book.reader.contains(search_string)).distinct().order_by(Book.name)


def search_tracks(search_string):
    """
    Search all tracks in the db with the given substring.
    This ignores upper/lowercase.
    :param search_string: substring to search for
    :return: tracks matching the substring
    """
    return Track.select(Track.name).where(Track.name.contains(search_string)).order_by(Track.name)


def update_db_1():
    """
    Update database to v1.
    """
    migrator = SqliteMigrator(db)

    version = IntegerField(default=1)
    crc32 = BooleanField(default=False)

    migrate(
        migrator.add_column('settings', 'version', version),
        migrator.add_column('track', 'crc32', crc32),
    )


def update_db_2():
    """
    Update database to v2.
    """
    migrator = SqliteMigrator(db)

    playback_speed = FloatField(default=1.0)

    migrate(
        migrator.add_column('book', 'playback_speed', playback_speed),
    )

    Settings.update(version=2).execute()


def update_db_3():
    """
    Update database to v3.
    """
    current_path = Settings.get().path

    db.create_tables([Storage])
    Storage.create(path=current_path, default=True)
    Settings.update(path="NOT_USED").execute()
    Settings.update(version=3).execute()


def update_db_4():
    """
    Update database to v4.
    """
    migrator = SqliteMigrator(db)

    last_played = IntegerField(default=0)

    migrate(
        migrator.add_column('book', 'last_played', last_played),
    )

    Settings.update(version=4).execute()

def update_db_5():
    """
    """
    db.create_tables([StorageBlackList])

    Settings.update(version=5).execute()
    

def update_db():
    """
    Updates the database if not already done.
    """
    global db
    # First test for version 1
    try:
        next(c for c in db.get_columns("settings") if c.name == "version")
    except StopIteration as e:
        update_db_1()

    version = Settings.get().version
    # then for version 2 and so on
    if version < 2:
        update_db_2()

    if version < 3:
        update_db_3()

    if version < 4:
        update_db_4()

    if version < 5:
        update_db_5()


# thanks to oleg-krv
def get_book_duration(book):
    """
    Get the duration of a book in seconds.
    :param book:
    :return: duration of the book
    """
    duration = 0
    for track in tracks(book):
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
    for track in tracks(book):
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
    for track in tracks(book):
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

    for track in tracks(book):
        if elapsed_time + track.length > seconds:
            current_track = track
            current_time = seconds - elapsed_time
            return current_track, current_time
        else:
            elapsed_time += track.length
    
    last_track = tracks(book)[-1]
    return last_track, last_track.length

def remove_invalid_entries(ui=None, refresh=False):
    """
    Remove track entries from db that no longer exist in the filesystem.
    """
    # remove entries from the db that are no longer existent
    for track in Track.select():
        if not os.path.isfile(track.file):
            track.delete_instance()

    clean_books()

    if refresh:
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.refresh_content)

def clean_books():
    """
    Remove all books that have no tracks
    """
    for book in Book.select():
        if Track.select().where(Track.book == book).count() < 1:
            if Settings.get().last_played_book == book.id:
                Settings.update(last_played_book = None).execute()
            book.delete_instance()

def remove_tracks_with_path(ui, path):
    """
    Remove all tracks that contain the given path.
    """
    if path == "":
        return
    
    with db.atomic():
        for track in Track.select():
            if path in track.file:
                track.delete_instance()
    
    clean_books()

    Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.refresh_content)

def blacklist_book(book):
    """
    Removes a book from the library and adds the path(s) to the track list.
    """
    book_tracks = tracks(book)
    data = list((t.file, ) for t in book_tracks)
    StorageBlackList.insert_many(data, fields=[StorageBlackList.path]).execute()
    ids = list(t.id for t in book_tracks)
    with db.atomic():
        Track.delete().where(Track.id << ids).execute()
        book.delete_instance()

def is_blacklisted(path):
    """
    Tests wether a given path is blacklisted.
    """
    if StorageBlackList.select().where(StorageBlackList.path == path).count() > 0:
        return True
    else:
        return False