def test_db_created(peewee_database):
    from cozy.db.book import Book

    with peewee_database:
        assert Book.table_exists()


def test_name_returns_correct_value(peewee_database):
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    assert book.name == "Test Book"


def test_setting_name_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookModel
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    book.name = "Altered"
    assert book.name == "Altered"
    assert BookModel.get_by_id(1).name == "Altered"


def test_author_returns_correct_value(peewee_database):
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    assert book.author == "Test Author"


def test_setting_author_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookModel
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    book.author = "Altered"
    assert book.author == "Altered"
    assert BookModel.get_by_id(1).author == "Altered"


def test_reader_returns_correct_value(peewee_database):
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    assert book.reader == "Test Reader"


def test_setting_reader_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookModel
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    book.reader = "Altered"
    assert book.reader == "Altered"
    assert BookModel.get_by_id(1).reader == "Altered"


def test_position_returns_default_value(peewee_database):
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    assert book.position == 0


def test_setting_position_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookModel
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    book.position = 42
    assert book.position == 42
    assert BookModel.get_by_id(1).position == 42


def test_rating_returns_default_value(peewee_database):
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    assert book.rating == 0


def test_setting_rating_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookModel
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    book.rating = 5
    assert book.rating == 5
    assert BookModel.get_by_id(1).rating == 5


def test_cover_returns_default_value(peewee_database):
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    assert book.cover == None


def test_setting_cover_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookModel
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    book.cover = b"42"
    assert book.cover == b"42"
    assert BookModel.get_by_id(1).cover == b"42"


def test_playback_speed_returns_default_value(peewee_database):
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    assert book.playback_speed == 1.0


def test_setting_playback_speed_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookModel
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    book.playback_speed = 1.2
    assert book.playback_speed == 1.2
    assert BookModel.get_by_id(1).playback_speed == 1.2


def test_last_played_returns_default_value(peewee_database):
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    assert book.last_played == 0


def test_setting_last_played_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookModel
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    book.last_played = 42
    assert book.last_played == 42
    assert BookModel.get_by_id(1).last_played == 42


def test_offline_returns_default_value(peewee_database):
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    assert book.offline == False


def test_setting_offline_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookModel
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    book.offline = True
    assert book.offline is True
    assert BookModel.get_by_id(1).offline is True


def test_downloaded_returns_default_value(peewee_database):
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    assert book.downloaded == False


def test_setting_downloaded_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookModel
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    book.downloaded = True
    assert book.downloaded is True
    assert BookModel.get_by_id(1).downloaded is True


def test_chapters_return_correct_count_of_chapters(peewee_database):
    from cozy.model.book import Book

    book = Book(peewee_database, 1)
    assert len(book.chapters) == 1


def test_tracks_are_ordered_by_disk_number_name(peewee_database):
    from cozy.model.book import Book

    book = Book(peewee_database, 9)

    chapters_manually_sorted = book.chapters.copy()
    chapters_manually_sorted.sort(key=lambda chapter: (chapter.disk, chapter.number, chapter.name))

    assert all([a == b for a, b in zip(book.chapters, chapters_manually_sorted)])


def test_current_track_is_actually_current_track(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookModel

    book = Book(peewee_database, 9)

    assert book.current_chapter.id == BookModel.get_by_id(9).position
