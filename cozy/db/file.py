from peewee import CharField

from cozy.db.model_base import ModelBase


class File(ModelBase):
    path = CharField()
