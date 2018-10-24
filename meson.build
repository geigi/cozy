project('cozy',
  version: '0.6.4',
  meson_version: '>= 0.40.0')

project_name = 'cozy'

python = import('python3')
project_id = 'com.github.geigi.cozy'
i18n = import('i18n')
gnome = import('gnome')

message('Looking for dependencies')
python_bin = python.find_python()
if not python_bin.found()
    error('No valid python3 binary found')
else
    message('Found python3 binary')
endif

# dependency('gtk+-3.0', version :'>=3.14')
# dependency('glib-2.0')

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

subdir('data')
subdir('po')

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

peewee_dir = join_paths(meson.source_root(), 'peewee/lib/python3.5/site-packages')
new_peewee_dir = join_paths(meson.source_root(), 'peewee/lib/python3.5/dist-packages')
components = python_dir.split('/')

final_components = []
length = components.length()
i = 1

foreach c : components
  if i < length
    i += 1
    final_components += c
  endif
endforeach

peewee_install_dir = '/'.join(final_components)

if run_command('[', '-d', peewee_dir, ']').returncode() == 0
    message('Installing peewee dependency')
    run_command('mv', peewee_dir, new_peewee_dir)
    if r.returncode() == 0
      install_subdir(
        'peewee/lib/python3.5/dist-packages',
        install_dir: peewee_install_dir)
    endif
endif


