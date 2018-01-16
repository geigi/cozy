import os
import logging
import uuid
from peewee import BaseModel, Model, CharField, IntegerField, BlobField, ForeignKeyField, FloatField, BooleanField, SqliteDatabase
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


class Settings(BaseModel):
    """
    Settings contains all settings that are not saved in the gschema.
    """
    path = CharField()
    first_start = BooleanField(default=True)
    last_played_book = ForeignKeyField(Book, null=True)


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


def get_cover_pixbuf(book, size=0):
    """
    """
    pixbuf = None

    if size > 0:
        # first try the cache
        pixbuf = __load_pixbuf_from_cache(book, size)

    if pixbuf is not None:
        return pixbuf
    else:
        # then try the db or file
        pixbuf = __load_cover_pixbuf(book)

    if pixbuf is not None:
        # return original size if it is not greater than 0
        if not size > 0:
            return pixbuf

        # create cached version
        pixbuf = __create_artwork_cache(book, pixbuf, size)
    else:
        pixbuf = __load_placeholder(size)

    return pixbuf


def delete_artwork_cache():
    """
    Deletes the artwork cache completely.
    """
    cache_dir = tools.get_cache_dir()
    import shutil
    shutil.rmtree(cache_dir)

    q = ArtworkCache.delete()
    q.execute()


def generate_artwork_cache():
    """
    Generates the default artwork cache for cover preview.
    """
    for book in Book.select():
        get_cover_pixbuf(book, 180)


def __load_artwork_placeholder(size):
    """
    Loads the artwork placeholder first from cache and then from file.
    Creates cached versions if it doesn't exist already at the given size.
    :param size: Size in px for the placeholder
    :return: Placeholder pixbuf at given size
    """
    pixbuf = None

    file_path = os.path.join(tools.get_cache_dir(), "placeholder_" + str(size) + ".jpg")
    if os.path.exists(file_path):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(file_path)
    else:
        pixbuf = GdkPixbuf.Pixbuf.new_from_resource("/de/geigi/cozy/blank_album.png")
        pixbuf = __resize_pixbuf(pixbuf, size)
        resized_pixbuf.save(file_path, "jpeg")
    
    return pixbuf


def __create_artwork_cache(book, pixbuf, size):
    """
    Creates a resized cache version of the given pixbuf and saves it 
    in the cozy cache folder under a unique identifier. 
    :param book: Book which the artwork is from
    :param pixbuf: Pixbuf to be cached
    :param size: Size for the cached version
    :return: Resized pixbuf
    """
    query = ArtworkCache.select().where(ArtworkCache.book == book.id)
    gen_uuid = ""

    if query.exists():
        gen_uuid = str(query.first().uuid)
    else:
        gen_uuid = str(uuid.uuid4())
        ArtworkCache.create(book = book, uuid=gen_uuid)

    cache_dir = os.path.join(tools.get_cache_dir(), gen_uuid)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    resized_pixbuf = __resize_pixbuf(pixbuf, size)
    file_path = os.path.join(cache_dir, str(size) + ".jpg")
    if not os.path.exists(file_path):
        try:
            resized_pixbuf.savev(file_path, "jpeg", "", "")
        except Exception as e:
            log.warning("Failed to save resized cache albumart for following uuid: " + gen_uuid)
            log.warning(e)

    return resized_pixbuf


def __load_pixbuf_from_cache(book, size):
    """
    """
    pixbuf = None

    query = ArtworkCache.select().where(ArtworkCache.book == book.id)
    if query.exists():
        uuid = query.first().uuid
    else:
        return None

    cache_dir = tools.get_cache_dir()
    cache_dir = os.path.join(cache_dir, uuid)

    try:
        if os.path.exists(cache_dir):
            file_path = os.path.join(cache_dir, str(size) + ".jpg")
            if os.path.exists(file_path):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(os.path.join(cache_dir, str(size) + ".jpg"))
            else:
                return None
    except Exception as e:
        log.warning(e)
        return None

    return pixbuf


def __load_cover_pixbuf(book):
    """
    Load the cover from a given book and create a pixbuf object with a given from it.
    :param book: The book object
    :param size: The size of the bigger side in pixels
    :return: pixbuf object containing the cover
    """
    pixbuf = None

    # first try to load pixbuf from db
    if book is not None and book.cover is not None:
        try:
            loader = GdkPixbuf.PixbufLoader.new()
            loader.write(book.cover)
            loader.close()
            pixbuf = loader.get_pixbuf()
        except Exception as e:
            log.warning("Could not get cover for book " + book.name)
            log.warning(e)
    
    # then try from file
    if pixbuf is None:
        pixbuf = __load_pixbuf_from_file(book, pixbuf)

    return pixbuf


def __resize_pixbuf(pixbuf, size):
    """
    Resizes an pixbuf and keeps the aspect ratio.
    :return: Resized pixbuf.
    """
    resized_pixbuf = pixbuf

    if size > 0:
        if pixbuf.get_height() > pixbuf.get_width():
            width = int(pixbuf.get_width() / (pixbuf.get_height() / size))
            resized_pixbuf = pixbuf.scale_simple(
                width, size, GdkPixbuf.InterpType.BILINEAR)
        else:
            height = int(pixbuf.get_height() / (pixbuf.get_width() / size))
            resized_pixbuf = pixbuf.scale_simple(
                size, height, GdkPixbuf.InterpType.BILINEAR)

    return resized_pixbuf

def __load_pixbuf_from_file(book):
    """
    Try to load the artwork from a book from image files.
    :param book: The book to load the artwork from.
    :return: Artwork as pixbuf object.
    """
    pixbuf = None

    directory = os.path.dirname(os.path.normpath(tracks(book)[0].file))
    cover_files = [f for f in os.listdir(directory)
                   if f.lower().endswith('.png') or f.lower().endswith(".jpg") or f.lower().endswith(".gif")]
    for elem in (x for x in cover_files if os.path.splitext(x.lower())[0] == "cover"):
        # find cover.[jpg,png,gif]
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(os.path.join(directory, elem))
        except Exception as e:
            log.debug(e)
        if pixbuf is not None:
            break
    if pixbuf is None:
        # find other cover file (sort alphabet)
        cover_files.sort(key=str.lower)
        for elem in cover_files:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(os.path.join(directory, elem))
            except Exception as e:
                log.debug(e)
            if pixbuf is not None:
                break
    return pixbuf


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
