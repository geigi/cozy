from peewee import ForeignKeyField, BooleanField, CharField

from cozy.model.model_base import ModelBase
from cozy.model.track import Track


class OfflineCache(ModelBase):
    track = ForeignKeyField(Track, unique=True)
    copied = BooleanField(default=False)
    file = CharField()
