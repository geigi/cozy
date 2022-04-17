![Unit Testing](https://github.com/geigi/cozy/workflows/Unit%20Testing/badge.svg)
<p align="center">
  <img width="200" height="200" src="https://raw.githubusercontent.com/geigi/cozy/master/data/icons/hicolor/scalable/apps/com.github.geigi.cozy.svg">
</p>
<p align="center">
  <a href='https://flathub.org/apps/details/com.github.geigi.cozy'><img width='150' alt='Download on Flathub' src='https://flathub.org/assets/badges/flathub-badge-en.png'/></a>
</p>

# It's getting Cozy

![Screenshot](https://raw.githubusercontent.com/geigi/cozy/img/img/screenshot1.png)

Cozy is a modern audiobook player for Linux.
Head over to [Matrix](https://matrix.to/#/#cozy:gnome.org?via=matrix.org&via=gnome.org) to join the conversation.

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

# Install

| Distro | Package |
|--------|:---------:|
| Flatpak | <a href='https://flathub.org/apps/details/com.github.geigi.cozy'><img width='150' alt='Download on Flathub' src='https://flathub.org/assets/badges/flathub-badge-en.png'/></a> |
| openSUSE | <center><a href="https://software.opensuse.org/package/cozy">cozy</a> |
| Fedora | <center><a href="https://src.fedoraproject.org/rpms/cozy">cozy</a> |
| Arch Linux (AUR) | <a href="https://aur.archlinux.org/packages/cozy-audiobooks/">cozy-audiobooks</a></center> |
| VoidLinux | <a href="https://github.com/void-linux/void-packages/tree/master/srcpkgs/cozy">cozy</a> |
| Solus | <a href="https://dev.getsol.us/source/cozy/">cozy</a> |
| MX Linux | <center><a href="https://forum.mxlinux.org/viewtopic.php?p=621071#p621071">Cozy</a> |
| elementaryOS | Currently out of date. Please use Flatpak for now. |
| Ubuntu (PPA) | <center><a href="https://launchpad.net/~cozy-team/+archive/ubuntu/cozy">cozy</a> |
| OpenBSD | <center><a href="https://cvsweb.openbsd.org/ports/audio/cozy/">cozy</a> |
| Nix | <center><a href="https://github.com/NixOS/nixpkgs/blob/master/pkgs/applications/audio/cozy/default.nix">cozy</a> |


## elementaryOS
The App Center version of Cozy is currently out of date. elementaryOS ships with old versions of dependencies needed by Cozy. Those are not compatible anymore. Therefore I'm unable to update the App Center version to the latest version of Cozy. Please switch over to the Flatpak version for now. If you experience issues with moving your library, let me know!

elementaryOS is working on a new version of App Center which will be based on Flatpak. When the new App Center is live, Cozy will be back on the app center! :) Thanks for everyone who supported me on the App Center.

## macOS
**Currently discontinued**

There is an older beta of Cozy 0.6.7 which is tested on macOS 10.14. It might not work with newer versions of macOS. 
Because the build process is rather complicated and not easy to automate I've currently discontinued building for macOS. If you're interested in the build process: have a look at my [writeup](https://gist.github.com/geigi/a3b6d661daeb7b181d3bdd3cab517092).

Some information about the old beta:

- no integration in notification center or any other desktop integration really
- media keys are not working
- dark mode requires 2x switching in settings + is not loading automatically at startup
- large Cozy.app

You can download it here: <a href="https://github.com/geigi/cozy/releases/download/0.6.7/cozy_macos_0.6.7_beta3.dmg">Cozy 0.6.7 beta3 for macOS</a>

# Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed instructions and developing Cozy on Ubuntu.

## Requirements
- `python3`
- `meson >= 0.40.0` as build system
- `gtk3 >= 3.22`
- `libhandy >= 1.0.0`
- `libdazzle >= 3.34.0`
- `peewee >= 3.9.6` as object relation mapper
- `mutagen` for meta tag management
- `distro`
- `requests`
- `pytz`
- `packaging`
- `gi-cairo`
- `gst-1.0`
- `file`
- `gstreamer1.0-plugins-good`
- `gstreamer1.0-plugins-bad`
- `gstreamer1.0-plugins-ugly`
- `gstreamer1.0-libav` for mp4 support

## Bundled Requirements
- `inject`: https://github.com/ivankorobkov/python-inject

This dependency is bundled because it is not generally available as a linux package. The licence is respected and included.

## Build

```bash
$ git clone https://github.com/geigi/cozy.git
$ cd cozy
$ meson <build_dir> --prefix=<installation_dir>
$ ninja -C <build_dir> install
```

## Update `po` files
```bash
$ ninja -C <build_dir> com.github.geigi.cozy-update-po
$ ninja -C <build_dir> extra-update-po
```

## Running a local build
```
XDG_DATA_DIRS=<installation_dir>/share:/usr/share \
PYTHONPATH=<installation_dir>/lib/python3.[your_python3_version]/site-packages \
  app/bin/com.github.geigi.cozy
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
- A6GibKm
- alyssais
- apandada1
- AsavarTzeth
- Fatih20
- NathanBnm
- camellan
- chris-kobrzak
- elya5
- foliva
- grenade
- jimmac
- jnbr
- jubalh
- kaphula
- leuc
- magnickolas
- meisenzahl
- naglis
- oleg-krv
- paper42
- phpwutz
- rapenne-s
- thibaultamartin
- umeboshi2
- worldofpeace

The translators:
- Ainte
- AndreBarata
- Andrey389
- Asyx
- BunColak
- Caarmi
- CiTyBear
- Distil62
- Fitoschido
- Floflr
- Foxyriot
- HansCz
- IngrownMink4
- IvoIliev
- Jagadeeshvarma
- Kwentin
- MageJohn
- NHiX
- Nimmerliefde
- Oi_Suomi_On
- Okton
- Panwar108
- Potty0
- Sebosun
- TheMBTH
- TheRuleOfMike
- Vistaus
- W2hJ3MOmIRovEpTeahe80jC
- WhiredPlanck
- _caasi
- aKodi
- abcmen
- abuyop
- albanobattistella
- amadeussss
- andreapillai
- arejano
- artnay
- b3nj4m1n
- baschdl78
- camellan
- cavinsmith
- cho2
- chris109b
- cjfloss
- ckaotik
- corentinbettiol
- dtgoitia
- dzerus3
- elgosz
- endiamesos
- eson
- fishcake13
- fountain
- fran.dieguez
- georgelemental
- giuscasula
- goran.p1123581321
- hamidout
- hkoivuneva
- jan.sundman
- jan_nekvasil
- jouselt
- karaagac
- kevinmueller
- leondorus
- libreajans
- linuxmasterclub
- magnickolas
- makaleks
- mannycalavera42
- mardojai
- markluethje
- milotype
- mvainola
- n1k7as
- nikkpark
- no404error
- nvivant
- oleg_krv
- ooverloord
- oscfdezdz
- pavelz
- rafaelff1
- ragouel
- saarikko
- sobeitnow0
- sojuz151
- steno
- tclokie
- test21
- thibaultmartin
- translatornator
- tsitokhtsev
- twardowskidev
- txelu
- useruseruser1233211
- vanhoxx
- vlabo
- xfgusta
- yalexaner
- bittin


To nedrichards for the Flatpak.

## Help me translate cozy!
Cozy is on <a href="https://www.transifex.com/geigi/cozy/"> Transifex</a>, where anyone can contribute and translate. Can't find your language in the list? Let me know!

If you like this project, consider supporting me on <a href="https://www.patreon.com/bePatron?u=8147127"> Patreon</a> :)

----
[![Maintainability](https://api.codeclimate.com/v1/badges/fde8cbdff23033adaca2/maintainability)](https://codeclimate.com/github/geigi/cozy/maintainability)
