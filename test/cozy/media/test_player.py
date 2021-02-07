from unittest.mock import MagicMock, call

import pytest
from peewee import SqliteDatabase

from cozy.application_settings import ApplicationSettings
from cozy.ext import inject
from cozy.media.gst_player import GstPlayer
from cozy.model.library import Library
from cozy.model.settings import Settings


@pytest.fixture(autouse=True)
def setup_inject(peewee_database):
    inject.clear_and_configure(lambda binder: binder
                               .bind(SqliteDatabase, peewee_database)
                               .bind_to_constructor("FilesystemMonitor", MagicMock())
                               .bind_to_constructor(GstPlayer, MagicMock())
                               .bind_to_constructor(ApplicationSettings, MagicMock())
                               .bind_to_constructor(Library, lambda: Library())
                               .bind_to_constructor(Settings, lambda: Settings()))

    yield
    inject.clear()


def test_initializing_player_loads_last_book(mocker):
    from cozy.media.player import Player

    mocker.patch("cozy.media.player.Player._rewind_in_book")
    library = inject.instance(Library)
    library.last_played_book = library.books[0]

    player = Player()

    assert player._book == library.last_played_book


def test_loading_new_book_loads_chapter_and_book(mocker):
    from cozy.media.player import Player

    mocker.patch("cozy.media.player.Player._rewind_in_book")
    library = inject.instance(Library)
    player = Player()

    book = library.books[0]
    player._load_book(book)

    assert player._book == book
    assert player._book.current_chapter == book.current_chapter


def test_loading_new_book_emits_changed_event(mocker):
    from cozy.media.player import Player

    mocker.patch("cozy.media.player.Player._rewind_in_book")
    library = inject.instance(Library)
    player = Player()
    spy = mocker.spy(player, "emit_event")

    book = library.books[2]
    player._load_book(book)

    spy.assert_has_calls(calls=[call("chapter-changed", book)])


def test_loading_new_chapter_loads_chapter(mocker):
    from cozy.media.player import Player

    mocker.patch("cozy.media.player.Player._rewind_in_book")
    library = inject.instance(Library)
    player = Player()

    book = library.books[0]
    player._load_chapter(book.current_chapter)

    assert player._book.current_chapter == book.current_chapter


def test_loading_new_chapter_emits_changed_event(mocker):
    from cozy.media.player import Player

    mocker.patch("cozy.media.player.Player._rewind_in_book")
    library = inject.instance(Library)
    player = Player()
    spy = mocker.spy(player, "emit_event")

    book = library.books[1]
    player._book = book
    player._load_chapter(book.chapters[1])

    spy.assert_has_calls(calls=[call('chapter-changed', book)])
