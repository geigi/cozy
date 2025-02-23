# Cozy development

This document is intended for software engineers and translators who would like to help out with the development of Cozy, or simply be able to run bleeding edge versions of the code locally.

## Code style

To ensure good quality code, we lint our codebase with Ruff. We recommend that you run Ruff before pushing your changes to GitHub and correct the warnings, otherwise the automatic checks on pull requests will fail.

```
ruff check <filename>
```

For consistent code style, we format the source files using `black` and `isort`. Run these two tools on the changed files before committing.

```
black cozy
isort cozy
```

You can install these tools via pip: 

```
pip install black isort ruff
```


## Building with GNOME Builder (recommended)

We recommend using [GNOME Builder](https://apps.gnome.org/Builder/) to build and run Cozy.

1. Open GNOME Builder
2. Click the **Clone Repository** button
3. Enter `https://github.com/geigi/cozy.git` in the **Repository URL** field
4. Click the **Clone Project** button
5. Click the ▶️**Run** button to start building the application


## Building manually

_The below instructions have been tested on Ubuntu 20.04 and Fedora 39_


### Requirements (Ubuntu)

```console
sudo apt update
sudo apt install \
  appstreamcli \
  cmake \
  gettext \
  git \
  gstreamer1.0-libav \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-ugly \
  libgirepository1.0-dev \
  libgstreamer1.0-0 \
  libgtk-4-dev \
  libadwaita-1-dev \
  pip \
  python-gi-cairo \
  python3-gst-1.0 \
  python3-venv
```


### Requirements (Fedora)

```console
sudo dnf install \
  appstream \
  cmake \
  gettext \
  gstreamer1-libav \
  gstreamer1-plugins-ugly \
  gstreamer1-plugins-bad \
  gstreamer1-plugins-good \
  gstreamer1-devel\
  gtk4-devel \
  libadwaita-devel \
  pipenv \
  python3-cairo-devel \
  python3-gstreamer1
```


### Source code

```console
git clone https://github.com/geigi/cozy.git
cd cozy
```


### Python packages

> [!TIP]
> It is generally a good idea to set up a virtual environment for Python projects. It creates an isolated environment where packages can be installed without creating conflicts with other packages installed system-wide.

```console
python3 -m venv venv
source ./venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

pip install meson ninja

pip install pytest pytest-mock
```

To enter the virtual environment, you will need to run `source ./venv/bin/activate` every time you reopen your terminal.


### Build and install

Let's assume you wish to build the application under the `build/` directory and install the binaries under `app/`:

```console
meson setup --prefix=$(pwd)/app ./build

ninja -C build install
```


### Install translation files

```console
ninja -C build com.github.geigi.cozy-update-po
ninja -C build extra-update-po
```


### Run application

```console
XDG_DATA_DIRS=app/share:/usr/share \
PYTHONPATH=app/lib/python3.11/site-packages \
  app/bin/com.github.geigi.cozy
```

Your Python path may be different so you might need to amend the `PYTHONPATH` environment variable above in case of errors.

> [!NOTE]
> Every time you make changes to the code, you need to execute `ninja -C build install` before you run the application.


## Running the test suite

```bash
python -m pytest
```

