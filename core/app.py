from PyQt5.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QMenuBar, QMenu, QAction
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QIcon
from core.mask import Mask, MaskType
from core.media import Media
from core.renderer import Renderer
from core.project import ProjectSerializer
from ui.control_window import ControlWindow
from ui.projection_window import ProjectionWindow
import os
import sys

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(__file__))

    return os.path.join(base_path, relative_path)

class ProjectionMapper(QMainWindow):
    def __init__(self):
        super().__init__()

        self.projection_width = 1920
        self.projection_height = 1080

        self.masks = []
        self.renderer = Renderer(self.projection_width, self.projection_height)
        self.current_file = None  # Track current project file

        self.init_ui()

        # Create initial mask after UI is ready
        self.create_initial_mask()

        # Select first mask by default
        if self.masks:
            self.control_window.selected_mask = self.masks[0]

        # Refresh mask list to show initial mask
        self.control_window.refresh_mask_list()

    def init_ui(self):
        self.setWindowTitle("BadMapper - Editor")

        # Set initial window size to match projection window
        self.resize(self.projection_width, self.projection_height)

        # Set window icon
        icon_path = get_resource_path('assets/favicon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Create menu bar
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('File')

        new_action = QAction('New Project', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)

        open_action = QAction('Open Project...', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction('Save Project', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        save_as_action = QAction('Save Project As...', self)
        save_as_action.setShortcut('Ctrl+Shift+S')
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        add_mask_action = QAction('New Mask', self)
        add_mask_action.triggered.connect(self.add_mask_dialog)
        file_menu.addAction(add_mask_action)

        add_webcam_action = QAction('Add Webcam to Mask', self)
        add_webcam_action.triggered.connect(self.add_webcam_to_selected_mask)
        file_menu.addAction(add_webcam_action)

        file_menu.addSeparator()

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu('View')

        toggle_projection_action = QAction('Projection Window', self)
        toggle_projection_action.triggered.connect(self.toggle_projection_window)
        view_menu.addAction(toggle_projection_action)

        fullscreen_action = QAction('Projection Fullscreen (F11)', self)
        fullscreen_action.triggered.connect(self.toggle_projection_fullscreen)
        view_menu.addAction(fullscreen_action)

        # Control window
        self.control_window = ControlWindow(self.masks)
        self.control_window.media_requested.connect(self.add_media_to_mask)
        self.control_window.mask_delete_requested.connect(self.delete_mask)
        self.control_window.media_replace_requested.connect(self.replace_media)
        self.setCentralWidget(self.control_window)

        # Projection window
        self.projection_window = ProjectionWindow(self.renderer,
                                                   self.projection_width,
                                                   self.projection_height)
        self.projection_window.show()

        # Render timer
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(self.render_frame)
        self.render_timer.start(33)  # ~30 FPS

    def create_initial_mask(self):
        mask = Mask(MaskType.RECTANGLE, 600, 400, (200, 200))
        self.masks.append(mask)

    def add_mask_dialog(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QRadioButton, QPushButton

        dialog = QDialog(self)
        dialog.setWindowTitle("Choose mask type")
        layout = QVBoxLayout()

        rect_radio = QRadioButton("Rectangle")
        rect_radio.setChecked(True)
        tri_radio = QRadioButton("Triangle")
        sphere_radio = QRadioButton("Sphere (2D)")

        layout.addWidget(rect_radio)
        layout.addWidget(tri_radio)
        layout.addWidget(sphere_radio)

        ok_button = QPushButton("Create")
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button)

        dialog.setLayout(layout)

        if dialog.exec_():
            if rect_radio.isChecked():
                mask_type = MaskType.RECTANGLE
            elif tri_radio.isChecked():
                mask_type = MaskType.TRIANGLE
            else:
                mask_type = MaskType.SPHERE

            mask = Mask(mask_type, 400, 300, (100, 100))
            self.masks.append(mask)
            self.control_window.refresh_mask_list()

    def add_media_to_mask(self, mask):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Media",
            "",
            "Media Files (*.jpg *.jpeg *.png *.bmp *.mp4 *.avi *.mov *.mkv *.webm)"
        )

        if file_path:
            try:
                media = Media(file_path)
                mask.media = media
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load media: {str(e)}")

    def add_webcam_to_selected_mask(self):
        """Add webcam to the currently selected mask"""
        if not self.control_window.selected_mask:
            QMessageBox.warning(self, "No Mask Selected", "Please select a mask first.")
            return

        self.add_webcam_to_mask(self.control_window.selected_mask)

    def add_webcam_to_mask(self, mask):
        """Add webcam as media source to a mask"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QSpinBox, QPushButton, QHBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("Select Webcam")
        layout = QVBoxLayout()

        # Webcam index selection
        label = QLabel("Select webcam index (usually 0 for default camera):")
        layout.addWidget(label)

        spinbox = QSpinBox()
        spinbox.setMinimum(0)
        spinbox.setMaximum(10)
        spinbox.setValue(0)
        layout.addWidget(spinbox)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)

        if dialog.exec_():
            webcam_index = spinbox.value()
            try:
                # Release old media if any
                if mask.media:
                    mask.media.release()

                # Create webcam media
                media = Media(path="", is_webcam=True, webcam_index=webcam_index)
                mask.media = media
                QMessageBox.information(self, "Success", f"Webcam {webcam_index} added successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open webcam: {str(e)}")

    def delete_mask(self, mask):
        """Delete the selected mask"""
        if mask in self.masks:
            # Release media resources if any
            if mask.media:
                mask.media.release()

            # Remove from masks list
            self.masks.remove(mask)

            # Clear selection if deleted mask was selected
            if self.control_window.selected_mask == mask:
                self.control_window.selected_mask = None
                # Select first mask if any remain
                if self.masks:
                    self.control_window.selected_mask = self.masks[0]

            # Refresh sidebar
            self.control_window.refresh_mask_list()

    def replace_media(self, mask):
        """Replace media in the selected mask"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Replace Media",
            "",
            "Media Files (*.jpg *.jpeg *.png *.bmp *.mp4 *.avi *.mov *.mkv *.webm)"
        )

        if file_path:
            try:
                # Release old media if any
                if mask.media:
                    mask.media.release()

                # Load new media
                media = Media(file_path)
                mask.media = media

                # Reset media transform
                mask.media_transform.reset()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load media: {str(e)}")

    def render_frame(self):
        self.renderer.reset_canvas()

        for mask in self.masks:
            if mask.media:
                self.renderer.render_mask(mask)

        # Draw grids if enabled
        if self.renderer.show_grid:
            for mask in self.masks:
                self.renderer.draw_grid(mask)

        self.projection_window.update()

    def toggle_projection_window(self):
        if self.projection_window.isVisible():
            self.projection_window.hide()
        else:
            self.projection_window.show()

    def toggle_projection_fullscreen(self):
        if self.projection_window.isFullScreen():
            self.projection_window.showNormal()
        else:
            self.projection_window.showFullScreen()

    def keyPressEvent(self, event):
        # F11 for fullscreen
        if event.key() == Qt.Key_F11:
            self.toggle_projection_fullscreen()
        else:
            # Pass keyboard events to control_window
            self.control_window.keyPressEvent(event)

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        # Pass keyboard events to control_window
        self.control_window.keyReleaseEvent(event)
        super().keyReleaseEvent(event)

    def new_project(self):
        """Create a new project"""
        reply = QMessageBox.question(
            self,
            'New Project',
            'Are you sure you want to create a new project? Any unsaved changes will be lost.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Clean up existing masks
            for mask in self.masks:
                if mask.media:
                    mask.media.release()

            # Reset project
            self.masks.clear()
            self.current_file = None
            self.create_initial_mask()

            # Select first mask
            if self.masks:
                self.control_window.selected_mask = self.masks[0]

            # Refresh sidebar
            self.control_window.refresh_mask_list()

            self.setWindowTitle("BadMapper - Editor")

    def save_project(self):
        """Save the current project"""
        if self.current_file:
            success = ProjectSerializer.save_project(
                self.current_file,
                self.masks,
                self.projection_width,
                self.projection_height
            )
            if success:
                QMessageBox.information(self, "Success", f"Project saved to {self.current_file}")
                self.update_window_title()
            else:
                QMessageBox.critical(self, "Error", "Failed to save project")
        else:
            self.save_project_as()

    def save_project_as(self):
        """Save the current project with a new filename"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project As",
            "",
            "BadMapper Project (*.bad)"
        )

        if file_path:
            success = ProjectSerializer.save_project(
                file_path,
                self.masks,
                self.projection_width,
                self.projection_height
            )
            if success:
                self.current_file = file_path
                QMessageBox.information(self, "Success", f"Project saved to {file_path}")
                self.update_window_title()
            else:
                QMessageBox.critical(self, "Error", "Failed to save project")

    def open_project(self):
        """Open an existing project"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            "",
            "BadMapper Project (*.bad)"
        )

        if file_path:
            project_data = ProjectSerializer.load_project(file_path)

            if project_data:
                # Clean up existing masks
                for mask in self.masks:
                    if mask.media:
                        mask.media.release()

                # Load new project
                self.masks.clear()
                self.masks.extend(project_data["masks"])
                self.projection_width = project_data["projection_width"]
                self.projection_height = project_data["projection_height"]
                self.current_file = file_path

                # Update renderer with new projection size
                self.renderer.width = self.projection_width
                self.renderer.height = self.projection_height
                self.renderer.canvas = None  # Will be recreated on next render

                # Update projection window
                self.projection_window.setFixedSize(self.projection_width, self.projection_height)

                # Select first mask if available
                if self.masks:
                    self.control_window.selected_mask = self.masks[0]
                else:
                    self.control_window.selected_mask = None

                # Refresh sidebar
                self.control_window.refresh_mask_list()

                self.update_window_title()
                QMessageBox.information(self, "Success", f"Project loaded from {file_path}")
            else:
                QMessageBox.critical(self, "Error", "Failed to load project")

    def update_window_title(self):
        """Update the window title with the current file name"""
        if self.current_file:
            file_name = os.path.basename(self.current_file)
            self.setWindowTitle(f"BadMapper - Editor - {file_name}")
        else:
            self.setWindowTitle("BadMapper - Editor")

    def closeEvent(self, event):
        # Clean up media resources
        for mask in self.masks:
            if mask.media:
                mask.media.release()

        self.projection_window.close()
        event.accept()
