from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QScrollArea, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPalette, QFont


class MaskListItem(QFrame):
    """Widget representing a single mask in the list"""
    lock_toggled = pyqtSignal(object)  # Emits the mask
    visibility_toggled = pyqtSignal(object)  # Emits the mask
    mask_selected = pyqtSignal(object)  # Emits the mask

    def __init__(self, mask, index, parent=None):
        super().__init__(parent)
        self.mask = mask
        self.index = index
        self.selected = False

        self.setFrameStyle(QFrame.Box | QFrame.Plain)
        self.setLineWidth(1)
        self.setAutoFillBackground(True)

        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        # Mask label
        self.label = QLabel(f"Mask {index + 1}")
        font = QFont()
        font.setPointSize(10)
        self.label.setFont(font)
        layout.addWidget(self.label)

        layout.addStretch()

        # Lock button
        self.lock_btn = QPushButton("🔓")
        self.lock_btn.setFixedSize(30, 30)
        self.lock_btn.setToolTip("Lock/Unlock mask editing")
        self.lock_btn.clicked.connect(self._on_lock_clicked)
        self.update_lock_button()
        layout.addWidget(self.lock_btn)

        # Visibility button
        self.visibility_btn = QPushButton("👁")
        self.visibility_btn.setFixedSize(30, 30)
        self.visibility_btn.setToolTip("Show/Hide mask in editor")
        self.visibility_btn.clicked.connect(self._on_visibility_clicked)
        self.update_visibility_button()
        layout.addWidget(self.visibility_btn)

        self.setLayout(layout)
        self.update_style()

    def _on_lock_clicked(self):
        self.mask.locked = not self.mask.locked
        self.update_lock_button()
        self.lock_toggled.emit(self.mask)

    def _on_visibility_clicked(self):
        self.mask.hidden = not self.mask.hidden
        self.update_visibility_button()
        self.visibility_toggled.emit(self.mask)

    def update_lock_button(self):
        if self.mask.locked:
            self.lock_btn.setText("🔒")
            self.lock_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
        else:
            self.lock_btn.setText("🔓")
            self.lock_btn.setStyleSheet("background-color: #51cf66; color: white;")

    def update_visibility_button(self):
        if self.mask.hidden:
            self.visibility_btn.setText("👁‍🗨")
            self.visibility_btn.setStyleSheet("background-color: #868e96; color: white;")
        else:
            self.visibility_btn.setText("👁")
            self.visibility_btn.setStyleSheet("background-color: #339af0; color: white;")

    def set_selected(self, selected):
        self.selected = selected
        self.update_style()

    def update_style(self):
        if self.selected:
            self.setStyleSheet("""
                QFrame {
                    background-color: #4a5568;
                    border: 2px solid #00c8ff;
                }
            """)
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
            self.mask_selected.emit(self.mask)
        super().mousePressEvent(event)


class MaskListWidget(QWidget):
    """Sidebar widget showing a list of all masks"""
    mask_selected = pyqtSignal(object)  # Emits the selected mask

    def __init__(self, masks, parent=None):
        super().__init__(parent)
        self.masks = masks
        self.mask_items = []

        self.setFixedWidth(200)
        self.setStyleSheet("background-color: #1a202c;")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("Masks")
        title.setStyleSheet("color: white; font-weight: bold; font-size: 14px; padding: 10px; background-color: #2d3748;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Scroll area for mask list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1a202c;
            }
        """)

        # Container for mask items
        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container_layout.setSpacing(5)
        self.container_layout.setContentsMargins(5, 5, 5, 5)
        self.container.setLayout(self.container_layout)

        scroll_area.setWidget(self.container)
        main_layout.addWidget(scroll_area)

        self.setLayout(main_layout)

        self.refresh()

    def refresh(self):
        """Refresh the mask list"""
        # Clear existing items and layout completely
        for item in self.mask_items:
            item.setParent(None)
            item.deleteLater()
        self.mask_items.clear()

        # Clear all items from layout (including stretches)
        while self.container_layout.count():
            child = self.container_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Create new items
        for i, mask in enumerate(self.masks):
            item = MaskListItem(mask, i)
            item.lock_toggled.connect(self._on_lock_toggled)
            item.visibility_toggled.connect(self._on_visibility_toggled)
            item.mask_selected.connect(self._on_mask_selected)
            self.container_layout.addWidget(item)
            self.mask_items.append(item)

        # Add stretch at the end to push all items to the top
        self.container_layout.addStretch()

    def _on_lock_toggled(self, mask):
        """Handle lock toggle"""
        # Just update the display
        pass

    def _on_visibility_toggled(self, mask):
        """Handle visibility toggle"""
        # Just update the display
        pass

    def _on_mask_selected(self, mask):
        """Handle mask selection"""
        self.set_selected_mask(mask)
        self.mask_selected.emit(mask)

    def set_selected_mask(self, mask):
        """Update the visual selection state"""
        for item in self.mask_items:
            item.set_selected(item.mask == mask)

    def update_items(self):
        """Update all items (useful when masks change)"""
        for item in self.mask_items:
            item.update_lock_button()
            item.update_visibility_button()
