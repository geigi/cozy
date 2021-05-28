from peewee import CharField, IntegerField

from cozy.db.model_base import ModelBase


class File(ModelBase):
    path = CharField(unique=True)
    modified = IntegerField()
