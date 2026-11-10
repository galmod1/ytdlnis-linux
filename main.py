# YTDLnis Linux — full-featured audio/video downloader for Linux, inspired by
# YTDLnis (Android, https://github.com/deniscerri/ytdlnis) — GPL-3.0.
import os
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk

from core.i18n import set_language
from core.settings import Settings
from core.theme import apply_appearance, apply_theme
from ui.window import MainWindow

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


class App(Gtk.Application):
    def __init__(self, app_id="org.galmod.ytdlnis.linux"):
        super().__init__(application_id=app_id)
        self.settings = Settings()
        set_language(self.settings.get("language", "ar"))
        self.window = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        apply_theme(self.settings.get("theme", "system"))
        provider = Gtk.CssProvider()
        provider.load_from_path(os.path.join(ASSETS, "style.css"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        apply_appearance(self.settings)

    def do_activate(self):
        if self.window is None:
            self.window = MainWindow(self)
        self.window.present()


def main():
    app = App()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
