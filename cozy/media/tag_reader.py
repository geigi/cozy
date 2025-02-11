import os
from urllib.parse import unquote, urlparse

from gi.repository import GLib, Gst, GstPbutils
from mutagen import File
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4

from cozy.media.chapter import Chapter
from cozy.media.media_file import MediaFile


class TagReader:
    def __init__(self, uri: str, discoverer_info: GstPbutils.DiscovererInfo):
        if not uri:
            raise ValueError("URI must not be None or empty")

        if not discoverer_info:
            raise ValueError("discoverer_info must not be None")

        self.uri: str = uri
        self.discoverer_info = discoverer_info

        self.tags: Gst.TagList = discoverer_info.get_tags()
        self.tag_format = self.tags.get_string_index("container-format", 0)[1].lower()

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
            modified=self._get_modified(),
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
        authors = (
            self._get_string_list(Gst.TAG_ARTIST)
            if self.tag_format == "ogg"
            else self._get_string_list(Gst.TAG_COMPOSER)
        )

        if authors and authors[0]:
            return "; ".join(authors)
        else:
            return _("Unknown")

    def _get_reader(self):
        readers = (
            self._get_string_list(Gst.TAG_PERFORMER)
            if self.tag_format == "ogg"
            else self._get_string_list(Gst.TAG_ARTIST)
        )

        if readers and readers[0]:
            return "; ".join(readers)
        else:
            return _("Unknown")

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
        path = unquote(urlparse(self.uri).path)
        mutagen_file = File(path)

        if isinstance(mutagen_file, MP4):
            return self._get_mp4_chapters(mutagen_file)
        elif isinstance(mutagen_file, MP3):
            return self._get_mp3_chapters(mutagen_file)
        elif self.tag_format == "ogg":
            return self._get_ogg_chapters()
        else:
            return self._get_single_file_chapter()

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
            success, value = self.tags.get_string_index(tag, i)
            if success:
                values.append(value.strip())

        return values

    def _get_single_file_chapter(self):
        chapter = Chapter(
            name=self._get_track_name(),
            position=0,
            length=self._get_length_in_seconds(),
            number=self._get_track_number(),
        )
        return [chapter]

    def _get_mp4_chapters(self, file: MP4) -> list[Chapter]:
        if not file.chapters or len(file.chapters) == 0:
            return self._get_single_file_chapter()

        chapters = []

        for index, chapter in enumerate(file.chapters):
            if index < len(file.chapters) - 1:
                length = file.chapters[index + 1].start - chapter.start
            else:
                length = self._get_length_in_seconds() - chapter.start

            chapters.append(
                Chapter(
                    name=chapter.title or "",
                    position=int(chapter.start * Gst.SECOND),
                    length=length,
                    number=index + 1,
                )
            )

        return chapters

    def _get_mp3_chapters(self, file: MP3) -> list[Chapter]:
        chaps = file.tags.getall("CHAP")
        if not chaps:
            return self._get_single_file_chapter()

        chapters = []
        chaps.sort(key=lambda k: k.element_id)

        for index, chapter in enumerate(chaps):
            if index < len(chaps) - 1:
                length = chapter.end_time - chapter.start_time
            else:
                length = self._get_length_in_seconds() - chapter.start_time

            sub_frames = chapter.sub_frames.get("TIT2", ())
            title = sub_frames.text[0] if sub_frames else ""

            chapters.append(
                Chapter(
                    name=title,
                    position=int(chapter.start_time * Gst.SECOND),
                    length=length,
                    number=index + 1,
                )
            )

        return chapters

    def _get_ogg_chapters(self) -> list[Chapter]:
        comment_list: list[str] = self._get_string_list("extended-comment")
        chapter_dict: dict[int, Chapter] = {}
        chapter_list: list[Chapter] = []

        for comment in comment_list:
            if not comment.lower().startswith("chapter"):
                continue

            try:
                tag, value = comment.split("=", 1)
            except ValueError:
                continue

            if len(tag) not in (10, 14) or not tag[7:10].isdecimal():
                continue  # Tag should be in the form CHAPTER + 3 numbers + NAME (for chapter names only)

            try:
                chapter_num = int(tag[7:10], 10) + 1  # get chapter number from 3 chars
            except ValueError:
                continue

            if chapter_num not in chapter_dict:
                chapter_dict[chapter_num] = Chapter(None, None, None, chapter_num)

            if tag.lower().endswith("name"):
                chapter_dict[chapter_num].name = value
            elif len(tag) == 10:
                chapter_dict[chapter_num].position = self._vorbis_timestamp_to_secs(value)

        if not chapter_dict:
            return self._get_single_file_chapter()

        prev_chapter = None
        for _, chapter in sorted(chapter_dict.items()):
            if not chapter.is_valid():
                return self._get_single_file_chapter()

            if prev_chapter:
                prev_chapter.length = chapter.position - prev_chapter.position

            chapter_list.append(chapter)
            prev_chapter = chapter

        prev_chapter.length = self._get_length_in_seconds() - prev_chapter.position

        return chapter_list

    @staticmethod
    def _vorbis_timestamp_to_secs(timestamp: str) -> float | None:
        parts = timestamp.split(":", 2)

        try:
            return int(parts[0], 10) * 3600 + int(parts[1], 10) * 60 + float(parts[2])
        except ValueError:
            return None
