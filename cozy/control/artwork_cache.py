import logging
import os
import shutil
from pathlib import Path
from uuid import uuid4
import io
from PIL import Image

import inject
from gi.repository import Gdk, GLib

from cozy.control.application_directories import get_artwork_cache_dir
from cozy.db.artwork_cache import ArtworkCache as ArtworkCacheModel
from cozy.media.importer import Importer, ScanStatus
from cozy.report import reporter
from cozy.settings import ApplicationSettings

log = logging.getLogger("artwork_cache")


class ArtworkCache:
    _importer = inject.attr(Importer)
    _app_settings = inject.attr(ApplicationSettings)

    def __init__(self):
        self._importer.add_listener(self._on_importer_event)
        self._app_settings.add_listener(self._on_app_setting_changed)

    def get_cover_paintable(self, book, scale, size) -> Gdk.Texture | None:
        texture = None
        size *= scale

        # First try the cache
        texture = self._load_texture_from_cache(book, size)

        if not texture:
            image = self._load_cover_image(book)

            if image:
                self._cache_cover(book, image, size)
                texture = self._load_texture_from_cache(book, size)

        return texture

    def delete_artwork_cache(self):
        shutil.rmtree(get_artwork_cache_dir(), ignore_errors=True)
        ArtworkCacheModel.delete().execute()

    def get_album_art_path(self, book, size) -> str:
        query = ArtworkCacheModel.select().where(ArtworkCacheModel.book == book.id)
        if not query.exists():
            return None

        try:
            uuid = query.first().uuid
        except Exception:
            reporter.error(
                "artwork_cache",
                "load_texture_from_cache: query exists but query.first().uuid crashed.",
            )
            return None
        
        cache_dir = get_artwork_cache_dir() / uuid
        cache_dir.mkdir(exist_ok=True, parents=True)
        file_path = (cache_dir / str(size)).with_suffix(".png")
    
        if file_path.exists():
            return str(file_path)

        return None

    def _cache_cover(self, book, image, size):
        query = ArtworkCacheModel.select().where(ArtworkCacheModel.book == book.id)

        if query.exists():
            uuid = str(query.first().uuid)
        else:
            uuid = str(uuid4())
            ArtworkCacheModel.create(book=book.id, uuid=uuid)

        resized = image.resize((size, size), Image.LANCZOS)
        
        cache_dir = get_artwork_cache_dir() / uuid
        cache_dir.mkdir(exist_ok=True, parents=True)
        file_path = (cache_dir / str(size)).with_suffix(".png")
        
        if not file_path.exists():
            try:
                resized.save(str(file_path), format="PNG")
            except Exception as e:
                reporter.warning("artwork_cache", "Failed to save resized cache albumart")
                log.warning("Failed to save resized cache albumart for uuid %r: %s", uuid, e)

    def _load_texture_from_cache(self, book, size):
        path = self.get_album_art_path(book, size)

        try:
            texture = Gdk.Texture.new_from_filename(path) if path else None
        except Exception as e:
            log.warning("Failed to load texture from path: %s. Deleting file.", path)
            log.debug(e)
            os.remove(path)
            return None

        return texture

    def _load_cover_image(self, book):
        loading_order = [self._load_texture_from_db, self._load_texture_from_file]

        if self._app_settings.prefer_external_cover:
            loading_order.reverse()

        for loader in loading_order:
            texture = loader(book)
            if texture:
                return texture

        return None

    def _load_texture_from_db(self, book):
        if not book or not book.cover:
            return None

        try:
            texture = Image.open(io.BytesIO(book.cover))
        except Exception as e:
            reporter.warning("artwork_cache", "Could not get book cover from db.")
            log.warning("Could not get cover for book %r: %s", book.name, e)
        else:
            return texture

    def _load_texture_from_file(self, book) -> Gdk.Texture | None:
        directory = Path(book.chapters[0].file).absolute().parent
        cover_extensions = {".jpg", ".jpeg", ".png", ".gif"}

        for path in directory.glob("cover.*"):
            if path.suffix.lower() not in cover_extensions:
                continue

            try:
                texture = Image.open(str(path))
            except Exception as e:
                log.debug(e)

            if texture:
                return texture

        return None

    def _on_importer_event(self, event, data):
        if event == "scan" and data == ScanStatus.STARTED:
            self.delete_artwork_cache()

    def _on_app_setting_changed(self, event: str, data):
        if event == "prefer-external-cover":
            self.delete_artwork_cache()
