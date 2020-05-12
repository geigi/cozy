![Unit Testing](https://github.com/geigi/cozy/workflows/Unit%20Testing/badge.svg)
<p align="center">
  <img width="200" height="200" src="https://raw.githubusercontent.com/geigi/cozy/master/data/icons/hicolor/scalable/apps/com.github.geigi.cozy.svg">
</p>
<p align="center">
  <a href='https://flathub.org/apps/details/com.github.geigi.cozy'><img width='150' alt='Download on Flathub' src='https://flathub.org/assets/badges/flathub-badge-en.png'/></a>
</p>

# It's getting Cozy

![Screenshot](https://raw.githubusercontent.com/geigi/cozy/img/img/screenshot.png)

Cozy is a modern audiobook player for Linux and macOS. 

## Here are some of the current features:
- **Import** your audiobooks into Cozy to browse them comfortably
- **Sort** your audio books by author, reader & name
- **Remembers** your **playback position**
- **Sleep timer**
- **Playback speed control**
- **Search** your library
- **Offline Mode!** This allows you to keep an audio book on your internal storage if you store your audiobooks on an external or network drive. Perfect for listening on the go!
- Add **mulitple storage locations**
- **Drag & Drop** to import new audio books
- Support for DRM free **mp3, m4a (aac, ALAC, …), flac, ogg, opus, wav** files
- Mpris integration (**Media keys** & playback info for desktop environment)
- Developed on Fedora and tested under elementaryOS

# Install
| elementaryOS | openSUSE | Arch Linux | Flatpak (other) | macOS |
|--------------|:----------:|:------------:|-----------------|:-------:|
| <a href="https://appcenter.elementary.io/com.github.geigi.cozy"><img src="https://appcenter.elementary.io/badge.svg" alt="Get it on AppCenter"></a> | <center><a href="https://software.opensuse.org/package/cozy">cozy</a> | <a href="https://aur.archlinux.org/packages/cozy-audiobooks/">cozy-audiobooks</a></center> | <a href='https://flathub.org/apps/details/com.github.geigi.cozy'><img width='150' alt='Download on Flathub' src='https://flathub.org/assets/badges/flathub-badge-en.png'/></a> | <center><a href="https://github.com/geigi/cozy/releases/download/0.6.4/cozy_macos_0.6.4_beta2.dmg">Beta 2</a></center> |  

## macOS
Cozy for macOS is currently in beta. It's tested on 10.14 Mojave so far. Known bugs:
- no integration in notification center or any other desktop integration really
- media keys are not working
- dark mode requires 2x switching in settings + is not loading automatically at startup
- large Cozy.app

You can download it here: <a href="https://github.com/geigi/cozy/releases/download/0.6.7/cozy_macos_0.6.7_beta3.dmg">Cozy 0.6.7 beta3 for macOS</a>

## Requirements
- `python3`
- `meson >= 0.40.0` as build system
- `gtk3 >= 3.18` but fancier with `gtk3 >= 3.22`
- `peewee >= 3.9.6` as object relation mapper
- `python3-mutagen` for meta tag management
- `python3-distro`
- `python3-requests`
- `python3-pytz`
- `python3-gi-cairo`
- `python3-gst-1.0`
- `file`
- `gstreamer1.0-plugins-good`
- `gstreamer1.0-plugins-bad`
- `gstreamer1.0-plugins-ugly`
- `gstreamer1.0-libav` for mp4 support


## Build
```bash
$ git clone https://github.com/geigi/cozy.git
$ cd cozy
$ meson desired_build_directory --prefix=desired_installation_directory
$ ninja -C desired_build_directory install
```

## Update `po` files
```bash
$ ninja -C build com.github.geigi.cozy-update-po
$ ninja -C build extra-update-po
```

## Running a local build
```
XDG_DATA_DIRS=desired_installation_directory/share:/usr/share PYTHONPATH=desired_installation_directory/lib/python3.[your_python3_version]/site-packages app/bin/com.github.geigi.cozy
```

## Q&A
### I have imported wrong files and cannot get rid of them:
Delete the following folders to reset cozy (this will loose all saved progress):
```
~/.local/share/cozy
~/.cache/cozy
```


### I can't uninstall the Flatpak:
Try
```
flatpak uninstall com.github.geigi.cozy/x86_64/stable
```
or
```
flatpak uninstall --user com.github.geigi.cozy/x86_64/stable
```
Thanks to @Meresmata

### I store my audiobooks in a location that is not accessible in the Flatpak sandbox:
You can override the flatpak settings and allow access to a path (e.g. /media) like this:
```
flatpak --user override --filesystem=/media com.github.geigi.cozy
```

## A big thanks
To the contributors on GitHub:
- AsavarTzeth
- Fatih20
- NathanBnm
- camellan
- elya5
- grenade
- jnbr
- kaphula
- meisenzahl
- oleg-krv
- umeboshi2
- worldofpeace

The translators:
- Distil62
- Fitoschido
- Floflr
- Foxyriot
- HansCz
- IvoIliev
- MageJohn
- Nimmerliefde
- Potty0
- TheMBTH
- TheRuleOfMike
- Vistaus
- W2hJ3MOmIRovEpTeahe80jC
- aKodi
- abuyop
- akodi
- albanobattistella
- amadeussss
- andreapillai
- arejano
- camellan
- chris109b
- cjfloss
- cleitonjfloss
- corentinbettiol
- dtgoitia
- eson
- fishcake13
- fountain
- georgelemental
- giuscasula
- jan_nekvasil
- jouselt
- karaagac
- libreajans
- linuxmasterclub
- mardojai
- mvainola
- nvivant
- oleg_krv
- test21
- trampover
- twardowskidev
- txelu
- yalexaner

To nedrichards for the Flatpak.

## Help me translate cozy!
Cozy is on <a href="https://www.transifex.com/geigi/cozy/"> Transifex</a>, where anyone can contribute and translate. Can't find your language in the list? Let me know!

If you like this project, consider supporting me on <a href="https://www.patreon.com/bePatron?u=8147127"> Patreon</a> :)

----
[![Maintainability](https://api.codeclimate.com/v1/badges/fde8cbdff23033adaca2/maintainability)](https://codeclimate.com/github/geigi/cozy/maintainability)
