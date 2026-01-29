"""
OpenGL-accelerated projection window with hardware rendering
"""
from PyQt5.QtWidgets import QOpenGLWidget, QWidget
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPainter, QImage
from OpenGL.GL import *
import numpy as np
import cv2


class GLProjectionWindow(QOpenGLWidget):
    """Hardware-accelerated projection window using OpenGL"""

    def __init__(self, renderer, gl_renderer, width=1920, height=1080):
        super().__init__()
        self.renderer = renderer  # Keep CPU renderer for fallback
        self.gl_renderer = gl_renderer
        self.use_opengl = True  # Flag to switch between GL and CPU rendering
        self.masks = []  # Will be set by the app

        self.setWindowTitle("BadMapper - Projection Output (OpenGL)")
        self.resize(width, height)

        # Update timer for video playback
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(16)  # ~60 FPS with OpenGL

    def initializeGL(self):
        """Initialize OpenGL context"""
        try:
            # Make sure context is current
            self.makeCurrent()
            self.gl_renderer.initialize()
            glViewport(0, 0, self.width(), self.height())

            if not self.gl_renderer.initialized:
                print("OpenGL initialization failed, will use CPU fallback")
                self.use_opengl = False
        except Exception as e:
            print(f"Failed to initialize OpenGL: {e}")
            print("Using CPU renderer fallback")
            self.use_opengl = False

    def resizeGL(self, w, h):
        """Handle window resize"""
        glViewport(0, 0, w, h)

    def paintGL(self):
        """Render using OpenGL"""
        if self.use_opengl and self.gl_renderer.initialized:
            try:
                self.gl_renderer.reset_canvas()

                # Render all masks
                for mask in self.masks:
                    if mask.media and not mask.hidden:
                        self.gl_renderer.render_mask(mask)

                # Draw grids if enabled
                if self.gl_renderer.show_grid:
                    for mask in self.masks:
                        if not mask.hidden:
                            self.gl_renderer.draw_grid(mask)
            except Exception as e:
                print(f"OpenGL rendering error: {e}")
                print("Switching to CPU fallback - please restart the application")
                self.use_opengl = False
                # Clear screen on error
                glClearColor(0.0, 0.0, 0.0, 1.0)
                glClear(GL_COLOR_BUFFER_BIT)
        else:
            # Just clear screen if not using OpenGL
            glClearColor(0.0, 0.0, 0.0, 1.0)
            glClear(GL_COLOR_BUFFER_BIT)

    def update_frame(self):
        """Trigger frame update"""
        self.update()

    def keyPressEvent(self, event):
        """Handle keyboard input"""
        if event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
        elif event.key() == Qt.Key_G:
            self.gl_renderer.toggle_grid()
        elif event.key() == Qt.Key_O:
            # Toggle between OpenGL and CPU rendering
            self.use_opengl = not self.use_opengl
            mode = "OpenGL" if self.use_opengl else "CPU"
            self.setWindowTitle(f"BadMapper - Projection Output ({mode})")
