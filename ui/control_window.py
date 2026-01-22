from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPainter, QColor, QPen, QBrush, QFont
import numpy as np
from enum import Enum

class EditTarget(Enum):
    MASK = "Mask"
    MEDIA = "Media"

class EditType(Enum):
    ROTATE = (1, "Rotate")
    MOVE = (2, "Move")
    SCALE = (3, "Scale")
    PERSPECTIVE = (4, "Perspective")

    def __init__(self, num, label):
        self.num = num
        self.label = label

class ControlWindow(QWidget):
    media_requested = pyqtSignal(object)
    mask_delete_requested = pyqtSignal(object)
    media_replace_requested = pyqtSignal(object)

    def __init__(self, masks, width=1024, height=768):
        super().__init__()
        self.masks = masks
        self.canvas_width = width
        self.canvas_height = height

        self.setWindowTitle("BadMapper - Editor")
        self.resize(width, height)

        self.dragging_vertex = None
        self.dragging_mask = None
        self.drag_start = None
        self.selected_mask = None
        self.hover_vertex = None
        self.hover_mask = None

        self.ctrl_pressed = False
        self.media_transform_mode = False
        self.media_drag_start = None
        self.media_initial_offset = None
        self.show_help = True

        # Edit mode (Mask or Media)
        self.edit_target = EditTarget.MASK
        # Edit type selected (1-4)
        self.edit_type = EditType.MOVE

        self.setMouseTracking(True)

        # Allow focus to receive keyboard events
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

        # Update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(33)  # ~30 FPS

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(0, 0, self.width(), self.height(), QColor(30, 30, 30))

        for mask in self.masks:
            self._draw_mask_grid(painter, mask)

        # Draw Ctrl mode indicator
        if self.ctrl_pressed:
            painter.setPen(QPen(QColor(255, 200, 0), 2))
            painter.setBrush(QBrush(QColor(255, 200, 0, 100)))
            painter.drawRect(10, 10, 200, 30)
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(20, 30, "MEDIA MODE (Ctrl active)")

        # Draw edit mode indicator (bottom left corner)
        self._draw_edit_mode_indicator(painter)

        # Draw help overlay
        if self.show_help:
            painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
            painter.setPen(QPen(QColor(100, 100, 100)))
            help_w, help_h = 400, 340
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
            painter.drawText(help_x + 10, y_offset, "• Ctrl + Drag: move media")
            y_offset += line_height
            painter.drawText(help_x + 10, y_offset, "• Ctrl + Scroll: scale media")
            y_offset += line_height
            painter.drawText(help_x + 10, y_offset, "• Shift + Scroll: rotate media")
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
            y_offset += line_height + 10

            painter.setPen(QPen(QColor(150, 150, 150)))
            painter.drawText(help_x + 10, y_offset, "Press H to hide")

    def _draw_mask_grid(self, painter, mask):
        is_selected = (mask == self.selected_mask)

        # Draw grid lines
        if is_selected:
            pen = QPen(QColor(0, 200, 255), 2)
        else:
            pen = QPen(QColor(100, 100, 100), 1)
        painter.setPen(pen)

        vertices = mask.vertices.astype(int)

        # Draw polygon
        for i in range(len(vertices)):
            p1 = vertices[i]
            p2 = vertices[(i + 1) % len(vertices)]
            painter.drawLine(p1[0], p1[1], p2[0], p2[1])

        # Draw grid inside mask
        self._draw_internal_grid(painter, mask, 10, 10)

        # Draw vertices
        for i, vertex in enumerate(vertices):
            is_hover = (self.hover_vertex == i and self.hover_mask == mask)
            if is_hover:
                painter.setBrush(QBrush(QColor(255, 200, 0)))
                painter.setPen(QPen(QColor(255, 255, 0), 2))
                painter.drawEllipse(vertex[0] - 6, vertex[1] - 6, 12, 12)
            else:
                painter.setBrush(QBrush(QColor(0, 200, 255) if is_selected else QColor(150, 150, 150)))
                painter.setPen(QPen(QColor(255, 255, 255), 1))
                painter.drawEllipse(vertex[0] - 5, vertex[1] - 5, 10, 10)

        # Draw add media button if no media
        if mask.media is None:
            center = mask.get_center()
            painter.setBrush(QBrush(QColor(50, 150, 50, 180)))
            painter.setPen(QPen(QColor(100, 255, 100), 2))
            painter.drawRect(int(center[0] - 40), int(center[1] - 20), 80, 40)
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(int(center[0] - 35), int(center[1] + 5), "Select Media")

    def _draw_internal_grid(self, painter, mask, rows, cols):
        pen = QPen(QColor(70, 70, 70), 1, Qt.DashLine)
        painter.setPen(pen)

        vertices = mask.vertices
        if len(vertices) < 3:
            return

        # For quad/rectangle: interpolate grid
        if len(vertices) >= 4:
            for i in range(1, rows):
                t = i / rows
                p1 = vertices[0] * (1 - t) + vertices[3] * t
                p2 = vertices[1] * (1 - t) + vertices[2] * t
                painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))

            for j in range(1, cols):
                t = j / cols
                p1 = vertices[0] * (1 - t) + vertices[1] * t
                p2 = vertices[3] * (1 - t) + vertices[2] * t
                painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))

    def mousePressEvent(self, event):
        # Ensure focus to receive keyboard events
        self.setFocus()

        if event.button() == Qt.LeftButton:
            pos = np.array([event.x(), event.y()])

            # Check if clicking add media button
            for mask in self.masks:
                if mask.media is None:
                    center = mask.get_center()
                    if abs(pos[0] - center[0]) < 40 and abs(pos[1] - center[1]) < 20:
                        self.media_requested.emit(mask)
                        return

            # Ctrl + drag for media transformation
            if self.ctrl_pressed:
                for mask in self.masks:
                    if mask.media and self._point_in_polygon(pos, mask.vertices):
                        self.media_transform_mode = True
                        self.dragging_mask = mask
                        self.selected_mask = mask
                        self.media_drag_start = pos.copy()
                        self.media_initial_offset = np.array([mask.media_transform.offset_x,
                                                              mask.media_transform.offset_y])
                        return

            # Check if clicking on vertex
            for mask in self.masks:
                for i, vertex in enumerate(mask.vertices):
                    dist = np.linalg.norm(pos - vertex)
                    if dist < 10:
                        self.dragging_vertex = i
                        self.dragging_mask = mask
                        self.selected_mask = mask
                        self.drag_start = pos.copy()
                        return

            # Check if clicking inside mask
            for mask in self.masks:
                if self._point_in_polygon(pos, mask.vertices):
                    self.dragging_mask = mask
                    self.selected_mask = mask
                    self.drag_start = pos.copy()
                    return

    def mouseMoveEvent(self, event):
        pos = np.array([event.x(), event.y()])

        # Update hover state
        self.hover_vertex = None
        self.hover_mask = None
        for mask in self.masks:
            for i, vertex in enumerate(mask.vertices):
                dist = np.linalg.norm(pos - vertex)
                if dist < 10:
                    self.hover_vertex = i
                    self.hover_mask = mask
                    break

        # Handle dragging
        if self.dragging_mask and self.drag_start is not None:
            delta = pos - self.drag_start

            # Check if editing media or mask
            if self.edit_target == EditTarget.MEDIA and self.dragging_mask.media:
                self._apply_media_edit(delta, pos)
            else:
                self._apply_mask_edit(delta, pos)

            self.drag_start = pos.copy()

    def _apply_mask_edit(self, delta, pos):
        """Apply edit to mask based on selected type"""
        mask = self.dragging_mask

        if self.edit_type == EditType.ROTATE:
            # Rotation based on horizontal movement
            angle_delta = delta[0] * 0.5
            mask.rotate_mask(angle_delta)

        elif self.edit_type == EditType.MOVE:
            if self.dragging_vertex is not None:
                # If dragging vertex, move only the vertex
                mask.set_vertex(self.dragging_vertex, pos)
            else:
                # Move the entire mask
                mask.translate(delta[0], delta[1])

        elif self.edit_type == EditType.SCALE:
            # Scale based on vertical movement (up = larger)
            scale_delta = -delta[1] * 0.005
            mask.scale_mask(scale_delta)

        elif self.edit_type == EditType.PERSPECTIVE:
            # Perspective - move only the closest vertex
            if self.dragging_vertex is not None:
                mask.set_vertex(self.dragging_vertex, pos)
            else:
                # Find closest vertex to drag start
                closest_idx = 0
                min_dist = float('inf')
                for i, v in enumerate(mask.vertices):
                    d = np.linalg.norm(self.drag_start - v)
                    if d < min_dist:
                        min_dist = d
                        closest_idx = i
                new_pos = mask.vertices[closest_idx] + delta
                mask.set_vertex(closest_idx, new_pos)

    def _apply_media_edit(self, delta, pos):
        """Apply edit to media based on selected type"""
        transform = self.dragging_mask.media_transform

        if self.edit_type == EditType.ROTATE:
            # Rotation based on horizontal movement
            angle_delta = delta[0] * 0.5
            transform.rotation += angle_delta

        elif self.edit_type == EditType.MOVE:
            # Move media
            transform.offset_x += delta[0]
            transform.offset_y += delta[1]

        elif self.edit_type == EditType.SCALE:
            # Scale based on vertical movement
            scale_delta = -delta[1] * 0.005
            transform.scale = max(0.1, transform.scale + scale_delta)

        elif self.edit_type == EditType.PERSPECTIVE:
            # For media, perspective works as move for now
            transform.offset_x += delta[0]
            transform.offset_y += delta[1]

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging_vertex = None
            self.dragging_mask = None
            self.drag_start = None
            self.media_transform_mode = False
            self.media_drag_start = None
            self.media_initial_offset = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.ctrl_pressed = True
        elif event.key() == Qt.Key_H:
            self.show_help = not self.show_help
            self.update()
        elif event.key() == Qt.Key_E:
            # Toggle edit target (Mask/Media)
            if self.edit_target == EditTarget.MASK:
                self.edit_target = EditTarget.MEDIA
            else:
                self.edit_target = EditTarget.MASK
            self.update()
        elif event.key() == Qt.Key_1:
            self.edit_type = EditType.ROTATE
            self.update()
        elif event.key() == Qt.Key_2:
            self.edit_type = EditType.MOVE
            self.update()
        elif event.key() == Qt.Key_3:
            self.edit_type = EditType.SCALE
            self.update()
        elif event.key() == Qt.Key_4:
            self.edit_type = EditType.PERSPECTIVE
            self.update()
        elif event.key() == Qt.Key_Delete:
            if self.selected_mask:
                self.mask_delete_requested.emit(self.selected_mask)
        elif event.key() == Qt.Key_R:
            if self.selected_mask:
                self.media_replace_requested.emit(self.selected_mask)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.ctrl_pressed = False

    def _draw_edit_mode_indicator(self, painter):
        """Draw edit mode indicator in the bottom left corner"""
        # Indicator background
        box_width = 350
        box_height = 100
        box_x = 10
        box_y = self.height() - box_height - 10

        # Color based on edit target
        if self.edit_target == EditTarget.MASK:
            bg_color = QColor(0, 100, 200, 200)
            border_color = QColor(0, 150, 255)
        else:
            bg_color = QColor(200, 100, 0, 200)
            border_color = QColor(255, 150, 0)

        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 2))
        painter.drawRoundedRect(box_x, box_y, box_width, box_height, 5, 5)

        # Target text
        painter.setPen(QPen(QColor(255, 255, 255)))
        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        painter.setFont(font)
        painter.drawText(box_x + 10, box_y + 22, f"Target: {self.edit_target.value}")

        # Edit type text
        font.setPointSize(12)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 100)))
        painter.drawText(box_x + 10, box_y + 45, f"Edit: {self.edit_type.label}")

        # Controls
        font.setBold(False)
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QPen(QColor(220, 220, 220)))

        # Show keys with highlight on selected
        edit_types_text = ""
        for et in EditType:
            if et == self.edit_type:
                edit_types_text += f"[{et.num}:{et.label}] "
            else:
                edit_types_text += f"{et.num}:{et.label} "

        painter.drawText(box_x + 10, box_y + 65, edit_types_text)
        painter.drawText(box_x + 10, box_y + 85, "E: Toggle Mask/Media")

        # Selected mask info
        if self.selected_mask:
            info_x = box_x + box_width + 10
            painter.setPen(QPen(QColor(150, 150, 150)))
            if self.edit_target == EditTarget.MASK:
                painter.drawText(info_x, box_y + 25, f"Rot: {self.selected_mask.rotation:.1f}°")
                painter.drawText(info_x, box_y + 45, f"Scale: {self.selected_mask.scale:.2f}")
            elif self.selected_mask.media:
                painter.drawText(info_x, box_y + 25, f"Rot: {self.selected_mask.media_transform.rotation:.1f}°")
                painter.drawText(info_x, box_y + 45, f"Scale: {self.selected_mask.media_transform.scale:.2f}")

    def wheelEvent(self, event):
        if self.ctrl_pressed and self.selected_mask and self.selected_mask.media:
            # Ctrl + Scroll = Scale media
            delta = event.angleDelta().y()
            scale_factor = 1.05 if delta > 0 else 0.95
            self.selected_mask.media_transform.scale *= scale_factor
            self.update()
        elif event.modifiers() & Qt.ShiftModifier and self.selected_mask and self.selected_mask.media:
            # Shift + Scroll = Rotate media
            delta = event.angleDelta().y()
            rotation_delta = 5 if delta > 0 else -5
            self.selected_mask.media_transform.rotation += rotation_delta
            self.update()

    def _point_in_polygon(self, point, vertices):
        x, y = point
        n = len(vertices)
        inside = False

        p1x, p1y = vertices[0]
        for i in range(n + 1):
            p2x, p2y = vertices[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside
