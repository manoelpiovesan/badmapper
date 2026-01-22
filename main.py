import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from core.app import ProjectionMapper

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(__file__)

    return os.path.join(base_path, relative_path)

def main():
    app = QApplication(sys.argv)

    # Set application icon
    icon_path = get_resource_path('assets/favicon.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    mapper = ProjectionMapper()
    mapper.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
