from pathlib import Path

from gi.repository import GLib


def get_path_relative_to_chache_folder(*args) -> Path:
    dir = Path(GLib.get_user_cache_dir(), "cozy", *args)
    dir.mkdir(parents=True, exist_ok=True)
    return dir


def get_artwork_cache_dir() -> Path:
    return get_path_relative_to_chache_folder("artwork")


def get_offline_cache_dir() -> Path:
    return get_path_relative_to_chache_folder("offline")


def get_cache_dir() -> Path:
    return get_path_relative_to_chache_folder()


def get_data_dir() -> Path:
    dir = Path(GLib.get_user_data_dir(), "cozy")
    dir.mkdir(parents=True, exist_ok=True)

    return dir
