def test_get_media_data_should_work_with_valid_audio_files(mocker):
    from cozy.media.media_detector import MediaDetector

    mocker.patch("gi.repository.GstPbutils.Discoverer")
    mocker.patch("gi.repository.Gst.init")

    file_extensions = ['.mp3', '.ogg', '.flac', '.m4a', '.m4b', '.mp4', '.wav', '.opus']

    for extension in file_extensions:
        md = MediaDetector("/test.{}".format(extension))
        assert md._has_audio_file_ending()

    for extension in file_extensions:
        md = MediaDetector("/test.{}".format(extension.upper()))
        assert md._has_audio_file_ending()
