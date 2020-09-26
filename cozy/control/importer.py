import errno
import logging
import os
import shutil
import urllib
import urllib.parse

import gi

gi.require_version('GstPbutils', '1.0')
from gi.repository import Gdk, GLib

from cozy.db.storage import Storage
from cozy.report import reporter

log = logging.getLogger("importer")


def copy(ui, selection):
    """
    Copy the selected files to the audiobook location.
    """
    selection = selection.get_uris()

    # count the work
    count = len(selection)
    cur = 0

    for uri in selection:
        parsed_path = urllib.parse.urlparse(uri)
        path = urllib.parse.unquote(parsed_path.path)
        if os.path.isfile(path) or os.path.isdir(path):
            copy_to_audiobook_folder(path)
            cur = cur + 1
            Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE,
                                 ui.titlebar.update_progress_bar.set_fraction, cur / count)

    Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, ui.scan, None, None)


def copy_to_audiobook_folder_new(path):
    try:
        name = os.path.basename(os.path.normpath(path))
        storage_location_path = Storage.select().where(Storage.default == True).get().path


def copy_to_audiobook_folder(path):
    """
    Copies the given path (folder or file) to the audio book folder.
    """
    try:
        name = os.path.basename(os.path.normpath(path))
        storage_location_path = Storage.select().where(Storage.default == True).get().path
        shutil.copytree(path, os.path.join(storage_location_path, name), dirs_exist_ok=True)
    except OSError as exc:
        reporter.exception("importer", exc)
        if exc.errno == errno.ENOTDIR:
            try:
                storage_location_path = Storage.select().where(Storage.default == True).get().path
                shutil.copy(path, storage_location_path)
            except OSError as e:
                if e.errno == 95:
                    log.error("Could not import file " + path)
                    log.error(exc)
                else:
                    log.error(e)
        elif exc.errno == errno.ENOTSUP:
            log.error("Could not import file " + path)
            log.error(exc)
        else:
            log.error("Could not import file " + path)
            log.error(exc)
