import os
import uuid
import logging
import cozy.tools as tools

from cozy.db import *

log = logging.getLogger("artwork_cache")

def get_cover_pixbuf(book, scale, size=0):
    """
    """
    pixbuf = None
    size *= scale

    if size > 0:
        # first try the cache
        pixbuf = __load_pixbuf_from_cache(book, size)

    if pixbuf:
        return pixbuf
    else:
        # then try the db or file
        pixbuf = __load_cover_pixbuf(book)

    if pixbuf:
        # return original size if it is not greater than 0
        if not size > 0:
            return pixbuf

        # create cached version
        pixbuf = __create_artwork_cache(book, pixbuf, size)
    else:
        pixbuf = None

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

    if tools.get_glib_settings().get_boolean("prefer-external-cover"):
        pixbuf = __load_pixbuf_from_file(book)

        if pixbuf is None:
            pixbuf = __load_pixbuf_from_db(book)
    else:
        pixbuf = __load_pixbuf_from_db(book)

        if pixbuf is None:
            pixbuf = __load_pixbuf_from_file(book)

    return pixbuf

def __load_pixbuf_from_db(book):
    pixbuf = None

    if book and book.cover:
        try:
            loader = GdkPixbuf.PixbufLoader.new()
            loader.write(book.cover)
            loader.close()
            pixbuf = loader.get_pixbuf()
        except Exception as e:
            log.warning("Could not get cover for book " + book.name)
            log.warning(e)
    
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
    cover_files = []

    try:
        cover_files = [f for f in os.listdir(directory)
                       if f.lower().endswith('.png') or f.lower().endswith(".jpg") or f.lower().endswith(".gif")]
    except Exception as e:
        log.warning("Could not open audiobook directory and look for cover files.")
        log.warning(e)
    for elem in (x for x in cover_files if os.path.splitext(x.lower())[0] == "cover"):
        # find cover.[jpg,png,gif]
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(os.path.join(directory, elem))
        except Exception as e:
            log.debug(e)
        if pixbuf:
            break
    if pixbuf is None:
        # find other cover file (sort alphabet)
        cover_files.sort(key=str.lower)
        for elem in cover_files:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(os.path.join(directory, elem))
            except Exception as e:
                log.debug(e)
            if pixbuf:
                break
    return pixbuf
