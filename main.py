import sys
from PyQt5.QtWidgets import QApplication
from core.app import ProjectionMapper

def main():
    app = QApplication(sys.argv)
    mapper = ProjectionMapper()
    mapper.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
