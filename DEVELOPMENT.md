# Cozy development

This document is intended for software engineers and translators who would like to help out with the development of Cozy or simply be able to run bleeding edge versions of the code locally.

## Ubuntu

_The below instructions have been tested on Ubuntu 20.04_

## Requirements

```bash
sudo apt update
sudo apt install \
  gettext \
  git \
  gstreamer1.0-libav \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-ugly \
  libgstreamer1.0-0 \
  libgtk-3-dev \
  meson \
  pip \
  python-gi-cairo \
  python3-gst-1.0 \
  python3-venv

sudo snap install libhandy
```

In case of problems with the `libhandy` installation, try this instead:

```bash
sudo apt install libhandy-1-0 libhandy-1-dev
```

### UI development

[Glade](https://glade.gnome.org/) is the GUI tool we have been using for generating and managing application [windows and widgets](data/ui/).

## Source code

```bash
git clone https://github.com/geigi/cozy.git
cd cozy
```

## Python packages

It is generally a good idea to set up a virtual environment to avoid referencing packages and the Python binary installed globally.

> At its core, the main purpose of Python virtual environments is to create an isolated environment for Python projects. This means that each project can have its own dependencies, regardless of what dependencies every other project has.
>
> realpython.com

```bash
# only if you wish to use a virtual environment
python3 -m venv venv
source ./venv/bin/activate

pip install -r requirements.txt

pip install \
  pytest \
  pytest-mock
```

## Build and install

Let's assume you wish to build the application under the `build/` directory and install the binaries under `app/`:

```bash
meson build --prefix=app
ninja -C build install
```

### Install translation files

```bash
$ ninja -C build com.github.geigi.cozy-update-po
$ ninja -C build extra-update-po
```

## Run application

```bash
XDG_DATA_DIRS=app/share:/usr/share \
PYTHONPATH=app/lib/python3/dist-packages \
  app/bin/com.github.geigi.cozy
```

Everytime you make code changes, you will need to run `ninja -C build install` before you run the application.

## Test

```bash
python -m pytest
```