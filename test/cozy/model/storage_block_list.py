import inject
import pytest
from peewee import SqliteDatabase


@pytest.fixture(autouse=True)
def setup_inject(peewee_database_storage):
    inject.clear_and_configure(lambda binder: binder.bind(SqliteDatabase, peewee_database_storage))
    yield
    inject.clear()


def test_rebase_path():
    from cozy.model.storage_block_list import StorageBlockList
    from cozy.db.storage_blacklist import StorageBlackList

    model = StorageBlockList()

    model.rebase_path("/path/to/replace", "/replaced/path")

    assert StorageBlackList.get_by_id(1).path == "/replaced/path/test1.mp3"
    assert StorageBlackList.get_by_id(2).path == "/path/to/not/replace/test2.mp3"
