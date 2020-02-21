from peewee import ForeignKeyField, CharField

from cozy.model.book import Book
from cozy.model.model_base import ModelBase


class ArtworkCache(ModelBase):
    book = ForeignKeyField(Book)
    uuid = CharField()
