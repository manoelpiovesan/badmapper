from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QScrollArea, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPalette, QFont
import os


class ProjectListItem(QFrame):
    """Widget representing a single project in the list"""
    project_selected = pyqtSignal(object)  # Emits the project dict

    def __init__(self, project_data, index, parent=None):
        super().__init__(parent)
        self.project_data = project_data  # Dict with 'name', 'path', 'masks', 'projection_width', 'projection_height'
        self.index = index
        self.selected = False

        self.setFrameStyle(QFrame.Box | QFrame.Plain)
        self.setLineWidth(1)
        self.setAutoFillBackground(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        # Project name label
        self.label = QLabel(project_data.get('name', f'Project {index + 1}'))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.label.setFont(font)
        layout.addWidget(self.label)

        # Info label (masks count)
        mask_count = len(project_data.get('masks', []))
        self.info_label = QLabel(f"{mask_count} mask(s)")
        info_font = QFont()
        info_font.setPointSize(8)
        self.info_label.setFont(info_font)
        layout.addWidget(self.info_label)

        self.setLayout(layout)
        self.update_style()

    def set_selected(self, selected):
        self.selected = selected
        self.update_style()

    def update_style(self):
        if self.selected:
            self.setStyleSheet("""
                QFrame {
                    background-color: #4a5568;
                    border: 2px solid #00ff88;
                }
            """)
            self.label.setStyleSheet("color: #00ff88; border: none;")
            self.info_label.setStyleSheet("color: #aaffdd; border: none;")
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #2d3748;
                    border: 1px solid #4a5568;
                }
                QFrame:hover {
                    background-color: #3d4758;
                }
            """)
            self.label.setStyleSheet("color: white; border: none;")
            self.info_label.setStyleSheet("color: #a0aec0; border: none;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.project_selected.emit(self.project_data)
        super().mousePressEvent(event)


class ProjectListWidget(QWidget):
    """Sidebar widget showing a list of all loaded projects"""
    project_selected = pyqtSignal(object)  # Emits the selected project dict
    project_removed = pyqtSignal(object)  # Emits the project to remove

    def __init__(self, projects, parent=None):
        super().__init__(parent)
        self.projects = projects  # List of project dicts
        self.project_items = []

        self.setFixedWidth(200)
        self.setStyleSheet("background-color: #1a202c;")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("Projects")
        title.setStyleSheet("color: white; font-weight: bold; font-size: 14px; padding: 10px; background-color: #2d3748;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Scroll area for project list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1a202c;
            }
        """)

        # Container for project items
        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container_layout.setSpacing(5)
        self.container_layout.setContentsMargins(5, 5, 5, 5)
        self.container.setLayout(self.container_layout)

        scroll_area.setWidget(self.container)
        main_layout.addWidget(scroll_area)

        # Add project button
        add_btn = QPushButton("+ Load Project")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #38a169;
                color: white;
                border: none;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #48bb79;
            }
        """)
        add_btn.clicked.connect(self._on_add_clicked)
        main_layout.addWidget(add_btn)

        self.setLayout(main_layout)

        self.refresh()

    def _on_add_clicked(self):
        """Request to load a new project"""
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Project",
            "",
            "BadMapper Project (*.bad)"
        )
        if file_path:
            # Emit signal to parent to handle loading
            self.project_selected.emit({'path': file_path, 'is_new': True})

    def refresh(self):
        """Refresh the project list"""
        # Clear existing items and layout completely
        for item in self.project_items:
            item.setParent(None)
            item.deleteLater()
        self.project_items.clear()

        # Clear all items from layout (including stretches)
        while self.container_layout.count():
            child = self.container_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Create new items
        for i, project in enumerate(self.projects):
            item = ProjectListItem(project, i)
            item.project_selected.connect(self._on_project_selected)
            self.container_layout.addWidget(item)
            self.project_items.append(item)

        # Add stretch at the end to push all items to the top
        self.container_layout.addStretch()

    def _on_project_selected(self, project_data):
        """Handle project selection"""
        self.set_selected_project(project_data)
        self.project_selected.emit(project_data)

    def set_selected_project(self, project_data):
        """Update the visual selection state"""
        for item in self.project_items:
            item.set_selected(item.project_data == project_data)
