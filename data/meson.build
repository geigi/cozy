subdir('ui')
subdir('icons')

gnome.compile_resources(
    meson.project_name(),
    'gresource.xml',
    dependencies: blueprints,
    gresource_bundle: true,
    source_dir: meson.current_build_dir(),
    install_dir: DATA_DIR,
    install: true,
)

install_data(
    meson.project_name() + '.gschema.xml',
    install_dir: join_paths(get_option('datadir'), 'glib-2.0', 'schemas')
)

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test('Validate schema file', compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()]
  )
endif

desktop_file = i18n.merge_file(
    input: meson.project_name() + '.desktop',
    output: meson.project_name() + '.desktop',
    po_dir: join_paths(meson.current_source_dir(), 'po', 'extra'),
    type: 'desktop',
    install: true,
    install_dir: join_paths(get_option('datadir'), 'applications')
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils,
    args: [desktop_file]
  )
endif

appstream_file = i18n.merge_file(
    input: meson.project_name() + '.appdata.xml',
    output: meson.project_name() + '.appdata.xml',
    po_dir: join_paths(meson.current_source_dir(), 'po', 'extra'),
    install: true,
    install_dir: join_paths(get_option('datadir'), 'metainfo')
)

appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
  test('Validate appstream file', appstreamcli,
    args: ['validate', '--no-net', '--explain', appstream_file],
    workdir: meson.current_build_dir()
  )
endif
