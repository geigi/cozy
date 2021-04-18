def test_db_created(peewee_database):
    from cozy.db.track import Track

    assert Track.table_exists()


def test_name_returns_correct_value(peewee_database):
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    assert track.name == "Test Track"


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
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    spy = mocker.spy(track, "emit_event")
    track.delete()

    assert TrackModel.select().where(TrackModel.id == 1).count() < 1
    spy.assert_called_once_with("chapter-deleted", track)
    assert len(track._listeners) < 1
