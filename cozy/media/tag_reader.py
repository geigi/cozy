import os
from urllib.parse import unquote, urlparse

import mutagen
from gi.repository import GLib, Gst, GstPbutils
from mutagen.mp4 import MP4

from cozy.media.chapter import Chapter
from cozy.media.media_file import MediaFile

NS_TO_SEC = 10 ** 9


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
            chapters=self._get_chapters(),
            cover=self._get_cover(),
            modified=self._get_modified()
        )

        return media_file

    def _get_book_name(self):
        success, value = self.tags.get_string_index(Gst.TAG_ALBUM, 0)

        return value.strip() if success else self._get_book_name_fallback()

    def _get_book_name_fallback(self):
        path = os.path.normpath(self.uri)
        directory_path = os.path.dirname(path)
        directory = os.path.basename(directory_path)
        return unquote(directory)

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
        filename_without_extension = os.path.splitext(filename)[0]
        return unquote(filename_without_extension)

    def _get_chapters(self):
        if self.uri.lower().endswith("m4b") and self._mutagen_supports_chapters():
            mutagen_tags = self._parse_with_mutagen()
            return self._get_m4b_chapters(mutagen_tags)
        else:
            return self._get_single_chapter()

    def _get_single_chapter(self):
        chapter = Chapter(
            name=self._get_track_name(),
            position=0,
            length=self._get_length_in_seconds(),
            number=self._get_track_number()
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

    def _get_m4b_chapters(self, mutagen_tags: MP4) -> list[Chapter]:
        chapters = []

        if not mutagen_tags.chapters or len(mutagen_tags.chapters) == 0:
            return self._get_single_chapter()

        for index, chapter in enumerate(mutagen_tags.chapters):
            if index < len(mutagen_tags.chapters) - 1:
                length = mutagen_tags.chapters[index + 1].start - chapter.start
            else:
                length = self._get_length_in_seconds() - chapter.start

            title = chapter.title or ""

            chapters.append(Chapter(
                name=title,
                position=int(chapter.start * NS_TO_SEC),
                length=length,
                number=index + 1
            ))

        return chapters

    def _parse_with_mutagen(self) -> MP4:
        path = unquote(urlparse(self.uri).path)
        mutagen_mp4 = MP4(path)

        return mutagen_mp4

    @staticmethod
    def _mutagen_supports_chapters() -> bool:
        if mutagen.version[0] > 1:
            return True

        if mutagen.version[0] == 1 and mutagen.version[1] >= 45:
            return True

        return False
