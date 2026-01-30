from PyQt5.QtWidgets import QWidget, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPainter, QColor, QPen, QBrush, QFont
import numpy as np
from enum import Enum
from ui.mask_list_widget import MaskListWidget
from ui.project_list_widget import ProjectListWidget
from ui.mask_canvas import MaskCanvas

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
    project_selected = pyqtSignal(str, str)  # Emits (file_path, project_name)
    add_project_requested = pyqtSignal()

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

        # View navigation (zoom and pan) - does not affect projection
        self.view_zoom = 1.0
        self.view_offset_x = 0.0
        self.view_offset_y = 0.0
        self.pan_speed = 20  # pixels per key press

        # Create layout with sidebar
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create mask list sidebar (left)
        self.mask_list_widget = MaskListWidget(self.masks)
        self.mask_list_widget.mask_selected.connect(self._on_sidebar_mask_selected)
        main_layout.addWidget(self.mask_list_widget)

        # Create canvas
        self.canvas = MaskCanvas(self)
        main_layout.addWidget(self.canvas)

        # Create project list sidebar (right)
        self.project_list_widget = ProjectListWidget()
        self.project_list_widget.project_selected.connect(self._on_project_selected)
        self.project_list_widget.add_project_requested.connect(self._on_add_project_requested)
        main_layout.addWidget(self.project_list_widget)

        self.setLayout(main_layout)

        # Update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(33)  # ~30 FPS

    def _on_sidebar_mask_selected(self, mask):
        """Handle mask selection from sidebar"""
        self.selected_mask = mask
        self.canvas.setFocus()

    def _on_project_selected(self, file_path, project_name):
        """Handle project selection from sidebar"""
        self.project_selected.emit(file_path, project_name)

    def _on_add_project_requested(self):
        """Handle add project request from sidebar"""
        self.add_project_requested.emit()

    def set_masks(self, masks):
        """Update the masks list reference (used when switching projects)"""
        self.masks = masks
        self.mask_list_widget.masks = masks
        self.refresh_mask_list()

    def refresh_mask_list(self):
        """Refresh the sidebar mask list"""
        self.mask_list_widget.refresh()
        if self.selected_mask:
            self.mask_list_widget.set_selected_mask(self.selected_mask)

    def _transform_point_to_view(self, point):
        """Transform a point from world space to view space (with zoom and pan)"""
        x, y = point
        view_x = (x + self.view_offset_x) * self.view_zoom
        view_y = (y + self.view_offset_y) * self.view_zoom
        return np.array([view_x, view_y])

    def _transform_point_from_view(self, point):
        """Transform a point from view space back to world space"""
        x, y = point
        world_x = x / self.view_zoom - self.view_offset_x
        world_y = y / self.view_zoom - self.view_offset_y
        return np.array([world_x, world_y])

    def _draw_mask_grid(self, painter, mask):
        is_selected = (mask == self.selected_mask)

        # Draw grid lines
        if is_selected:
            pen = QPen(QColor(0, 200, 255), 2)
        else:
            pen = QPen(QColor(100, 100, 100), 1)
        painter.setPen(pen)

        # Apply view transformation to vertices
        vertices_transformed = np.array([self._transform_point_to_view(v) for v in mask.vertices]).astype(int)

        # Draw polygon
        for i in range(len(vertices_transformed)):
            p1 = vertices_transformed[i]
            p2 = vertices_transformed[(i + 1) % len(vertices_transformed)]
            painter.drawLine(p1[0], p1[1], p2[0], p2[1])

        # Draw grid inside mask
        self._draw_internal_grid(painter, mask, 10, 10)

        # Draw vertices
        for i, vertex in enumerate(vertices_transformed):
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
            center_transformed = self._transform_point_to_view(center)
            button_size = 80 * self.view_zoom
            button_height = 40 * self.view_zoom
            painter.setBrush(QBrush(QColor(50, 150, 50, 180)))
            painter.setPen(QPen(QColor(100, 255, 100), 2))
            painter.drawRect(int(center_transformed[0] - button_size/2),
                           int(center_transformed[1] - button_height/2),
                           int(button_size), int(button_height))
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(int(center_transformed[0] - button_size/2 + 5),
                           int(center_transformed[1] + 5), "Select Media")

    def _draw_internal_grid(self, painter, mask, rows, cols):
        pen = QPen(QColor(70, 70, 70), 1, Qt.DashLine)
        painter.setPen(pen)

        vertices = mask.vertices
        if len(vertices) < 3:
            return

        # For triangles: interpolate grid from top to base
        if len(vertices) == 3:
            # Assume triangle vertices: [top, bottom-right, bottom-left]
            top = vertices[0]
            bottom_right = vertices[1]
            bottom_left = vertices[2]

            # Draw horizontal lines from left edge to right edge
            for i in range(1, rows):
                t = i / rows
                # Interpolate along left and right edges
                p_left = top * (1 - t) + bottom_left * t
                p_right = top * (1 - t) + bottom_right * t
                p_left_view = self._transform_point_to_view(p_left)
                p_right_view = self._transform_point_to_view(p_right)
                painter.drawLine(int(p_left_view[0]), int(p_left_view[1]),
                               int(p_right_view[0]), int(p_right_view[1]))

            # Draw vertical-ish lines from top to base
            for j in range(1, cols):
                t = j / cols
                # Point on the base
                p_base = bottom_left * (1 - t) + bottom_right * t
                top_view = self._transform_point_to_view(top)
                p_base_view = self._transform_point_to_view(p_base)
                painter.drawLine(int(top_view[0]), int(top_view[1]),
                               int(p_base_view[0]), int(p_base_view[1]))

        # For quad/rectangle: interpolate grid
        elif len(vertices) >= 4:
            for i in range(1, rows):
                t = i / rows
                p1 = vertices[0] * (1 - t) + vertices[3] * t
                p2 = vertices[1] * (1 - t) + vertices[2] * t
                p1_view = self._transform_point_to_view(p1)
                p2_view = self._transform_point_to_view(p2)
                painter.drawLine(int(p1_view[0]), int(p1_view[1]),
                               int(p2_view[0]), int(p2_view[1]))

            for j in range(1, cols):
                t = j / cols
                p1 = vertices[0] * (1 - t) + vertices[1] * t
                p2 = vertices[3] * (1 - t) + vertices[2] * t
                p1_view = self._transform_point_to_view(p1)
                p2_view = self._transform_point_to_view(p2)
                painter.drawLine(int(p1_view[0]), int(p1_view[1]),
                               int(p2_view[0]), int(p2_view[1]))

    def mousePressEvent(self, event):
        # Ensure focus to receive keyboard events
        self.canvas.setFocus()

        if event.button() == Qt.LeftButton:
            pos_view = np.array([event.x(), event.y()])
            pos = self._transform_point_from_view(pos_view)

            # Check if clicking add media button
            for mask in self.masks:
                if mask.hidden or mask.locked:  # Skip hidden or locked masks
                    continue
                if mask.media is None:
                    center = mask.get_center()
                    if abs(pos[0] - center[0]) < 40 and abs(pos[1] - center[1]) < 20:
                        self.media_requested.emit(mask)
                        return

            # Ctrl + drag for media transformation
            if self.ctrl_pressed:
                for mask in self.masks:
                    if mask.hidden or mask.locked:  # Skip hidden or locked masks
                        continue
                    if mask.media and self._point_in_polygon(pos, mask.vertices):
                        self.media_transform_mode = True
                        self.dragging_mask = mask
                        self.selected_mask = mask
                        self.mask_list_widget.set_selected_mask(mask)
                        self.media_drag_start = pos.copy()
                        self.media_initial_offset = np.array([mask.media_transform.offset_x,
                                                              mask.media_transform.offset_y])
                        return

            # Check if clicking on vertex
            for mask in self.masks:
                if mask.hidden or mask.locked:  # Skip hidden or locked masks
                    continue
                for i, vertex in enumerate(mask.vertices):
                    dist = np.linalg.norm(pos - vertex)
                    if dist < 10:
                        self.dragging_vertex = i
                        self.dragging_mask = mask
                        self.selected_mask = mask
                        self.mask_list_widget.set_selected_mask(mask)
                        self.drag_start = pos.copy()
                        return

            # Check if clicking inside mask
            for mask in self.masks:
                if mask.hidden or mask.locked:  # Skip hidden or locked masks
                    continue
                if self._point_in_polygon(pos, mask.vertices):
                    self.dragging_mask = mask
                    self.selected_mask = mask
                    self.mask_list_widget.set_selected_mask(mask)
                    self.drag_start = pos.copy()
                    return

    def mouseMoveEvent(self, event):
        pos_view = np.array([event.x(), event.y()])
        pos = self._transform_point_from_view(pos_view)

        # Update hover state (skip hidden masks)
        self.hover_vertex = None
        self.hover_mask = None
        for mask in self.masks:
            if mask.hidden:  # Skip hidden masks
                continue
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
        elif event.key() == Qt.Key_Period:  # . key for zoom in
            self.view_zoom *= 1.1
            self.update()
        elif event.key() == Qt.Key_Comma:  # , key for zoom out
            self.view_zoom *= 0.9
            self.update()
        elif event.key() == Qt.Key_Left:  # Pan left
            self.view_offset_x += self.pan_speed / self.view_zoom
            self.update()
        elif event.key() == Qt.Key_Right:  # Pan right
            self.view_offset_x -= self.pan_speed / self.view_zoom
            self.update()
        elif event.key() == Qt.Key_Up:  # Pan up
            self.view_offset_y += self.pan_speed / self.view_zoom
            self.update()
        elif event.key() == Qt.Key_Down:  # Pan down
            self.view_offset_y -= self.pan_speed / self.view_zoom
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
        box_height = 65
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
        painter.drawText(box_x + 10, box_y + 22, f"{self.edit_target.value} Mode")

        # Edit type text
        font.setPointSize(12)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 100)))
        painter.drawText(box_x + 10, box_y + 45, f"{self.edit_type.label}")

        # Controls
        font.setBold(False)
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QPen(QColor(220, 220, 220)))

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
