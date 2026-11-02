"""Точка входа: python -m p2pshare"""

from __future__ import annotations

import logging
import sys

from PyQt6.QtWidgets import QApplication

from p2pshare.app.controller import ApplicationController
from p2pshare.core.config import AppConfig
from p2pshare.ui.main_window import MainWindow


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main() -> int:
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("P2P Share LAN")
    controller = ApplicationController(AppConfig())
    window = MainWindow(controller)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
