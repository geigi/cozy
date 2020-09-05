import pytest


def test_path_returns_correct_value(peewee_database_storage):
    from cozy.model.storage import Storage

    storage = Storage(peewee_database_storage, 1)
    assert storage.path == "/media/test"


def test_setting_path_updates_in_track_object_and_database(peewee_database_storage):
    from cozy.db.storage import Storage as StorageModel
    from cozy.model.storage import Storage

    new_path = "/tmp/media2"

    storage = Storage(peewee_database_storage, 1)
    storage.path = new_path
    assert storage.path == new_path
    assert StorageModel.get_by_id(1).path == new_path


def test_setting_invalid_path_raises_exception(peewee_database_storage):
    from cozy.model.storage import Storage, InvalidPath

    invalid_path = "not an absolute path"
    storage = Storage(peewee_database_storage, 1)

    with pytest.raises(InvalidPath):
        storage.path = invalid_path


def test_location_type_returns_correct_default_value(peewee_database_storage):
    from cozy.model.storage import Storage

    storage = Storage(peewee_database_storage, 1)
    assert storage.location_type == 0


def test_setting_location_type_updates_in_track_object_and_database(peewee_database_storage):
    from cozy.db.storage import Storage as StorageModel
    from cozy.model.storage import Storage

    new_location_type = 555

    storage = Storage(peewee_database_storage, 1)
    storage.location_type = new_location_type
    assert storage.location_type == new_location_type
    assert StorageModel.get_by_id(1).location_type == new_location_type


def test_default_returns_correct_default_value(peewee_database_storage):
    from cozy.model.storage import Storage

    storage = Storage(peewee_database_storage, 1)
    assert storage.default == False


def test_setting_default_updates_in_track_object_and_database(peewee_database_storage):
    from cozy.db.storage import Storage as StorageModel
    from cozy.model.storage import Storage

    new_default = True

    storage = Storage(peewee_database_storage, 1)
    storage.default = new_default
    assert storage.default == new_default
    assert StorageModel.get_by_id(1).default == new_default


def test_external_returns_correct_default_value(peewee_database_storage):
    from cozy.model.storage import Storage

    storage = Storage(peewee_database_storage, 1)
    assert storage.external == False


def test_setting_external_updates_in_track_object_and_database(peewee_database_storage):
    from cozy.db.storage import Storage as StorageModel
    from cozy.model.storage import Storage

    new_external = True

    storage = Storage(peewee_database_storage, 1)
    storage.external = new_external
    assert storage.external == new_external
    assert StorageModel.get_by_id(1).external == new_external
