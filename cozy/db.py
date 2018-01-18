import os
import logging
import uuid
from peewee import BaseModel, Model, CharField, IntegerField, BlobField, ForeignKeyField, FloatField, BooleanField, SqliteDatabase
from playhouse.migrate import SqliteMigrator, migrate
from gi.repository import GLib, GdkPixbuf

import cozy.tools as tools

# first we get the data home and find the database if it exists
data_dir = os.path.join(GLib.get_user_data_dir(), "cozy")
log = logging.getLogger("db")
log.debug(data_dir)
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

db = SqliteDatabase(os.path.join(data_dir, "cozy.db"))


class BaseModel(Model):
    """
    The BaseModel is the base class for all db tables.
    """
    class Meta:
        """
        The Meta class encapsulates the db object
        """
        database = db


class Book(BaseModel):
    """
    Book represents an audio book in the database.
    """
    name = CharField()
    author = CharField()
    reader = CharField()
    position = IntegerField()
    rating = IntegerField()
    cover = BlobField(null=True)


class Track(BaseModel):
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


class Settings(BaseModel):
    """
    Settings contains all settings that are not saved in the gschema.
    """
    path = CharField()
    first_start = BooleanField(default=True)
    last_played_book = ForeignKeyField(Book, null=True)
    version = IntegerField(default=1)


class ArtworkCache(BaseModel):
    """
    The artwork cache matches uuids for scaled image files to book objects.
    """
    book = ForeignKeyField(Book)
    uuid = CharField()


def init_db():
    db.connect()
    # Create tables only when not already present
    #                                           |
    db.create_tables([Track, Book, Settings, ArtworkCache], True)
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


def seconds_to_str(seconds):
    """
    Converts seconds to a string with the following apperance:
    hh:mm:ss

    :param seconds: The seconds as float
    """
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)

    if (h > 0):
        result = "%d:%02d:%02d" % (h, m, s)
    elif (m > 0):
        result = "%02d:%02d" % (m, s)
    else:
        result = "00:%02d" % (s)

    return result


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


def get_time_book(book):
    """
    Get times for book
    :param book:
    :return: duration, time read, time read in current file
    """
    duration = 0
    read = 0
    read_add = True
    current_track = 0
    if book.position == 0:
        read_add = False
    for track in tracks(book):
        duration += track.length
        if track.id == book.position:
            read_add = False
            current_track = track.position / 1000000000
        if read_add:
            read += track.length
    return duration, read, current_track
