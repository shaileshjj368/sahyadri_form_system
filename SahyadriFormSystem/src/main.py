from pathlib import Path
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from src.ui.main_window import MainWindow


def app_base_dir() -> Path:
    # Frozen PyInstaller app: keep writable database/PDFs beside the executable.
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def resource_dir() -> Path:
    if getattr(sys, '_MEIPASS', None):
        return Path(sys._MEIPASS)
    return app_base_dir()


def main():
    app = QApplication(sys.argv)
    resources = resource_dir()
    font = resources/'fonts'/'NotoSansDevanagari-Regular.ttf'
    if font.exists(): QFontDatabase.addApplicationFont(str(font))
    app.setStyle('Fusion')
    w = MainWindow(app_base_dir(), resource_dir())
    w.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
