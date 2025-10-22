import logging

from peewee import Model
from playhouse.sqliteq import SqliteQueueDatabase

from cozy.control.application_directories import get_data_dir

log = logging.getLogger(__name__)

_db = None


def get_sqlite_database():
    global _db
    return _db


def database_file_exists():
    return (get_data_dir() / "cozy.db").is_file()


def __open_database():
    global _db

    _db = SqliteQueueDatabase(str(get_data_dir() / "cozy.db"), queue_max_size=128, results_timeout=15.0,
                              timeout=15.0, pragmas=[('cache_size', -1024 * 32), ('journal_mode', 'wal')])


__open_database()


class ModelBase(Model):
    class Meta:
        database = _db
