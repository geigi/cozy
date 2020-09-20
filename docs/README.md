# It's getting Cozy

Cozy is a modern audiobook player for Linux. 

![Screenshot](https://raw.githubusercontent.com/geigi/cozy/img/img/screenshot.png)

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

| Flatpak | openSUSE | Arch Linux | Solus | VoidLinux | elementaryOS |
|--------------|:----------:|:------------:|:-----:|:-----------------:| --- |
| {::nomarkdown}<a href='https://flathub.org/apps/details/com.github.geigi.cozy'><img width='150' alt='Download on Flathub' src='https://flathub.org/assets/badges/flathub-badge-en.png'/></a>{:/} | {::nomarkdown}<center><a href="https://software.opensuse.org/package/cozy">cozy</a>{:/} | {::nomarkdown}<a href="https://aur.archlinux.org/packages/cozy-audiobooks/">cozy-audiobooks</a></center>{:/} | {::nomarkdown}<a href="https://dev.getsol.us/source/cozy/">cozy</a>{:/} | {::nomarkdown}<a href="https://github.com/void-linux/void-packages/tree/master/srcpkgs/cozy">cozy</a>{:/} | Currently out of date. Please use Flatpak for now. | 

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
- magnickolas
- meisenzahl
- naglis
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
