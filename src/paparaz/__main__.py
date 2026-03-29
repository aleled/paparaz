"""Entry point for PapaRaZ."""

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from paparaz.app import PapaRazApp


def main():
    # AA_EnableHighDpiScaling is deprecated in Qt6 (always enabled)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("PapaRaZ")
    app.setApplicationVersion("0.6.0")

    paparaz = PapaRazApp(app)
    paparaz.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
