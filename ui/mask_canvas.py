from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush
import numpy as np


class MaskCanvas(QWidget):
    """Canvas widget for drawing and editing masks"""

    def __init__(self, control_window, parent=None):
        super().__init__(parent)
        self.control_window = control_window
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(0, 0, self.width(), self.height(), QColor(30, 30, 30))

        for mask in self.control_window.masks:
            # Skip hidden masks
            if mask.hidden:
                continue
            self.control_window._draw_mask_grid(painter, mask)

        # Draw Ctrl mode indicator
        if self.control_window.ctrl_pressed:
            painter.setPen(QPen(QColor(255, 200, 0), 2))
            painter.setBrush(QBrush(QColor(255, 200, 0, 100)))
            painter.drawRect(10, 10, 200, 30)
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(20, 30, "MEDIA MODE (Ctrl active)")

        # Draw zoom indicator (top left corner)
        if self.control_window.view_zoom != 1.0 or self.control_window.view_offset_x != 0 or self.control_window.view_offset_y != 0:
            painter.setPen(QPen(QColor(100, 200, 255), 2))
            painter.setBrush(QBrush(QColor(100, 200, 255, 100)))
            painter.drawRect(10, 50, 150, 30)
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(20, 70, f"Zoom: {self.control_window.view_zoom:.2f}x")

        # Draw edit mode indicator (bottom left corner)
        self.control_window._draw_edit_mode_indicator(painter)

        # Draw help overlay
        if self.control_window.show_help:
            painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
            painter.setPen(QPen(QColor(100, 100, 100)))
            help_w, help_h = 400, 500
            help_x = self.width() - help_w - 20
            help_y = 20
            painter.drawRect(help_x, help_y, help_w, help_h)

            painter.setPen(QPen(QColor(255, 255, 255)))
            y_offset = help_y + 25
            line_height = 20

            painter.drawText(help_x + 10, y_offset, "SHORTCUTS:")
            y_offset += line_height + 5

            painter.setPen(QPen(QColor(200, 200, 200)))
            painter.drawText(help_x + 10, y_offset, "• Drag vertex: adjust perspective")
            y_offset += line_height
            painter.drawText(help_x + 10, y_offset, "• Drag mask: move")
            y_offset += line_height
            painter.drawText(help_x + 10, y_offset, "• P: toggle Performance mode")
            y_offset += line_height
            painter.drawText(help_x + 10, y_offset, "• 0-9: switch scenes (Performance)")
            y_offset += line_height
            painter.drawText(help_x + 10, y_offset, "• 1: Rotate (Edit mode)")
            y_offset += line_height
            painter.drawText(help_x + 10, y_offset, "• 2: Move (Edit mode)")
            y_offset += line_height
            painter.drawText(help_x + 10, y_offset, "• 3: Scale (Edit mode)")
            y_offset += line_height
            painter.drawText(help_x + 10, y_offset, "• 4: Perspective (Edit mode)")
            y_offset += line_height
            painter.drawText(help_x + 10, y_offset, "• Delete: remove selected mask")
            y_offset += line_height
            painter.drawText(help_x + 10, y_offset, "• R: replace media")
            y_offset += line_height
            painter.drawText(help_x + 10, y_offset, "• F11: fullscreen projection")
            y_offset += line_height
            painter.drawText(help_x + 10, y_offset, "• G: toggle grid (projection)")
            y_offset += line_height
            painter.drawText(help_x + 10, y_offset, "• H: hide/show help")
            y_offset += line_height
            painter.drawText(help_x + 10, y_offset, "• . (period): zoom in (navigation)")
            y_offset += line_height
            painter.drawText(help_x + 10, y_offset, "• , (comma): zoom out (navigation)")
            y_offset += line_height
            painter.drawText(help_x + 10, y_offset, "• Arrow keys: pan view (navigation)")
            y_offset += line_height

    def mousePressEvent(self, event):
        self.control_window.mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.control_window.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.control_window.mouseReleaseEvent(event)

    def wheelEvent(self, event):
        self.control_window.wheelEvent(event)
