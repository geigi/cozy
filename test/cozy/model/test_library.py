def test_library_contains_books(peewee_database):
    from cozy.model.library import Library

    library = Library(peewee_database)

    assert len(library.books) > 0
