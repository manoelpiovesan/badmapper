import numpy as np
import cv2
from enum import Enum

class MaskType(Enum):
    RECTANGLE = "rectangle"
    TRIANGLE = "triangle"
    SPHERE = "sphere"

class Mask:
    def __init__(self, mask_type, width=400, height=300, position=(100, 100)):
        self.mask_type = mask_type
        self.width = width
        self.height = height
        self.position = position
        self.media = None
        self.media_transform = MediaTransform()

        # Transformações da máscara
        self.rotation = 0.0
        self.scale = 1.0

        if mask_type == MaskType.RECTANGLE:
            self.vertices = self._create_rectangle()
        elif mask_type == MaskType.TRIANGLE:
            self.vertices = self._create_triangle()
        elif mask_type == MaskType.SPHERE:
            self.vertices = self._create_rectangle()

        self.original_vertices = self.vertices.copy()

    def _create_rectangle(self):
        x, y = self.position
        return np.array([
            [x, y],
            [x + self.width, y],
            [x + self.width, y + self.height],
            [x, y + self.height]
        ], dtype=np.float32)

    def _create_triangle(self):
        x, y = self.position
        return np.array([
            [x + self.width / 2, y],
            [x + self.width, y + self.height],
            [x, y + self.height]
        ], dtype=np.float32)

    def get_center(self):
        return np.mean(self.vertices, axis=0)

    def set_vertex(self, index, point):
        self.vertices[index] = point

    def translate(self, dx, dy):
        self.vertices += np.array([dx, dy])

    def rotate_mask(self, angle_delta):
        """Rotaciona a máscara por um delta de ângulo, preservando perspectiva"""
        self.rotation += angle_delta
        center = self.get_center()

        # Converter ângulo para radianos
        angle_rad = np.radians(angle_delta)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)

        # Matriz de rotação
        rotation_matrix = np.array([
            [cos_a, -sin_a],
            [sin_a, cos_a]
        ])

        # Aplicar rotação nos vértices atuais (preserva perspectiva)
        vertices_centered = self.vertices - center
        vertices_rotated = vertices_centered @ rotation_matrix.T
        self.vertices = (vertices_rotated + center).astype(np.float32)

    def scale_mask(self, scale_delta):
        """Escala a máscara por um delta de escala, preservando perspectiva"""
        new_scale = max(0.1, 1.0 + scale_delta)
        self.scale *= new_scale
        center = self.get_center()

        # Aplicar escala nos vértices atuais (preserva perspectiva)
        vertices_centered = self.vertices - center
        vertices_scaled = vertices_centered * new_scale
        self.vertices = (vertices_scaled + center).astype(np.float32)

    def reset_transform(self):
        """Reseta rotação e escala da máscara"""
        self.rotation = 0.0
        self.scale = 1.0
        self.vertices = self.original_vertices.copy()

    def get_bounds(self):
        min_x = np.min(self.vertices[:, 0])
        min_y = np.min(self.vertices[:, 1])
        max_x = np.max(self.vertices[:, 0])
        max_y = np.max(self.vertices[:, 1])
        return min_x, min_y, max_x, max_y

class MediaTransform:
    def __init__(self):
        self.offset_x = 0
        self.offset_y = 0
        self.scale = 1.0
        self.rotation = 0.0
        self.perspective_points = None

    def reset(self):
        self.offset_x = 0
        self.offset_y = 0
        self.scale = 1.0
        self.rotation = 0.0
        self.perspective_points = None
