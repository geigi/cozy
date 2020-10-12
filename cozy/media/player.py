from cozy.architecture.event_sender import EventSender
from cozy.architecture.singleton import Singleton
from cozy.control import player
from cozy.model.book import Book
from cozy.model.chapter import Chapter


class Player(EventSender):
    def __init__(self):
        super().__init__()
        self._gst_player: player = player.get_playbin()
        player.add_player_listener(self._pass_legacy_player_events)

    def play_pause(self, book: Book):
        pass

    def play_pause(self, chapter: Chapter):
        # current_track = player.get_current_track()
        # if current_track and current_track.id == self.chapter.id:
        #     player.play_pause(None)
        #     if player.get_gst_player_state() == Gst.State.PLAYING:
        #         player.jump_to_ns(Track.select().where(Track.id == self.chapter.id).get().position)
        # else:
        #     player.load_file(Track.select().where(Track.id == self.chapter.id).get())
        #     player.play_pause(None, True)
        #     Book.update(position=self.chapter).where(Book.id == self.chapter.book.id).execute()
        pass

    def _pass_legacy_player_events(self, event, message):
        if event == "play" and message:
            message = message.id
        self.emit_event(event, message)
