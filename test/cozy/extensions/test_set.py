from cozy.extensions.set import split_strings_to_set


def test_split_strings_does_nothing_for_non_seperated_element():
    test = "This is a nice test. Nothing should be split."
    result = split_strings_to_set({test})

    assert {test} == result


def test_split_strings_are_splitted():
    test = "This/is&a,test;splitting"
    how_it_should_be = {"This", "is", "a", "test", "splitting"}

    result = split_strings_to_set({test})

    assert how_it_should_be == result


def test_split_strings_are_splitted_and_whitespace_is_removed():
    test = "This  / is & a    ,     test ; splitting    "
    how_it_should_be = {"This", "is", "a", "test", "splitting"}

    result = split_strings_to_set({test})

    assert how_it_should_be == result


def test_split_strings_are_splitted_and_dots_are_not_splitted():
    test = "This Dr. Prof. L. Lala / is & a    ,     test ; splitting    "
    how_it_should_be = {"This Dr. Prof. L. Lala", "is", "a", "test", "splitting"}

    result = split_strings_to_set({test})

    assert how_it_should_be == result
