#!/usr/bin/env python3

from os import path, environ
import subprocess

prefix = environ.get('MESON_INSTALL_PREFIX', '/usr/local')
schemadir = path.join(environ['MESON_INSTALL_PREFIX'], 'share', 'glib-2.0', 'schemas')
datadir = path.join(prefix, 'share')

if not environ.get('DESTDIR'):
    print('Compiling gsettings schemas…')
    subprocess.call(['glib-compile-schemas', schemadir])
    print('Updating icon cache…')
    subprocess.call(['gtk-update-icon-cache', '-qtf', path.join(datadir, 'icons', 'hicolor')])