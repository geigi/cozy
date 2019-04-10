subdir('img')
subdir('ui')
subdir('icons')

message('Compiling schemas')

gnome.compile_schemas()
install_data(
  meson.project_name() + '.gschema.xml',
  install_dir: 'share/glib-2.0/schemas'
)
meson.add_install_script('meson_post_install.py')

i18n.merge_file(
    input: meson.project_name() + '.desktop.in',
    output: meson.project_name() + '.desktop',
    po_dir: join_paths(meson.source_root(), 'po'),
    type: 'desktop',
    install: true,
    install_dir: join_paths(get_option('datadir'), 'applications')
)

i18n.merge_file(
    input: meson.project_name() + '.appdata.xml.in',
    output: meson.project_name() + '.appdata.xml',
    po_dir: join_paths(meson.source_root(), 'po'),
    install: true,
    install_dir: join_paths(get_option('datadir'), 'metainfo')
)
