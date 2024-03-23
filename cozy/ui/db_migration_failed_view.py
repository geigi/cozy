import webbrowser

import gi
from gi.repository import Adw

EXPLANATION = _("During an update of the database an error occurred and Cozy will not be able to startup.\
 A backup of the database was created before the update and has been restored now.\
 Until this issue is resolved please use version 0.9.5 of Cozy.\
 You can help resolve this problem by reporting an issue on GitHub.")


class DBMigrationFailedView(Adw.AlertDialog):
    def __init__(self):
        super().__init__(
            heading=_("Failed to Update Database"),
            body=EXPLANATION,
            default_response="help",
            close_response="close",
        )

        self.add_response("close", _("Close Cozy"))
        self.add_response("help", _("Receive help on GitHub"))
        self.set_response_appearance("help", Adw.ResponseAppearance.SUGGESTED)

        self.connect("response", self.get_help)

    def get_help(self, _, response):
        if response == "help":
            webbrowser.open("https://github.com/geigi/cozy/issues", new=2)

    def present(self) -> None:
        super().present()

