import webbrowser

import gi

from cozy.ext import inject

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk


@Gtk.Template(resource_path='/com/github/geigi/cozy/db_migration_failed.ui')
class DBMigrationFailedView(Gtk.Dialog):
    __gtype_name__ = 'DBMigrationFailedDialog'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def show(self):
        response = self.run()

        if response == Gtk.ResponseType.OK:
            webbrowser.open("https://github.com/geigi/cozy/issues", new=2)
