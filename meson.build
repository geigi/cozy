project('com.github.geigi.cozy', version: '0.8')

python = import('python3')
i18n = import('i18n')
gnome = import('gnome')

message('Looking for dependencies')
python_bin = python.find_python()
if not python_bin.found()
    error('No valid python3 binary found')
else
    message('Found python3 binary')
endif

dependency('glib-2.0')
dependency('libhandy-1', version: '>= 1.0.0')

# from https://github.com/AsavarTzeth/pulseeffects/blob/master/meson.build
# Support Debian non-standard python paths
# Fallback to Meson python3 module if command fails
message('Getting python install path')
py3_purelib = ''
r = run_command(python_bin.path(), '-c', 'from distutils.sysconfig import get_python_lib; print(get_python_lib(prefix=""))')
if r.returncode() != 0
  py3_purelib = python.sysconfig_path('purelib')
  if not py3_purelib.endswith('site-packages')
    error('Cannot find python install path')
  endif
  python_dir = py3_purelib
else
  python_dir = r.stdout().strip()
endif

# Python 3 required modules
python3_required_modules = ['distro', 'peewee', 'mutagen', 'gi']

foreach p : python3_required_modules
  # Source: https://docs.python.org/3/library/importlib.html#checking-if-a-module-can-be-imported
  script = 'import importlib.util; import sys; exit(1) if importlib.util.find_spec(\''+ p +'\') is None else exit(0)'
  if run_command(python_bin, '-c', script).returncode() != 0
    error('Required Python3 module \'' + p + '\' not found')
  endif
endforeach

LIBEXEC_DIR = join_paths(get_option('prefix'), 'libexec')
DATA_DIR = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())

conf = configuration_data()
conf.set('PACKAGE_URL', 'https://github.com/geigi/cozy')
conf.set('DATA_DIR', DATA_DIR)
conf.set('LOCALE_DIR', join_paths(get_option('prefix'), get_option('datadir'), 'locale'))
conf.set('PYTHON_DIR', python_dir)
conf.set('PYTHON_EXEC_DIR', join_paths(get_option('prefix'), python.sysconfig_path('stdlib')))
conf.set('libexecdir', LIBEXEC_DIR)
conf.set('VERSION', meson.project_version())
conf.set('PYTHON', python_bin.path())
conf.set('INSTALLED', 'true')

subdir('data')
subdir('po')

message('Compile gnome schemas')

message('Preparing init file')
configure_file(
  input: 'main.py',
  output: 'com.github.geigi.cozy',
  configuration: conf,
  install_dir: 'bin'
)

install_subdir(
  'cozy',
  install_dir: python_dir
)

configure_file(
  input: 'cozy/version.py',
  output: 'version.py',
  configuration: conf,
  install_dir: python_dir + '/cozy'
)

configure_file(
  input: 'cozy/report/report_to_loki.py',
  output: 'report_to_loki.py',
  configuration: conf,
  install_dir: python_dir + '/cozy/report'
)

meson.add_install_script('meson/post_install.py')
