import re
from typing import Set


def split_strings_to_set(set_to_split: Set[str]):
    finished = set()
    for entry in set_to_split:
        results = re.split(",|;|/|&", entry)
        results = {
            entry.strip()
            for entry in results
        }

        finished.update(results)

    return finished