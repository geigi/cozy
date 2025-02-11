from collections import namedtuple
from typing import List

import pytest


class M4BChapter:
    title: str
    start: float

    def __init__(self, title: str, start: float):
        self.title = title
        self.start = start


class M4B:
    chapters: List[M4BChapter]

    def __init__(self, chapters: List[M4BChapter]):
        self.chapters = chapters


@pytest.fixture(scope="function")
def discoverer_mocks(mocker):
    mock_info = mocker.patch("gi.repository.GstPbutils.DiscovererInfo", )
    mock_tags = mocker.patch("gi.repository.Gst.TagList", autospec=True)

    mock_tags = mock_info.get_tags.return_value

    return namedtuple("discoverer_mocks", "info tags")(mock_info, mock_tags)


def get_true_and_numbered_string(_, number):
    return True, "string {}".format(str(number))


def test_multiple_authors_returned_as_separated_list(discoverer_mocks):
    from cozy.media.tag_reader import TagReader

    discoverer_mocks.tags.get_string_index.side_effect = get_true_and_numbered_string
    discoverer_mocks.tags.get_tag_size.return_value = 2

    tag_reader = TagReader("uri", discoverer_mocks.info)
    assert tag_reader._get_author() == "string 0; string 1"


def test_multiple_readers_returned_as_separated_list(discoverer_mocks):
    from cozy.media.tag_reader import TagReader

    discoverer_mocks.tags.get_string_index.side_effect = get_true_and_numbered_string
    discoverer_mocks.tags.get_tag_size.return_value = 2

    tag_reader = TagReader("uri", discoverer_mocks.info)
    assert tag_reader._get_reader() == "string 0; string 1"


def test_track_name_fallback_is_filename(discoverer_mocks):
    from cozy.media.tag_reader import TagReader

    tag_reader = TagReader("file://abc/def/a nice file.mp3", discoverer_mocks.info)

    assert tag_reader._get_track_name_fallback() == "a nice file"


def test_track_name_fallback_is_unescaped_filename(discoverer_mocks):
    from cozy.media.tag_reader import TagReader

    tag_reader = TagReader("file://abc/def/a%20nice%20file.mp3", discoverer_mocks.info)

    assert tag_reader._get_track_name_fallback() == "a nice file"


def test_book_title_fallback_is_parent_directory_name(discoverer_mocks):
    from cozy.media.tag_reader import TagReader

    tag_reader = TagReader("file://abc/def hij/a nice file.mp3", discoverer_mocks.info)

    assert tag_reader._get_book_name_fallback() == "def hij"


def test_book_title_fallback_is_unescaped_parent_directory_name(discoverer_mocks):
    from cozy.media.tag_reader import TagReader

    tag_reader = TagReader("file://abc/def%20hij/a%20nice%20file.mp3", discoverer_mocks.info)

    assert tag_reader._get_book_name_fallback() == "def hij"


def test_default_track_number(discoverer_mocks):
    from cozy.media.tag_reader import TagReader

    discoverer_mocks.tags.get_uint_index.return_value = False, 999

    tag_reader = TagReader("uri", discoverer_mocks.info)

    assert tag_reader._get_track_number() == 0


def test_default_disk_number(discoverer_mocks):
    from cozy.media.tag_reader import TagReader

    discoverer_mocks.tags.get_uint_index.return_value = False, 999

    tag_reader = TagReader("uri", discoverer_mocks.info)

    assert tag_reader._get_disk() == 1


def test_author_reader_fallback(mocker, discoverer_mocks):
    from cozy.media.tag_reader import TagReader

    discoverer_mocks.tags.get_string_index.return_value = False, []

    tag_reader = TagReader("uri", discoverer_mocks.info)

    assert tag_reader._get_author() == "Unknown"
    assert tag_reader._get_reader() == "Unknown"


def test_get_m4b_chapters(mocker, discoverer_mocks):
    discoverer_mocks.info.get_duration = lambda: 10 * (10 ** 9)

    from cozy.media.tag_reader import TagReader

    tag_reader = TagReader("file://abc/def/01 a nice file.m4b", discoverer_mocks.info)
    chapters = tag_reader._get_mp4_chapters(M4B([M4BChapter("test", 0), M4BChapter("testa", 1)]))

    assert len(chapters) == 2
    assert chapters[0].name == "test"
    assert chapters[0].position == 0
    assert chapters[0].length == 1
    assert chapters[0].number == 1
    assert chapters[1].name == "testa"
    assert chapters[1].position == 1 * (10 ** 9)
    assert chapters[1].length == 9
    assert chapters[1].number == 2


def test_get_m4b_chapters_creates_single_chapter_if_none_present(mocker, discoverer_mocks):
    discoverer_mocks.info.get_duration = lambda: 10 * (10 ** 9)
    discoverer_mocks.tags.get_string_index.return_value = True, "a nice file"
    discoverer_mocks.tags.get_uint_index.return_value = True, 1

    from cozy.media.tag_reader import TagReader

    tag_reader = TagReader("file://abc/def/01 a nice file.m4b", discoverer_mocks.info)
    chapters = tag_reader._get_mp4_chapters(M4B([]))

    assert len(chapters) == 1
    assert chapters[0].name == "a nice file"
    assert chapters[0].position == 0
    assert chapters[0].length == 10
    assert chapters[0].number == 1
