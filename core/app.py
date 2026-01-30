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

        # Project management
        self.loaded_projects = {}  # Dictionary: file_path -> project_data
        self.current_project_path = None  # Currently active project

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

        # Export menu
        export_menu = menubar.addMenu('Export')

        export_video_action = QAction('Export video', self)
        export_video_action.triggered.connect(self.export_video)
        export_menu.addAction(export_video_action)

        # Control window
        self.control_window = ControlWindow(self.masks)
        self.control_window.media_requested.connect(self.add_media_to_mask)
        self.control_window.mask_delete_requested.connect(self.delete_mask)
        self.control_window.media_replace_requested.connect(self.replace_media)
        self.control_window.project_selected.connect(self.switch_to_project)
        self.control_window.add_project_requested.connect(self.add_project_to_list)
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
            # Save current project state if it exists
            if self.current_project_path and self.current_project_path in self.loaded_projects:
                self.loaded_projects[self.current_project_path]["projection_width"] = self.projection_width
                self.loaded_projects[self.current_project_path]["projection_height"] = self.projection_height

            # Create a completely new masks list (don't modify the old one)
            # This prevents affecting loaded projects
            self.masks = []
            self.current_file = None
            self.current_project_path = None

            # Create initial mask
            self.create_initial_mask()

            # Select first mask
            if self.masks:
                self.control_window.selected_mask = self.masks[0]

            # Update control window with new masks list
            self.control_window.set_masks(self.masks)

            # Deselect any project in the project list
            self.control_window.project_list_widget.set_selected_project(None)

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
                self.current_project_path = file_path

                # Add to project list and loaded projects
                self.control_window.project_list_widget.add_project(file_path)
                self.control_window.project_list_widget.set_selected_project(file_path)
                self.save_current_project_state()

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
            self.load_and_switch_project(file_path)

    def load_and_switch_project(self, file_path):
        """Load a project and switch to it"""
        # Check if file exists
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "File Not Found", f"Project file not found:\n{file_path}\n\nRemoving from list.")
            # Remove from project list
            self.control_window.project_list_widget.remove_project(file_path)
            return

        project_data = ProjectSerializer.load_project(file_path)

        if project_data:
            # Save current project state before switching
            if self.current_project_path and self.current_project_path in self.loaded_projects:
                # Update the stored reference with current state
                self.loaded_projects[self.current_project_path]["projection_width"] = self.projection_width
                self.loaded_projects[self.current_project_path]["projection_height"] = self.projection_height

            # Clean up existing masks only if we're replacing them
            if not self.current_project_path or self.current_project_path not in self.loaded_projects:
                for mask in self.masks:
                    if mask.media:
                        mask.media.release()

            # Create a new masks list for this project
            new_masks = list(project_data["masks"])

            # Store project in loaded_projects dictionary BEFORE switching
            self.loaded_projects[file_path] = {
                "masks": new_masks,  # Store the new list reference
                "projection_width": project_data["projection_width"],
                "projection_height": project_data["projection_height"],
                "file_path": file_path
            }

            # Now switch to the new project
            self.masks = new_masks
            self.projection_width = project_data["projection_width"]
            self.projection_height = project_data["projection_height"]
            self.current_file = file_path
            self.current_project_path = file_path

            # Add to project list if not already there
            self.control_window.project_list_widget.add_project(file_path)
            self.control_window.project_list_widget.set_selected_project(file_path)

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

            # Update control window with new masks list
            self.control_window.set_masks(self.masks)

            self.update_window_title()
            # Removed MessageBox for faster switching
        else:
            QMessageBox.critical(self, "Error", f"Failed to load project:\n{file_path}")

    def save_current_project_state(self):
        """Save the current project state to the loaded_projects dictionary"""
        if self.current_project_path and self.current_project_path in self.loaded_projects:
            # Just update the dimensions, masks list is already stored by reference
            self.loaded_projects[self.current_project_path]["projection_width"] = self.projection_width
            self.loaded_projects[self.current_project_path]["projection_height"] = self.projection_height

    def switch_to_project(self, file_path, project_name):
        """Switch to a different loaded project"""
        if file_path == self.current_project_path:
            # Already on this project
            return

        # Check if file exists
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "File Not Found", f"Project file not found:\n{file_path}\n\nRemoving from list.")
            # Remove from project list and loaded projects
            self.control_window.project_list_widget.remove_project(file_path)
            if file_path in self.loaded_projects:
                del self.loaded_projects[file_path]
            return

        # Save current project state before switching (keep masks list reference)
        if self.current_project_path and self.current_project_path in self.loaded_projects:
            # Update the stored reference with current state
            self.loaded_projects[self.current_project_path]["projection_width"] = self.projection_width
            self.loaded_projects[self.current_project_path]["projection_height"] = self.projection_height

        # Check if project is already loaded
        if file_path in self.loaded_projects:
            # Restore from memory - swap to the stored masks list
            project_data = self.loaded_projects[file_path]

            # Swap to the project's masks list (each project has its own list with active media)
            self.masks = project_data["masks"]
            self.projection_width = project_data["projection_width"]
            self.projection_height = project_data["projection_height"]
            self.current_file = file_path
            self.current_project_path = file_path

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

            # Update control window with new masks list
            self.control_window.set_masks(self.masks)
            self.control_window.project_list_widget.set_selected_project(file_path)

            self.update_window_title()
        else:
            # Load from file if not in memory
            self.load_and_switch_project(file_path)

    def add_project_to_list(self):
        """Add a project to the project list"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Add Project to List",
            "",
            "BadMapper Project (*.bad)"
        )

        if file_path:
            # Add to project list
            if self.control_window.project_list_widget.add_project(file_path):
                # Optionally switch to it
                reply = QMessageBox.question(
                    self,
                    'Switch to Project',
                    f'Do you want to switch to "{os.path.basename(file_path)}"?',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    self.switch_to_project(file_path, os.path.basename(file_path))

    def update_window_title(self):
        """Update the window title with the current file name"""
        if self.current_file:
            file_name = os.path.basename(self.current_file)
            self.setWindowTitle(f"BadMapper - Editor - {file_name}")
        else:
            self.setWindowTitle("BadMapper - Editor")

    def export_video(self):
        """Export the projection window as an MP4 video"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QSpinBox, QPushButton, QHBoxLayout, QProgressDialog, QTextEdit
        from PyQt5.QtCore import QThread, pyqtSignal
        import cv2
        import math

        def gcd(a, b):
            """Calculate Greatest Common Divisor"""
            while b:
                a, b = b, a % b
            return a

        def lcm(a, b):
            """Calculate Least Common Multiple"""
            return abs(a * b) // gcd(a, b)

        def lcm_multiple(numbers):
            """Calculate LCM of multiple numbers"""
            if not numbers:
                return 1
            result = numbers[0]
            for num in numbers[1:]:
                result = lcm(result, num)
            return result

        # Collect all video durations
        video_durations = []
        for mask in self.masks:
            if mask.media and mask.media.is_video and mask.media.cap:
                # Get total frame count and FPS
                frame_count = mask.media.cap.get(cv2.CAP_PROP_FRAME_COUNT)
                fps = mask.media.cap.get(cv2.CAP_PROP_FPS)
                if frame_count > 0 and fps > 0:
                    video_duration = int(frame_count / fps)
                    if video_duration > 0:
                        video_durations.append(video_duration)

        # Calculate recommended duration (LCM for perfect loop)
        if video_durations:
            recommended_duration = lcm_multiple(video_durations)
            # Cap at a reasonable maximum (e.g., 300 seconds = 5 minutes)
            if recommended_duration > 300:
                # If LCM is too large, use the longest video duration
                recommended_duration = max(video_durations)

            info_text = f"Detected {len(video_durations)} video(s) with durations: {', '.join(map(str, video_durations))} seconds.\n\n"
            info_text += f"Recommended duration: {recommended_duration} seconds (LCM)\n\n"
            info_text += "The LCM (Least Common Multiple) ensures all videos complete an exact number of loops, "
            info_text += "creating a perfect seamless loop without any video cutting off mid-playback."
        else:
            recommended_duration = 10
            info_text = "No videos detected. Using default duration of 10 seconds."

        # Dialog for export settings
        dialog = QDialog(self)
        dialog.setWindowTitle("Export Video Settings")
        layout = QVBoxLayout()

        # Info text about LCM
        info_label = QTextEdit()
        info_label.setReadOnly(True)
        info_label.setMaximumHeight(100)
        info_label.setText(info_text)
        layout.addWidget(info_label)

        # Duration
        duration_label = QLabel("Duration (seconds):")
        layout.addWidget(duration_label)
        duration_spinbox = QSpinBox()
        duration_spinbox.setMinimum(1)
        duration_spinbox.setMaximum(3600)
        duration_spinbox.setValue(recommended_duration)
        layout.addWidget(duration_spinbox)

        # FPS
        fps_label = QLabel("FPS:")
        layout.addWidget(fps_label)
        fps_spinbox = QSpinBox()
        fps_spinbox.setMinimum(1)
        fps_spinbox.setMaximum(60)
        fps_spinbox.setValue(30)
        layout.addWidget(fps_spinbox)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Export")
        ok_button.clicked.connect(dialog.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)

        if dialog.exec_():
            duration = duration_spinbox.value()
            fps = fps_spinbox.value()

            # Ask for save location
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Video As",
                "",
                "MP4 Video (*.mp4)"
            )

            if file_path:
                # Ensure .mp4 extension
                if not file_path.endswith('.mp4'):
                    file_path += '.mp4'

                try:
                    # Create progress dialog
                    progress = QProgressDialog("Exporting video...", "Cancel", 0, duration * fps, self)
                    progress.setWindowTitle("Export Progress")
                    progress.setWindowModality(Qt.WindowModal)
                    progress.show()

                    # Get projection size
                    width = self.projection_width
                    height = self.projection_height

                    # Create VideoWriter
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    out = cv2.VideoWriter(file_path, fourcc, fps, (width, height))

                    frame_count = duration * fps
                    was_canceled = False

                    for i in range(frame_count):
                        if progress.wasCanceled():
                            was_canceled = True
                            break

                        # Render current frame
                        self.renderer.reset_canvas()
                        for mask in self.masks:
                            if mask.media:
                                self.renderer.render_mask(mask)

                        # Draw grids if enabled
                        if self.renderer.show_grid:
                            for mask in self.masks:
                                self.renderer.draw_grid(mask)

                        # Get the output frame
                        frame = self.renderer.get_output()

                        if frame is not None:
                            out.write(frame)

                        progress.setValue(i + 1)

                    out.release()
                    progress.close()

                    if was_canceled:
                        QMessageBox.information(self, "Cancelled", "Video export was cancelled")
                        # Remove incomplete file
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    else:
                        QMessageBox.information(self, "Success", f"Video exported to {file_path}")

                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to export video: {str(e)}")

    def closeEvent(self, event):
        # Clean up media resources
        for mask in self.masks:
            if mask.media:
                mask.media.release()

        self.projection_window.close()
        event.accept()
