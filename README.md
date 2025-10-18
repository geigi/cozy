<p align="center">
  <img width="200" height="200" src="https://raw.githubusercontent.com/geigi/cozy/master/data/icons/hicolor/scalable/apps/com.github.geigi.cozy.svg">
</p>
<p align="center">
  <a href='https://flathub.org/apps/details/com.github.geigi.cozy'><img width='150' alt='Download on Flathub' src='https://flathub.org/assets/badges/flathub-badge-en.png'/></a>
</p>

# It's getting Cozy

[![Tests](https://github.com/geigi/cozy/actions/workflows/tests.yml/badge.svg)](https://github.com/geigi/cozy/actions/workflows/tests.yml)
![Flathub Downloads](https://img.shields.io/flathub/downloads/com.github.geigi.cozy?color=e66100&logo=flatpak&label=Flathub%20installs)

![Screenshot](https://raw.githubusercontent.com/geigi/cozy/img/img/screenshot1.png)

Cozy is a modern audiobook player for Linux.
Head over to [Matrix](https://matrix.to/#/#cozy:gnome.org) to join the conversation.

## Here are some of the current features:
- **Import** all your audio books into Cozy to browse them comfortably
- **Sort** your audio books by author, reader & name
- **Remembers** your **playback position**
- **Sleep timer**
- **Playback speed control** for each book individually
- **Search** your library
- **Offline Mode!** This allows you to keep an audio book on your internal storage if you store your audiobooks on an external or network drive. Perfect for listening on the go!
- Add **multiple storage locations**
- **Drag & Drop** to import new audio books
- Listen to your DRM free **mp3, m4b, m4a (aac, ALAC, …), flac, ogg and wav** audio books
- MPRIS integration (**Media keys** & playback info for desktop environment)

# Installation 

The preferred way to install Cozy is via Flatpak. You can get the official package from Flathub.

<a href='https://flathub.org/apps/details/com.github.geigi.cozy'><img width='150' alt='Download on Flathub' src='https://flathub.org/assets/badges/flathub-badge-en.png'/></a>

Alternatively, there are third party packages available in distros' repositories. Keep in mind that these packages are usually outdated, and if you encounter an issue, they may in fact have already been fixed.

<details>
<summary>List of distro packages</summary>

| Distro | Package |
|--------|:---------:|
| openSUSE | <center><a href="https://software.opensuse.org/package/cozy">cozy</a> |
| Fedora | <center><a href="https://src.fedoraproject.org/rpms/cozy">cozy</a> |
| Arch Linux (AUR) | <a href="https://aur.archlinux.org/packages/cozy-audiobooks/">cozy-audiobooks</a></center> |
| Debian | <a href="https://packages.debian.org/cozy">cozy</a></center> |
| VoidLinux | <a href="https://github.com/void-linux/void-packages/tree/master/srcpkgs/cozy">cozy</a> |
| Solus | <a href="https://dev.getsol.us/source/cozy/">cozy</a> |
| MX Linux | <center><a href="https://forum.mxlinux.org/viewtopic.php?p=621071#p621071">Cozy</a> |
| Ubuntu (PPA) | <center><a href="https://launchpad.net/~cozy-team/+archive/ubuntu/cozy">cozy</a> |
| OpenBSD | <center><a href="https://cvsweb.openbsd.org/ports/audio/cozy/">cozy</a> |
| Nix | <center><a href="https://github.com/NixOS/nixpkgs/blob/master/pkgs/by-name/co/cozy/package.nix">cozy</a> |

</details>

# Development
See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed instructions about developing Cozy in GNOME Builder, Fedora and Ubuntu

## FAQ
### I have imported wrong files and cannot get rid of them:
Delete the following folders to reset Cozy (this will lose all saved progress):
```
~/.local/share/cozy
~/.cache/cozy
```


### I can't uninstall the Flatpak:
Try
```console
flatpak uninstall com.github.geigi.cozy/x86_64/stable
```
or
```console
flatpak uninstall --user com.github.geigi.cozy/x86_64/stable
```
Thanks to @Meresmata

### I store my audiobooks in a location that is not accessible in the Flatpak sandbox:
You can use the [Flatseal](https://flathub.org/en/apps/com.github.tchx84.Flatseal) application to change permissions of a Flatpak app and allow access to a custom path (e.g. `/media`) like this:

<img height="450" alt="image" src="https://github.com/user-attachments/assets/1f999ddf-f7f6-4127-9cae-38b60ed9f0f5" />



## Thanks
A big thanks to all the contributors and translators! See the complete list in [AUTHORS.md](AUTHORS.MD)


## Help us translate Cozy!
Cozy is on <a href="https://explore.transifex.com/geigi/cozy/">Transifex</a>, where anyone can contribute and translate. Can't find your language in the list? Let us know!

If you like this project, consider supporting me on <a href="https://www.patreon.com/geigi">Patreon</a> :)
