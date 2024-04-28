from peewee import BooleanField, CharField, ForeignKeyField

from cozy.db.file import File
from cozy.db.model_base import ModelBase


class OfflineCache(ModelBase):
    original_file = ForeignKeyField(File, unique=True)
    copied = BooleanField(default=False)
    cached_file = CharField()
