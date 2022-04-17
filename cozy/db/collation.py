import re


def collate_natural(s1, s2):
    if s1 == s2:
        return 0

    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    list = sorted([s1, s2], key=alphanum_key)

    if list.index(s1) == 0:
        return -1
    else:
        return 1
