from peewee import ForeignKeyField, BooleanField, CharField

from cozy.db.model_base import ModelBase
from cozy.db.file import File


class OfflineCache(ModelBase):
    original_file = ForeignKeyField(File, unique=True)
    copied = BooleanField(default=False)
    cached_file = CharField()
