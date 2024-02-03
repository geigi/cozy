import re


def split_strings_to_set(set_to_split: set[str]) -> set[str]:
    return {entry.strip() for item in set_to_split for entry in re.split(",|;|/|&", item)}
