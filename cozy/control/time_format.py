from datetime import datetime
from gettext import ngettext

from gi.repository import Gst


def ns_to_time(
    nanoseconds: int, max_length: int | None = None, include_seconds: bool = True
) -> str:
    """
    Converts nanoseconds to a string with the following appearance:
    hh:mm:ss

    :param nanoseconds: int
    """
    m, s = divmod(nanoseconds / Gst.SECOND, 60)
    h, m = divmod(m, 60)

    if max_length:
        max_m, _ = divmod(max_length, 60)
        max_h, max_m = divmod(max_m, 60)
    else:
        max_h = h
        max_m = m

    if max_h >= 10:
        result = "%02d:%02d" % (h, m)
    elif max_h >= 1:
        result = "%d:%02d" % (h, m)
    else:
        result = "%02d" % m

    if include_seconds:
        result += ":%02d" % s

    return result


def ns_to_human_readable(nanoseconds: int) -> str:
    """
    Create a string with the following format:
    6 hours 1 minute
    45 minutes
    21 seconds
    :param seconds: int
    """
    m, s = divmod(nanoseconds / Gst.SECOND, 60)
    h, m = divmod(m, 60)
    h = int(h)
    m = int(m)
    s = int(s)

    result = ""
    if h > 0 and m > 0:
        result = (
            ngettext("{hours} hour", "{hours} hours", h).format(hours=h)
            + " "
            + ngettext("{minutes} minute", "{minutes} minutes", m).format(minutes=m)
        )
    elif h > 0:
        result = ngettext("{hours} hour", "{hours} hours", h).format(hours=h)
    elif m > 0:
        result = ngettext("{minutes} minute", "{minutes} minutes", m).format(minutes=m)
    elif s > 0:
        result = ngettext("{seconds} second", "{seconds} seconds", s).format(seconds=s)
    else:
        result = _("finished")

    return result


def date_delta_to_human_readable(unix_time):
    """
    Converts the date to the following strings (from today):
    today
    yesterday
    x days ago
    x week(s) ago
    x month(s) ago
    x year(s) ago
    """
    date = datetime.fromtimestamp(unix_time)
    past = datetime.today().date() - date.date()
    days = int(past.days)
    weeks = int(days / 7)
    months = int(days / 30)
    years = int(months / 12)

    if unix_time < 1:
        return _("never")
    elif days < 1:
        return _("today")
    elif days < 2:
        return _("yesterday")
    elif days < 7:
        return _("{days} days ago").format(days=days)
    elif weeks < 5:
        return ngettext("{weeks} week ago", "{weeks} weeks ago", weeks).format(weeks=weeks)
    elif months < 12:
        return ngettext("{months} month ago", "{months} months ago", months).format(months=months)
    else:
        return ngettext("{years} year ago", "{years} years ago", years).format(years=years)
