import pytest


def test_db_created(peewee_database):
    from cozy.db.track import Track

    assert Track.table_exists()


def test_name_returns_correct_value(peewee_database):
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    assert track.name == "Test Track"


def test_name_returns_generated_name_when_no_name_is_present(peewee_database):
    from cozy.model.track import Track

    track = Track(peewee_database, 234)

    assert track.name == "Chapter {}".format(track.number)


def test_setting_name_updates_in_track_object_and_database(peewee_database):
    from cozy.db.track import Track as TrackModel
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    track.name = "Altered"
    assert track.name == "Altered"
    assert TrackModel.get_by_id(1).name == "Altered"


def test_number_returns_correct_value(peewee_database):
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    assert track.number == 1


def test_setting_number_updates_in_track_object_and_database(peewee_database):
    from cozy.db.track import Track as TrackModel
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    track.number = 2
    assert track.number == 2
    assert TrackModel.get_by_id(1).number == 2


def test_disk_returns_correct_value(peewee_database):
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    assert track.disk == 1


def test_setting_disk_updates_in_track_object_and_database(peewee_database):
    from cozy.db.track import Track as TrackModel
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    track.disk = 2
    assert track.disk == 2
    assert TrackModel.get_by_id(1).disk == 2


def test_position_returns_default_value(peewee_database):
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    assert track.position == 0


def test_setting_position_updates_in_track_object_and_database(peewee_database):
    from cozy.db.track import Track as TrackModel
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    track.position = 42
    assert track.position == 42
    assert TrackModel.get_by_id(1).position == 42


def test_file_returns_default_value(peewee_database):
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    assert track.file == "test.mp3"


def test_setting_file_updates_in_track_object_and_database(peewee_database):
    from cozy.db.track_to_file import TrackToFile
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    track.file = "altered.mp3"
    file = TrackToFile.get(TrackToFile.track == track.id).file
    assert track.file == "altered.mp3"
    assert file.path == "altered.mp3"


def test_setting_file_gets_file_object_if_it_is_already_present_in_database(peewee_database):
    from cozy.db.track_to_file import TrackToFile
    from cozy.db.file import File
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    track.file = "file with multiple chapters.m4b"
    file = TrackToFile.get(TrackToFile.track == track.id).file

    assert track.file == "file with multiple chapters.m4b"
    assert file.path == "file with multiple chapters.m4b"
    assert File.select().where(File.id == 0).count() == 0


def test_setting_file_gets_file_object_if_it_is_already_present_in_database_but_preserves_old_file_if_still_used(
        peewee_database):
    from cozy.db.track_to_file import TrackToFile
    from cozy.db.file import File
    from cozy.model.track import Track

    track = Track(peewee_database, 230)
    track.file = "Changed path"
    file = TrackToFile.get(TrackToFile.track == track.id).file

    assert track.file == "Changed path"
    assert file.path == "Changed path"
    assert File.select().where(File.id == 229).count() == 1


def test_length_returns_default_value(peewee_database):
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    assert track.length == 42.1


def test_setting_length_updates_in_track_object_and_database(peewee_database):
    from cozy.db.track import Track as TrackModel
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    track.length = 42.42
    assert track.length == 42.42
    assert TrackModel.get_by_id(1).length == 42.42


def test_setting_modified_updates_in_track_object_and_database(peewee_database):
    from cozy.model.track import Track
    from cozy.db.track_to_file import TrackToFile

    track = Track(peewee_database, 1)
    track.modified = 42
    track_to_file = TrackToFile.select().where(TrackToFile.track == track._db_object.id).get()

    assert track.modified == 42
    assert track_to_file.file.modified == 42


def test_delete_deletes_track_from_db(peewee_database, mocker):
    from cozy.db.track import Track as TrackModel
    from cozy.db.track_to_file import TrackToFile
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    spy = mocker.spy(track, "emit_event")
    track.delete()

    assert TrackModel.select().where(TrackModel.id == 1).count() < 1
    assert TrackToFile.select().join(TrackModel).where(TrackToFile.track.id == 1).count() < 1
    spy.assert_called_once_with("chapter-deleted", track)
    assert len(track._listeners) < 1


def test_delete_does_not_delete_book(peewee_database):
    from cozy.db.track import Track as TrackModel
    from cozy.db.book import Book
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    book_id = TrackModel.get(1).book.id
    track.delete()

    assert Book.get_or_none(book_id) is not None


def test_track_to_file_not_present_throws_exception_and_deletes_track_instance(peewee_database):
    from cozy.db.track_to_file import TrackToFile
    from cozy.db.track import Track as TrackDB
    from cozy.model.track import Track, TrackInconsistentData

    TrackToFile.select().join(TrackDB).where(TrackToFile.track.id == 1).get().delete_instance()
    with pytest.raises(TrackInconsistentData):
        Track(peewee_database, 1)

    assert not TrackDB.get_or_none(1)


def test_delete_removes_file_object_if_not_used_elsewhere(peewee_database):
    from cozy.db.file import File
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    file_id = track.file_id
    track.delete()

    assert not File.get_or_none(file_id)


def test_delete_keeps_file_object_if_used_elsewhere(peewee_database):
    from cozy.db.file import File
    from cozy.model.track import Track

    track = Track(peewee_database, 230)
    file_id = track.file_id
    track.delete()

    assert File.get_or_none(file_id)
