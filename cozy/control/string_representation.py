def seconds_to_str(seconds, max_length=None, include_seconds=True):
    """
    Converts seconds to a string with the following appearance:
    hh:mm:ss

    :param seconds: The seconds as float
    """
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)

    if max_length:
        max_m, max_s = divmod(max_length, 60)
        max_h, max_m = divmod(max_m, 60)
    else:
        max_h = h
        max_m = m
        max_s = s

    if (max_h >= 10):
        result = "%02d:%02d" % (h, m)
    elif (max_h >= 1):
        result = "%d:%02d" % (h, m)
    else:
        result = "%02d" % (m)

    if include_seconds:
        result += ":%02d" % (s)

    return result
