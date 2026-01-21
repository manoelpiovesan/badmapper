from PyQt5.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QMenuBar, QMenu, QAction
from PyQt5.QtCore import QTimer, Qt
from core.mask import Mask, MaskType
from core.media import Media
from core.renderer import Renderer
from ui.control_window import ControlWindow
from ui.projection_window import ProjectionWindow

class ProjectionMapper(QMainWindow):
    def __init__(self):
        super().__init__()

        self.projection_width = 1920
        self.projection_height = 1080

        self.masks = []
        self.renderer = Renderer(self.projection_width, self.projection_height)

        self.init_ui()
        self.create_initial_mask()

        # Selecionar a primeira máscara por padrão
        if self.masks:
            self.control_window.selected_mask = self.masks[0]

    def init_ui(self):
        self.setWindowTitle("BadMapper3")

        # Create menu bar
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('Arquivo')

        add_mask_action = QAction('Nova Máscara', self)
        add_mask_action.triggered.connect(self.add_mask_dialog)
        file_menu.addAction(add_mask_action)

        file_menu.addSeparator()

        exit_action = QAction('Sair', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu('Visualizar')

        toggle_projection_action = QAction('Janela de Projeção', self)
        toggle_projection_action.triggered.connect(self.toggle_projection_window)
        view_menu.addAction(toggle_projection_action)

        fullscreen_action = QAction('Projeção Fullscreen (F11)', self)
        fullscreen_action.triggered.connect(self.toggle_projection_fullscreen)
        view_menu.addAction(fullscreen_action)

        # Control window
        self.control_window = ControlWindow(self.masks)
        self.control_window.media_requested.connect(self.add_media_to_mask)
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
        dialog.setWindowTitle("Escolha o tipo de máscara")
        layout = QVBoxLayout()

        rect_radio = QRadioButton("Retângulo")
        rect_radio.setChecked(True)
        tri_radio = QRadioButton("Triângulo")
        sphere_radio = QRadioButton("Esfera (2D)")

        layout.addWidget(rect_radio)
        layout.addWidget(tri_radio)
        layout.addWidget(sphere_radio)

        ok_button = QPushButton("Criar")
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

    def add_media_to_mask(self, mask):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Mídia",
            "",
            "Arquivos de Mídia (*.jpg *.jpeg *.png *.bmp *.mp4 *.avi *.mov *.mkv *.webm)"
        )

        if file_path:
            try:
                media = Media(file_path)
                mask.media = media
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Não foi possível carregar a mídia: {str(e)}")

    def render_frame(self):
        self.renderer.reset_canvas()

        for mask in self.masks:
            if mask.media:
                self.renderer.render_mask(mask)

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
        # F11 para fullscreen
        if event.key() == Qt.Key_F11:
            self.toggle_projection_fullscreen()
        else:
            # Repassar eventos de teclado para o control_window
            self.control_window.keyPressEvent(event)

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        # Repassar eventos de teclado para o control_window
        self.control_window.keyReleaseEvent(event)
        super().keyReleaseEvent(event)

    def closeEvent(self, event):
        # Clean up media resources
        for mask in self.masks:
            if mask.media:
                mask.media.release()

        self.projection_window.close()
        event.accept()
