def test_db_created(peewee_database):
    from cozy.db.track import Track

    with peewee_database:
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
    from cozy.db.track import Track as TrackModel
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    track.file = "altered.mp3"
    assert track.file == "altered.mp3"
    assert TrackModel.get_by_id(1).file == "altered.mp3"


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


def test_modified_returns_default_value(peewee_database):
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    assert track.modified == 123456


def test_setting_modified_updates_in_track_object_and_database(peewee_database):
    from cozy.db.track import Track as TrackModel
    from cozy.model.track import Track

    track = Track(peewee_database, 1)
    track.modified = 42
    assert track.modified == 42
    assert TrackModel.get_by_id(1).modified == 42
