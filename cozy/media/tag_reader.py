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
        _, self.tag_format = self.tags.get_string_index("container-format", 0).lower()

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
        chapter_dict: dict[int, list[float | str | None]] = {}
        for comment in comment_list:
            comment_split = comment.split("=", 1)
            if len(comment_split) != 2:  # Is a tag set in this comment
                continue
            if (
                len(comment_split[0]) not in (10, 14)
                or comment_split[0][:7].lower() != "chapter"
                or not comment_split[0][7:10].isdecimal()
            ):
                continue  # Is the tag in the form chapter + 3 numbers + maybe name
            try:
                chapter_num = int(comment_split[0][7:10], 10)  # get number from 3 chars
            except ValueError:
                continue
            if chapter_num not in chapter_dict:
                chapter_dict[chapter_num] = [None, None]
            if len(comment_split[0]) == 14 and comment_split[0][10:14].lower() == "name":
                chapter_dict[chapter_num][1] = comment_split[1]
            elif len(comment_split[0]) == 10:
                chapter_dict[chapter_num][0] = self._vorbis_timestamp_to_secs(comment_split[1])
        if 0 not in chapter_dict or chapter_dict[0][0] is None or chapter_dict[0][1] is None:
            return self._get_single_chapter()
        i = 1
        chapter_list: list[Chapter] = []
        while (
            i in chapter_dict and chapter_dict[i][0] is not None and chapter_dict[i][1] is not None
        ):
            chapter_list.append(
                Chapter(
                    name=chapter_dict[i - 1][1],
                    position=int(chapter_dict[i - 1][0] * NS_TO_SEC),
                    length=chapter_dict[i][0] - chapter_dict[i - 1][0],
                    number=i,
                )
            )
            i += 1
        chapter_list.append(
            Chapter(
                name=chapter_dict[i - 1][1],
                position=int(chapter_dict[i - 1][0] * NS_TO_SEC),
                length=self._get_length_in_seconds() - chapter_dict[i - 1][0],
                number=i,
            )
        )
        return chapter_list

    @staticmethod
    def _vorbis_timestamp_to_secs(timestamp: str) -> float | None:
        elems = timestamp.split(":")
        if len(elems) != 3:
            return None
        try:
            return int(elems[0], 10) * 3600 + int(elems[1], 10) * 60 + float(elems[2])
        except ValueError:
            return None
