from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QScrollArea, QFrame, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPalette, QFont
import os


class ProjectListItem(QFrame):
    """Widget representing a single project in the list"""
    project_selected = pyqtSignal(str, str)  # Emits (file_path, project_name)
    project_remove_requested = pyqtSignal(str)  # Emits file_path

    def __init__(self, file_path, index, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.index = index
        self.selected = False

        # Extract project name from file path
        self.project_name = os.path.splitext(os.path.basename(file_path))[0]

        self.setFrameStyle(QFrame.Box | QFrame.Plain)
        self.setLineWidth(1)
        self.setAutoFillBackground(True)

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)

        # Numpad indicator (only show for projects 0-9)
        if self.index <= 9:
            numpad_label = QLabel(f"[{self.index}]")
            font = QFont()
            font.setPointSize(10)
            font.setBold(True)
            numpad_label.setFont(font)
            numpad_label.setStyleSheet("color: #48bb78; border: none;")
            numpad_label.setFixedWidth(35)
            layout.addWidget(numpad_label)

        # Project label
        self.label = QLabel(self.project_name)
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        layout.addStretch()

        # Remove button
        self.remove_btn = QPushButton("✕")
        self.remove_btn.setFixedSize(25, 25)
        self.remove_btn.setToolTip("Remove project from list")
        self.remove_btn.clicked.connect(self._on_remove_clicked)
        self.remove_btn.setStyleSheet("background-color: #e53e3e; color: white; font-weight: bold;")
        layout.addWidget(self.remove_btn)

        self.setLayout(layout)
        self.update_style()

    def _on_remove_clicked(self):
        self.project_remove_requested.emit(self.file_path)

    def set_selected(self, selected):
        self.selected = selected
        self.update_style()

    def update_style(self):
        if self.selected:
            self.setStyleSheet("""
                QFrame {
                    background-color: #4a5568;
                    border: 2px solid #48bb78;
                }
            """)
            self.label.setStyleSheet("color: white; border: none;")
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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.project_selected.emit(self.file_path, self.project_name)
        super().mousePressEvent(event)


class ProjectListWidget(QWidget):
    """Sidebar widget showing a list of all loaded projects"""
    project_selected = pyqtSignal(str, str)  # Emits (file_path, project_name)
    add_project_requested = pyqtSignal()
    project_switch_by_index_requested = pyqtSignal(int)  # Emits index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_items = []
        self.project_files = []  # List of file paths

        self.setFixedWidth(250)
        self.setStyleSheet("background-color: #1a202c;")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Title with add button
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Projects")
        title.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        title_layout.addWidget(title)

        title_layout.addStretch()

        # Add project button
        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(30, 30)
        self.add_btn.setToolTip("Add project to list")
        self.add_btn.clicked.connect(self._on_add_clicked)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #48bb78;
                color: white;
                font-weight: bold;
                font-size: 18px;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #38a169;
            }
        """)
        title_layout.addWidget(self.add_btn)

        title_container = QWidget()
        title_container.setLayout(title_layout)
        title_container.setStyleSheet("background-color: #2d3748;")
        main_layout.addWidget(title_container)

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

        self.setLayout(main_layout)

    def _on_add_clicked(self):
        """Handle add project button click"""
        self.add_project_requested.emit()

    def add_project(self, file_path):
        """Add a project to the list"""
        if file_path and file_path not in self.project_files:
            self.project_files.append(file_path)
            self.refresh()
            return True
        return False

    def remove_project(self, file_path):
        """Remove a project from the list"""
        if file_path in self.project_files:
            self.project_files.remove(file_path)
            self.refresh()

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
        for i, file_path in enumerate(self.project_files):
            item = ProjectListItem(file_path, i)
            item.project_selected.connect(self._on_project_selected)
            item.project_remove_requested.connect(self._on_project_remove_requested)
            self.container_layout.addWidget(item)
            self.project_items.append(item)

        # Add stretch at the end to push all items to the top
        self.container_layout.addStretch()

    def _on_project_selected(self, file_path, project_name):
        """Handle project selection"""
        self.set_selected_project(file_path)
        self.project_selected.emit(file_path, project_name)

    def _on_project_remove_requested(self, file_path):
        """Handle project removal request"""
        self.remove_project(file_path)

    def set_selected_project(self, file_path):
        """Update the visual selection state"""
        for item in self.project_items:
            item.set_selected(file_path is not None and item.file_path == file_path)

    def get_project_files(self):
        """Get list of all project file paths"""
        return self.project_files.copy()

    def switch_to_project_by_index(self, index):
        """Switch to project by numpad index (0-9)"""
        if 0 <= index <= 9 and index < len(self.project_files):
            file_path = self.project_files[index]
            # Extract project name from file path
            project_name = os.path.splitext(os.path.basename(file_path))[0]
            self.set_selected_project(file_path)
            self.project_selected.emit(file_path, project_name)
            return True
        return False

