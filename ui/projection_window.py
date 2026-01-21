from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QImage, QPainter
import numpy as np
import cv2

class ProjectionWindow(QWidget):
    def __init__(self, renderer, width=1920, height=1080):
        super().__init__()
        self.renderer = renderer

        self.setWindowTitle("BadMapper - Projection Output")
        self.resize(width, height)

        # Update timer for video playback
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(33)  # ~30 FPS

    def update_frame(self):
        self.update()

    def paintEvent(self, event):
        output = self.renderer.get_output()

        if output is not None:
            # Convert BGR to RGB
            rgb = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)

            painter = QPainter(self)
            painter.drawImage(0, 0, qt_image.scaled(self.width(), self.height()))

    def keyPressEvent(self, event):
        from PyQt5.QtCore import Qt
        if event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
