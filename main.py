"""Prompt Vault - entry point."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler


def _setup_logging() -> None:
    from app.utils.paths import log_path
    handler = RotatingFileHandler(log_path(), maxBytes=512_000, backupCount=2, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler],
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> int:
    from PySide6.QtWidgets import QApplication, QMessageBox

    from app import APP_NAME, APP_VERSION
    _setup_logging()
    log = logging.getLogger("main")

    def excepthook(exc_type, exc, tb):
        log.error("Unhandled exception", exc_info=(exc_type, exc, tb))
        try:
            QMessageBox.critical(None, APP_NAME, f"Unexpected error:\n{exc}\n\nDetails were written to the log file.")
        except Exception:
            pass

    sys.excepthook = excepthook
    qapp = QApplication(sys.argv)
    qapp.setApplicationName(APP_NAME)
    qapp.setApplicationVersion(APP_VERSION)
    qapp.setOrganizationName("Sadroddin Aghaei")

    from app.app import AppController
    from app.database.db import DatabaseError
    try:
        controller = AppController(qapp)  # noqa: F841 - keeps the window alive
    except DatabaseError as exc:
        log.exception("Startup failure")
        QMessageBox.critical(None, APP_NAME, f"The database could not be opened.\n{exc}")
        return 1
    if "--smoke-test" in sys.argv:  # used by CI: start, build the UI, exit cleanly
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, qapp.quit)
    return qapp.exec()


if __name__ == "__main__":
    sys.exit(main())
