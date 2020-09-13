from peewee import ForeignKeyField, BooleanField, CharField

from cozy.db.model_base import ModelBase
from cozy.db.track import Track


class OfflineCache(ModelBase):
    track = ForeignKeyField(Track, unique=True)
    copied = BooleanField(default=False)
    file = CharField()
