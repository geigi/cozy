# It's getting Cozy

Cozy is a new GTK3 audio book manager and player. Here are some of the upcoming features:
- mp3, flac, ogg support
- display tags & cover
- category sort by author, reader & name
- developed on Arch Linux and tested under elementaryOS
- [ ] m4v support
- [ ] wav support
- [ ] remember playback position of audio books
- [ ] drag & drop support
- [ ] sort by name, added date, last played
- [ ] ratings
- [ ] media keys & notification integration
- [ ] playback speed
- [ ] sleep timer

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
# ninja -C desired_build_directory install
```

## Running a local build
```
XDG_DATA_DIRS=desired_installation_directory/share:/usr/share PYTHONPATH=desired_installation_directory/lib/python3.[your_python3_version]/site-packages app/bin/cozy
```

## Help me translate cozy!
Cozy is on Transifex, where anyone can help translate:
https://www.transifex.com/geigi/cozy/
