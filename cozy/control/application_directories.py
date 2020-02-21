import os

from gi.repository import GLib


def get_cache_dir():
    cache_dir = os.path.join(GLib.get_user_cache_dir(), "cozy")

    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    return cache_dir


def get_data_dir():
    return os.path.join(GLib.get_user_data_dir(), "cozy")
