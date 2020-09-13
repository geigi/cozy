from gi.overrides import Gio

settings = Gio.Settings.new("com.github.geigi.cozy")


def get_glib_settings():
    global settings
    return settings
