def test_update_copy_status_emits_1_for_zero_files(mocker):
    from cozy.media.files import Files

    files = Files()
    spy = mocker.spy(files, "emit_event_main_thread")

    files._file_count = 0
    files._update_copy_status(1, 2, None)
    spy.assert_called_once_with("copy-progress", 1.0)


def test_update_copy_status_emits_1_for_zero_byte_files(mocker):
    from cozy.media.files import Files

    files = Files()
    spy = mocker.spy(files, "emit_event_main_thread")

    files._file_count = 1
    files._file_progess = 1
    files._update_copy_status(0, 0, None)

    spy.assert_called_once_with("copy-progress", 1.0)
