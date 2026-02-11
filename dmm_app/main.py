import sys

from PySide6.QtWidgets import QApplication

from dmm_app.gui import DMMAppWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = DMMAppWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
