from peewee import BooleanField, CharField, IntegerField

from cozy.db.model_base import ModelBase


class Storage(ModelBase):
    path = CharField()
    location_type = IntegerField(default=0)
    default = BooleanField(default=False)
    external = BooleanField(default=False)
