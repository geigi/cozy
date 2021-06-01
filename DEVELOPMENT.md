# Cozy development

This document is intended for software engineers and translators who would like to help out with the development of Cozy or simply be able to run bleeding edge versions of the code locally.

## Ubuntu

_The below instructions have been tested on Ubuntu 20.04_

## Requirements

```bash
sudo apt update
sudo apt install \
  appstream-util \
  cmake \
  gettext \
  git \
  gir1.2-granite-1.0 \
  gstreamer1.0-libav \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-ugly \
  libgirepository1.0-dev \
  libgstreamer1.0-0 \
  libgtk-3-dev \
  libgranite5 \
  libgranite-dev \
  pip \
  python-gi-cairo \
  python3-gst-1.0 \
  python3-venv

sudo add-apt-repository ppa:apandada1/libhandy-1
sudo apt update
sudo apt install libhandy-1-0 libhandy-1-dev
```

In case of issues with the `libhandy` installation, please refer to our [GitHub build script](.github/workflows/build.yml) on an alternative source of the library packages.

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

python -m pip install --upgrade pip
pip install -r requirements.txt

pip install \
  meson \
  ninja

pip install \
  pytest \
  pytest-mock
```

## Build and install

Let's assume you wish to build the application under the `build/` directory and install the binaries under `app/`:

```bash
meson --prefix=$(pwd)/app ./build

ninja -C build install
```

### Install translation files

```bash
ninja -C build com.github.geigi.cozy-update-po
ninja -C build extra-update-po
```

## Run application

```bash
XDG_DATA_DIRS=app/share:/usr/share \
PYTHONPATH=app/lib/python3.8/site-packages \
  app/bin/com.github.geigi.cozy
```

Your Python path may be different so you might need to amend the `PYTHONPATH` environment variable above in case of errors.

Please note, every time you make code changes, you need to execute `ninja -C build install` before you run the application.

## Debug

### Visual Studio Code

Below are sample VSCode configuration files that follow the same assumptions:
- Python virtual environment has been set up under `venv/`
- application is built under `build/` and installed under `app/` directories
- Python version: 3.8

If your set-up is different, you might need to customise the configuration below.

`.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "install",
      "type": "shell",
      "command": "source ./venv/bin/activate; ninja install -C build",
      "options": {
        "cwd": "${workspaceFolder}"
      }
    }
  ]
}
```

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Cozy app",
      "type": "python",
      "request": "launch",
      "preLaunchTask": "install",
      "program": "app/bin/com.github.geigi.cozy",
      "justMyCode": false,
      "cwd": "${workspaceFolder}",
      "env": {
        "XDG_DATA_DIRS": "app/share:/usr/share",
        "PYTHONPATH": "app/lib/python3.8/site-packages"
      }
    }
  ]
}
```

Please note, the above configuration only allows for debugging of files installed under `app/`, not the actual source files.

## Test

```bash
python -m pytest
```