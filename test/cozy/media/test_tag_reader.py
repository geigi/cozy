from collections import namedtuple

import pytest


@pytest.fixture(scope="function")
def discoverer_mocks(mocker):
    mock_info = mocker.patch("gi.repository.GstPbutils.DiscovererInfo", autospec=True)
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


def test_book_title_fallback_is_parent_directory_name(discoverer_mocks):
    from cozy.media.tag_reader import TagReader

    tag_reader = TagReader("file://abc/def hij/a nice file.mp3", discoverer_mocks.info)

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
