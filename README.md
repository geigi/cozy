# It's getting Cozy
<span class="badge-patreon"><a href="https://patreon.com/geigi" title="Donate to this project using Patreon"><img src="https://img.shields.io/badge/patreon-donate-yellow.svg" alt="Patreon donate button" /></a></span>
[![AUR](https://img.shields.io/aur/version/yaourt.svg)](https://aur.archlinux.org/packages/cozy-audiobooks/)

Cozy is a modern audio book player for Linux. 

![Screenshot](https://raw.githubusercontent.com/geigi/cozy/img/img/screenshot.png)

<p align="center">
  <a href="https://appcenter.elementary.io/com.github.geigi.cozy">
  <img src="https://appcenter.elementary.io/badge.svg" alt="Get it on AppCenter">
  </a>
</p>

### Here are some of the current features:
- Import all your audiobooks into cozy to browse them comfortably
- Listen to your DRM free mp3, m4a (aac, ALAC, ...), flac, ogg audio books
- Remembers your playback position
- Sleep timer!
- Playback speed control
- Search your library
- Sort your audio books by author, reader & name
- drag & drop to import new audiobooks
- Mpris integration (Media keys & playback info for desktop environment)
- developed on Arch Linux and tested under elementaryOS

## How can I get it?
### Flatpak
For most distributions you can use Flatpak to install and run cozy: <a href="https://flathub.org/repo/appstream/com.github.geigi.cozy.flatpakref">Flathub</a>
Or use the following commands:
```
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub com.github.geigi.cozy
```

### elementaryOS
If you're running elementaryOS, you can get cozy from the <a href="https://appcenter.elementary.io/com.github.geigi.cozy">App Center</a>.

### Arch Linux
Arch Linux users can find cozy under the name `cozy-audiobooks` in the AUR:
```
$ pacaur -S cozy-audiobooks
```

### Ubuntu, Debian, openSUSE, Fedora repositories
If you prefer a custom repository - for Ubuntu, Debian, openSUSE and Fedora there are package repositories on the <a href="https://software.opensuse.org//download.html?project=home%3Ageigi&package=com.github.geigi.cozy">openSUSE Build Service</a>.

### Upcoming:
- wav support
- Sort by name, added date, last played
- Ratings

If you like this project, consider supporting me on <a href="https://www.patreon.com/bePatron?u=8147127"> Patreon</a> :)

## Requirements
- `python3`
- `pip` for `peewee`
- `meson >= 0.40.0` as build system
- `ninja`
- `gtk3 >= 3.18` but fancier with `gtk3 >= 3.22`
- `peewee >= 2.10.1` as object relation mapper
- `python3-mutagen` for meta tag management
- `gstreamer1.0-plugins-good`
- `gstreamer1.0-libav` for mp4 support

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

## A big thanks
To the contributors on GitHub:
- oleg-krv 
- AsavarTzeth
- worldofpeace
- camellan

The translators:
- camellan
- Vistaus
- Distil62
- karaagac
- HansCz
- mvainola
- giuscasula
- abuyop
- akodi
- cleitonjfloss
- amadeussss
- nvivant
- Foxyriot
- mardojai

To nedrichards for the Flatpak.

## Help me translate cozy!
Cozy is on <a href="https://www.transifex.com/geigi/cozy/"> Transifex</a>, where anyone can contribute and translate. Can't find your language in the list? Let me know!


----
[![Maintainability](https://api.codeclimate.com/v1/badges/fde8cbdff23033adaca2/maintainability)](https://codeclimate.com/github/geigi/cozy/maintainability)
