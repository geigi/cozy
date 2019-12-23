from peewee import CharField

from cozy.model.model_base import ModelBase


class StorageBlackList(ModelBase):
    path = CharField()
