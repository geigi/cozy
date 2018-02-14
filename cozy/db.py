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
from gi.repository import GLib, GdkPixbuf

import cozy.tools as tools

# first we get the data home and find the database if it exists
data_dir = os.path.join(GLib.get_user_data_dir(), "cozy")
log.debug(data_dir)
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

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
    version = IntegerField(default=1)


class ArtworkCache(ModelBase):
    """
    The artwork cache matches uuids for scaled image files to book objects.
    """
    book = ForeignKeyField(Book)
    uuid = CharField()


def init_db():
    db.connect()
    # Create tables only when not already present
    #                                           |
    if PeeweeVersion[0] == '2':
        db.create_tables([Track, Book, Settings, ArtworkCache], True)
    else:
        db.create_tables([Track, Book, Settings, ArtworkCache])
    update_db()

    if (Settings.select().count() == 0):
        Settings.create(path="", last_played_book=None)


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


def update_db():
    """
    Updates the database if not already done.
    """
    try:
        next(c for c in db.get_columns("settings") if c.name == "version")
    except StopIteration as e:
        update_db_1()
        

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
                remaining += int(track.position / 1000000000)
        
    return remaining
