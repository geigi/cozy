import logging
import os

from peewee import Model
from playhouse.apsw_ext import APSWDatabase

from cozy.control.application_directories import get_data_dir

log = logging.getLogger("db")

_db = None


def get_sqlite_database():
    global _db
    return _db


def database_file_exists():
    return os.path.exists(os.path.join(get_data_dir(), "cozy.db"))


def __open_database():
    global _db
    if not os.path.exists(get_data_dir()):
        os.makedirs(get_data_dir())
    _db = APSWDatabase(os.path.join(get_data_dir(), "cozy.db"), timeout=5, pragmas=[('journal_mode', 'wal')])


__open_database()


class ModelBase(Model):
    class Meta:
        database = _db
