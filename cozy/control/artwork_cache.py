import logging
import os
import shutil
from pathlib import Path
from uuid import uuid4

import inject
from gi.repository import Gdk, GdkPixbuf

from cozy.control.application_directories import get_artwork_cache_dir
from cozy.db.artwork_cache import ArtworkCache as ArtworkCacheModel
from cozy.media.importer import Importer, ScanStatus
from cozy.report import reporter
from cozy.settings import ApplicationSettings

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
        shutil.rmtree(get_artwork_cache_dir(), ignore_errors=True)
        ArtworkCacheModel.delete().execute()

    def _on_importer_event(self, event, data):
        if event == "scan" and data == ScanStatus.STARTED:
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

        if query.exists():
            uuid = str(query.first().uuid)
        else:
            uuid = str(uuid4())
            ArtworkCacheModel.create(book=book.id, uuid=uuid)

        cache_dir = get_artwork_cache_dir() / uuid
        cache_dir.mkdir(exist_ok=True, parents=True)
        file_path = (cache_dir / str(size)).with_suffix(".jpg")

        resized_pixbuf = self._resize_pixbuf(pixbuf, size)

        if not file_path.exists():
            try:
                resized_pixbuf.savev(str(file_path), "jpeg", ["quality", None], ["95"])
            except Exception as e:
                reporter.warning("artwork_cache", "Failed to save resized cache albumart")
                log.warning("Failed to save resized cache albumart for uuid %r: %s", uuid, e)

        return resized_pixbuf

    def get_album_art_path(self, book, size) -> str:
        query = ArtworkCacheModel.select().where(ArtworkCacheModel.book == book.id)
        if not query.exists():
            return None

        try:
            uuid = query.first().uuid
        except Exception:
            reporter.error(
                "artwork_cache",
                "load_pixbuf_from_cache: query exists but query.first().uuid crashed.",
            )
            return None

        cache_dir = get_artwork_cache_dir() / uuid

        if cache_dir.is_dir():
            file_path = (cache_dir / str(size)).with_suffix(".jpg")
            if file_path.exists():
                return str(file_path)

        return None

    def _load_pixbuf_from_cache(self, book, size):
        path = self.get_album_art_path(book, size)

        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path) if path else None
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
        loading_order = [self._load_pixbuf_from_db, self._load_pixbuf_from_file]

        if app_settings.prefer_external_cover:
            loading_order.reverse()

        for loader in loading_order:
            pixbuf = loader(book)
            if pixbuf:
                return pixbuf

        return None

    def _load_pixbuf_from_db(self, book):
        if not book or not book.cover:
            return None

        try:
            loader = GdkPixbuf.PixbufLoader.new()
            loader.write(book.cover)
            loader.close()
        except Exception as e:
            reporter.warning("artwork_cache", "Could not get book cover from db.")
            log.warning("Could not get cover for book %r: %s", book.name, e)
        else:
            return loader.get_pixbuf()

    def _resize_pixbuf(self, pixbuf, size):
        """
        Resizes an pixbuf and keeps the aspect ratio.
        :return: Resized pixbuf.
        """
        if size == 0:
            return pixbuf

        if pixbuf.get_height() > pixbuf.get_width():
            width = int(pixbuf.get_width() / (pixbuf.get_height() / size))
            return pixbuf.scale_simple(width, size, GdkPixbuf.InterpType.BILINEAR)
        else:
            height = int(pixbuf.get_height() / (pixbuf.get_width() / size))
            return pixbuf.scale_simple(size, height, GdkPixbuf.InterpType.BILINEAR)

    def _load_pixbuf_from_file(self, book) -> GdkPixbuf.Pixbuf | None:
        """
        Try to load the artwork from a book from image files.
        :param book: The book to load the artwork from.
        :return: Artwork as pixbuf object.
        """

        directory = Path(book.chapters[0].file).absolute().parent
        cover_extensions = {".jpg", ".jpeg", ".png", ".gif"}

        for path in directory.glob("cover.*"):
            if path.suffix.lower() not in cover_extensions:
                continue

            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(path))
            except Exception as e:
                log.debug(e)

            if pixbuf:
                return pixbuf

        return None

    def _on_app_setting_changed(self, event: str, data):
        if event == "prefer-external-cover":
            self.delete_artwork_cache()
