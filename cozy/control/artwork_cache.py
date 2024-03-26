import os
import uuid
import logging

from gi.repository import Gdk, GdkPixbuf

from cozy.application_settings import ApplicationSettings
from cozy.control.application_directories import get_cache_dir
from cozy.db.artwork_cache import ArtworkCache as ArtworkCacheModel
from cozy.ext import inject
from cozy.media.importer import Importer, ScanStatus
from cozy.report import reporter

log = logging.getLogger("artwork_cache")


class ArtworkCache:
    def __init__(self):
        _importer = inject.instance(Importer)
        _importer.add_listener(self._on_importer_event)
        _app_settings = inject.instance(ApplicationSettings)
        _app_settings.add_listener(self._on_app_setting_changed)

    def get_cover_paintable(self, book, scale, size=0) -> Gdk.Texture | None:
        pixbuf = None
        size *= scale

        if size > 0:
            # First try the cache
            pixbuf = self._load_pixbuf_from_cache(book, size)

        if not pixbuf:
            # Then try the db or file
            pixbuf = self._load_cover_pixbuf(book)

            if not pixbuf:
                return None
            elif size > 0:
                # Resize and cache artwork if size is greater than 0
                pixbuf = self._create_artwork_cache(book, pixbuf, size)

        return Gdk.Texture.new_for_pixbuf(pixbuf)

    def delete_artwork_cache(self):
        """
        Deletes the artwork cache completely.
        """
        cache_dir = os.path.join(get_cache_dir(), "artwork")

        import shutil
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)

        q = ArtworkCacheModel.delete()
        q.execute()

    def _on_importer_event(self, event, data):
        if event == "scan":
            if data == ScanStatus.STARTED:
                self.delete_artwork_cache()

    def _create_artwork_cache(self, book, pixbuf, size):
        """
        Creates a resized cache version of the given pixbuf and saves it
        in the cozy cache folder under a unique identifier.
        :param book: Book which the artwork is from
        :param pixbuf: Pixbuf to be cached
        :param size: Size for the cached version
        :return: Resized pixbuf
        """
        query = ArtworkCacheModel.select().where(ArtworkCacheModel.book == book.id)
        gen_uuid = ""

        if query.exists():
            gen_uuid = str(query.first().uuid)
        else:
            gen_uuid = str(uuid.uuid4())
            ArtworkCacheModel.create(book=book.id, uuid=gen_uuid)

        cache_dir = os.path.join(os.path.join(get_cache_dir(), "artwork"), gen_uuid)
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

        resized_pixbuf = self._resize_pixbuf(pixbuf, size)
        file_path = os.path.join(cache_dir, str(size) + ".jpg")
        if not os.path.exists(file_path):
            try:
                resized_pixbuf.savev(file_path, "jpeg", ["quality", None], ["95"])
            except Exception as e:
                reporter.warning("artwork_cache", "Failed to save resized cache albumart")
                log.warning("Failed to save resized cache albumart for uuid %r: %s", gen_uuid, e)

        return resized_pixbuf

    def get_album_art_path(self, book, size):
        query = ArtworkCacheModel.select().where(ArtworkCacheModel.book == book.id)
        if query.exists():
            try:
                uuid = query.first().uuid
            except Exception:
                reporter.error("artwork_cache", "load_pixbuf_from_cache: query exists but query.first().uuid crashed.")
                return None
        else:
            return None

        cache_dir = os.path.join(get_cache_dir(), "artwork")
        cache_dir = os.path.join(cache_dir, uuid)

        try:
            if os.path.exists(cache_dir):
                file_path = os.path.join(cache_dir, str(size) + ".jpg")
                if os.path.exists(file_path):
                    return file_path
                else:
                    return None
        except Exception as e:
            log.warning(e)
            return None

        return None

    def _load_pixbuf_from_cache(self, book, size):
        path = self.get_album_art_path(book, size)

        try:
            if path:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
            else:
                pixbuf = None
        except Exception as e:
            log.warning("Failed to load pixbuf from path: %s. Deleting file.", path)
            log.debug(e)
            os.remove(path)
            return None

        return pixbuf

    @inject.autoparams()
    def _load_cover_pixbuf(self, book, app_settings: ApplicationSettings):
        """
        Load the cover from a given book and create a pixbuf object with a given from it.
        :param book: The book object
        :param size: The size of the bigger side in pixels
        :return: pixbuf object containing the cover
        """
        pixbuf = None

        if app_settings.prefer_external_cover:
            pixbuf = self._load_pixbuf_from_file(book)

            if pixbuf is None:
                pixbuf = self._load_pixbuf_from_db(book)
        else:
            pixbuf = self._load_pixbuf_from_db(book)

            if pixbuf is None:
                pixbuf = self._load_pixbuf_from_file(book)

        return pixbuf

    def _load_pixbuf_from_db(self, book):
        pixbuf = None

        if book and book.cover:
            try:
                loader = GdkPixbuf.PixbufLoader.new()
                loader.write(book.cover)
                loader.close()
                pixbuf = loader.get_pixbuf()
            except Exception as e:
                reporter.warning("artwork_cache", "Could not get book cover from db.")
                log.warning("Could not get cover for book %r: %s", book.name, e)

        return pixbuf

    def _resize_pixbuf(self, pixbuf, size):
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

    def _load_pixbuf_from_file(self, book):
        """
        Try to load the artwork from a book from image files.
        :param book: The book to load the artwork from.
        :return: Artwork as pixbuf object.
        """
        pixbuf = None
        cover_files = []

        try:
            directory = os.path.dirname(os.path.normpath(book.chapters[0].file))

            cover_files = [f for f in os.listdir(directory)
                           if f.lower().endswith('.png') or f.lower().endswith(".jpg") or f.lower().endswith(".gif")]
        except Exception as e:
            log.warning("Could not open audiobook directory and look for cover files: %s", e)
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

    def _on_app_setting_changed(self, event: str, data):
        if event == "prefer-external-cover":
            self.delete_artwork_cache()

