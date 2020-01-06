from cozy.model.glib_settings import get_glib_settings
from cozy.model.model_base import ModelBase
from peewee import CharField, IntegerField, BlobField, FloatField, BooleanField


class Book(ModelBase):
    name = CharField()
    author = CharField()
    reader = CharField()
    position = IntegerField()
    rating = IntegerField()
    cover = BlobField(null=True)
    playback_speed = FloatField(default=1.0)
    last_played = IntegerField(default=0)
    offline = BooleanField(default=False)
    downloaded = BooleanField(default=False)

    def is_currently_available(self):
        if not get_glib_settings().get_boolean("hide-offline"):
            return True

        from cozy.control.filesystem_monitor import FilesystemMonitor
        if not FilesystemMonitor().is_book_online(self):
            return Book.get(Book.id == self.get_id()).downloaded
        else:
            return True

    def get_author(self):
        if not get_glib_settings().get_boolean("swap-author-reader"):
            return self.get(Book.id == self.id).author
        else:
            return self.get(Book.id == self.get_id()).reader

    def get_reader(self):
        if not get_glib_settings().get_boolean("swap-author-reader"):
            return self.get(Book.id == self.get_id()).reader
        else:
            return self.get(Book.id == self.get_id()).author
