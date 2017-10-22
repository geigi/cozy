subdir('img')
subdir('ui')
subdir('icons')

message('Compiling schemas')

gnome.compile_schemas()
install_data(
  project_id + '.gschema.xml',
  install_dir: 'share/glib-2.0/schemas'
)
meson.add_install_script('meson_post_install.py')

message('Making a .desktop file')
i18n.merge_file(
  output: project_id + '.desktop',
  input: 'desktop.in',
  po_dir: '../po',
  type: 'desktop',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

message('Preparing appdata')
install_data(
  project_id + '.appdata.xml',
  install_dir: join_paths(get_option('datadir'), 'metainfo')
)
