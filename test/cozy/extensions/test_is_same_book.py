from cozy.extensions.is_same_book import is_same_book


def test_books_with_identical_spelling_are_same():
    book_a = "Dummy Book Title"
    book_b = "Dummy Book Title"
    result = is_same_book(book_a, book_b)

    assert result is True


def test_books_with_inconsistent_spelling_are_same():
    book_a = "Dummy Book Title"
    book_b = "Dummy book title"
    result = is_same_book(book_a, book_b)

    assert result is True


def test_different_books_are_not_same():
    book_a = "First Dummy Book Title"
    book_b = "Second Dummy Book Title"
    result = is_same_book(book_a, book_b)

    assert result is False


def test_books_without_title_are_not_same():
    book_a = "First Dummy Book Title"
    book_b = ""
    result = is_same_book(book_a, book_b)

    assert result is False
