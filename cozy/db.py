import os
from peewee import *
from xdg import *

# first we get the data home and find the database if it exists
data_dir = BaseDirectory.xdg_data_home + "/cozy/"
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

db = SqliteDatabase(data_dir + "cozy.db")

class BaseModel(Model):
  """
  The BaseModel is the base class for all db tables.
  """
  class Meta:
    """
    The Meta class encapsulates the db object
    """
    database = db

class Book(BaseModel):
  """
  Book represents an audio book in the database.
  """
  name = CharField()
  author = CharField()
  reader = CharField()
  position = IntegerField()
  rating = IntegerField()
  cover = BlobField(null=True)

class Track(BaseModel):
  """
  Track represents a track from an audio book in the database.
  """
  name = CharField()
  number = IntegerField()
  disk = IntegerField()
  position = IntegerField()
  book = ForeignKeyField(Book)
  file = CharField()
  length = IntegerField()
  modified = IntegerField()

class Settings(BaseModel):
  """
  Settings contains all settings that are not saved in the gschema.
  """
  path = CharField()


db.connect()
# Create tables only when not already present
#                                           |
db.create_tables([Track, Book, Settings], True)

# If there is no user set AudioBooks location, create the default one
if (Settings.select().count() < 1):
  print("Init default audio book location path")
  home_dir = path = os.path.expanduser('~') + "/AudioBooks"
  if not os.path.exists(home_dir):
    os.makedirs(home_dir)

  Settings.create(path = home_dir)

def Books():
  """
  Find all books in the database

  :return: all books
  """
  return Book.select()

def Search(search):
  return Track.select().where(search in Track.name)

def Tracks(book):
  """
  Find all tracks that belong to a given book

  :param book: the book object
  :return: all tracks belonging to the book object
  """
  return Track.select().join(Book).where(Book.name == book.name)

def CleanDB():
  """
  Delete everything from the database except settings.
  """
  pass