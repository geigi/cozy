# It's getting Cozy

Cozy is a modern audio book player for Linux. 

<p align="center">
  <img src="https://raw.githubusercontent.com/geigi/cozy/master/data/icons/hicolor/scalable/apps/de.geigi.cozy.svg?sanitize=true" alt="Icon">
</p>

Here are some of the current features:
- Import all your audiobooks into cozy to browse them comfortably
- Listen to your DRM free mp3, flac, ogg audio books
- Remembers your playback position
- Sort your audio books by author, reader & name
- developed on Arch Linux and tested under elementaryOS

Upcoming:
- m4v support
- wav support
- Search
- drag & drop import and copy support
- Sort by name, added date, last played
- Ratings
- Media keys & notification integration
- Playback speed control
- Sleep timer

![Screenshot](https://raw.githubusercontent.com/geigi/cozy/img/img/screenshot.png)

## Requirements
- `python3`
- `pip` for `peewee`
- `meson >= 0.40.0` as build system
- `ninja`
- `gtk3 >= 3.18` but fancier with `gtk3 >= 3.22`
- `peewee >= 2.10.1` as object relation mapper
- `python3-mutagen` for meta tag management

## Build
```bash
$ git clone https://github.com/geigi/cozy.git
$ cd cozy
$ meson desired_build_directory --prefix=desired_installation_directory
$ ninja -C desired_build_directory install
```

## Running a local build
```
XDG_DATA_DIRS=desired_installation_directory/share:/usr/share PYTHONPATH=desired_installation_directory/lib/python3.[your_python3_version]/site-packages app/bin/cozy
```

## Help me translate cozy!
Cozy is on Transifex, where anyone can contribute and translate. Can't find your language in the list? Let me know!
https://www.transifex.com/geigi/cozy/
