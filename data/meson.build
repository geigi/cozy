subdir('img')
subdir('ui')

message('Making a .desktop file')
i18n.merge_file(
  output: project_id + '.desktop',
  input: 'desktop.in',
  po_dir: '../po',
  type: 'desktop',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

#message('Preparing appdata')
#i18n.merge_file(
#  output: project_id + '.appdata.xml',
#  input: 'appdata.xml.in',
#  po_dir: '../po',
#  install: true,
#  install_dir: join_paths(get_option('datadir'), 'appdata')
#)
