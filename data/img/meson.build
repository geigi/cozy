message('Compiling resources')

gnome.compile_resources(
  meson.project_name() + '.img',
  'gresource.xml',
  gresource_bundle: true,
  source_dir: '.',
  install_dir: DATA_DIR,
  install: true
)
