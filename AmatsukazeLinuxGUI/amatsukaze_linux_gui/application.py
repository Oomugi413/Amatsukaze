"""GTK application bootstrap and Wayland diagnostics."""

from __future__ import annotations

import logging
import os
import sys

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

from .api_client import ApiClient, make_loopback_url
from .dto import DEFAULT_REST_PORT
from .log_service import configure_logging
from .main_window import MainWindow
from .settings_service import GuiSettings, load_settings


class LinuxGuiApplication(Gtk.Application):
    def __init__(self, *, settings: GuiSettings, logger: logging.Logger) -> None:
        super().__init__(application_id="jp.amatsukaze.LinuxGUI")
        self.settings = settings
        self.logger = logger
        self.window: MainWindow | None = None

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        display = Gdk.Display.get_default()
        if display is not None:
            self.logger.info("GTK display=%s", display.get_name())
        self.logger.info("GDK_BACKEND=%s WAYLAND_DISPLAY=%s", os.environ.get("GDK_BACKEND", ""), os.environ.get("WAYLAND_DISPLAY", ""))

    def do_activate(self) -> None:
        if self.window is None:
            api = ApiClient(make_loopback_url(self.settings.rest_port))
            self.window = MainWindow(
                self,
                settings=self.settings,
                api=api,
                logger=self.logger,
            )
        self.window.present()


def main(argv: list[str] | None = None) -> int:
    logger = configure_logging()
    settings = load_settings()
    if not settings.rest_port:
        settings.rest_port = DEFAULT_REST_PORT
    logger.info("Amatsukaze Linux GUI起動: port=%s", settings.rest_port)
    application = LinuxGuiApplication(settings=settings, logger=logger)
    return application.run(sys.argv if argv is None else argv)
