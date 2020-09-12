import os
from urllib.parse import unquote, urlparse

import gi

gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import GstPbutils, Gst, GLib

from cozy.media.chapter import Chapter
from cozy.media.media_file import MediaFile


class TagReader:
    def __init__(self, uri: str, discoverer_info: GstPbutils.DiscovererInfo):
        if not uri:
            raise ValueError("URI must not be None or emtpy")

        if not discoverer_info:
            raise ValueError("discoverer_info must not be None")

        self.uri: str = uri
        self.discoverer_info: GstPbutils.DiscovererInfo = discoverer_info

        self.tags: Gst.TagList = discoverer_info.get_tags()

        if not self.tags:
            raise ValueError("Failed to retrieve tags from discoverer_info")

    def get_tags(self) -> MediaFile:
        media_file = MediaFile(
            path=unquote(urlparse(self.uri).path),
            book_name=self._get_book_name(),
            author=self._get_author(),
            reader=self._get_reader(),
            disk=self._get_disk(),
            track_number=self._get_track_number(),
            chapters=self._get_chapters(),
            cover=self._get_cover(),
            length=self._get_length_in_seconds(),
            modified=self._get_modified()
        )

        return media_file

    def _get_book_name(self):
        success, value = self.tags.get_string_index(Gst.TAG_ALBUM, 0)

        return value.strip() if success else self._get_book_name_fallback()

    def _get_book_name_fallback(self):
        path = os.path.normpath(self.uri)
        directory_path = os.path.dirname(path)
        return os.path.basename(directory_path)

    def _get_author(self):
        authors = self._get_string_list(Gst.TAG_COMPOSER)

        if len(authors) > 0 and authors[0]:
            return "; ".join(authors)
        else:
            return "Unknown"

    def _get_reader(self):
        readers = self._get_string_list(Gst.TAG_ARTIST)

        if len(readers) > 0 and readers[0]:
            return "; ".join(readers)
        else:
            return "Unknown"

    def _get_disk(self):
        success, value = self.tags.get_uint_index(Gst.TAG_ALBUM_VOLUME_NUMBER, 0)

        return value if success else 1

    def _get_track_number(self):
        success, value = self.tags.get_uint_index(Gst.TAG_TRACK_NUMBER, 0)

        return value if success else 0

    def _get_track_name(self):
        success, value = self.tags.get_string_index(Gst.TAG_TITLE, 0)

        return value.strip() if success else self._get_track_name_fallback()

    def _get_track_name_fallback(self):
        filename = os.path.basename(self.uri)
        return os.path.splitext(filename)[0]

    def _get_chapters(self):
        chapter = Chapter(
            name=self._get_track_name(),
            position=0
        )

        return [chapter]

    def _get_cover(self):
        success, sample = self.tags.get_sample_index(Gst.TAG_IMAGE, 0)

        if not success:
            success, sample = self.tags.get_sample_index(Gst.TAG_PREVIEW_IMAGE, 0)
        if not success:
            return None

        success, mapflags = sample.get_buffer().map(Gst.MapFlags.READ)
        if not success:
            return None

        cover_bytes = GLib.Bytes(mapflags.data).get_data()
        return cover_bytes

    def _get_length_in_seconds(self):
        return self.discoverer_info.get_duration() / Gst.SECOND

    def _get_modified(self):
        path = unquote(urlparse(self.uri).path)
        return int(os.path.getmtime(path))

    def _get_string_list(self, tag: str):
        success, value = self.tags.get_string_index(tag, 0)

        values = []
        for i in range(self.tags.get_tag_size(tag)):
            (success, value) = self.tags.get_string_index(tag, i)
            if success:
                values.append(value.strip())

        return values
