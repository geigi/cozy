message('Compiling blueprints')


blueprints = custom_target('blueprints',
  input: files(
    'album_element.blp',
    'book_detail.blp',
    'book_element.blp',
    'chapter_element.blp',
    'error_reporting.blp',
    'first_import_button.blp',
    'headerbar.blp',
    'main_window.blp',
    'media_controller.blp',
    'playback_speed_popover.blp',
    'preferences.blp',
    'progress_popover.blp',
    'search_page.blp',
    'seek_bar.blp',
    'storage_locations.blp',
    'storage_row.blp',
    'timer_popover.blp',
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)
