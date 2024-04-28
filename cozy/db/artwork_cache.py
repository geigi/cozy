from peewee import CharField, ForeignKeyField

from cozy.db.book import Book
from cozy.db.model_base import ModelBase


class ArtworkCache(ModelBase):
    book = ForeignKeyField(Book)
    uuid = CharField()
