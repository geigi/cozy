# It's getting Cozy

Cozy is a new GTK3 audio book manager and player. Here are some of the upcoming features:
- [ ] mp3, m4v, flac, wav support
- [ ] remember playback position of audio books
- [ ] drag & drop support
- [ ] display tags & cover
- [ ] category sort by author, reader & name
- [ ] sort by name, added date, last played
- [ ] ratings
- [ ] media keys & notification integration
- [ ] playback speed
- [ ] sleep timer

## Requirements
- `python3`
- `meson >= 0.40.0`
- `ninja`
- `gtk3 >= 3.16`

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
