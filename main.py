import pygame
import cv2
import numpy as np
import os
from pathlib import Path
from tkinter import Tk, filedialog
import math

class Button:
    """Botão clicável na interface"""
    def __init__(self, x, y, width, height, text, color=(100, 100, 100), active_color=(150, 150, 150)):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.active_color = active_color
        self.is_active = False
        self.hover = False
    
    def draw(self, screen):
        color = self.active_color if self.is_active else (self.color if not self.hover else (120, 120, 120))
        pygame.draw.rect(screen, color, self.rect, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), self.rect, 2, border_radius=5)
        
        font = pygame.font.Font(None, 24)
        text_surface = font.render(self.text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                return True
        return False

class Media:
    """Classe para gerenciar imagens e vídeos"""
    def __init__(self, filepath, x=100, y=100, width=400, height=300):
        self.filepath = filepath
        self.is_video = filepath.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))
        
        # Pontos de perspectiva (4 cantos)
        self.corners = np.float32([
            [x, y],
            [x + width, y],
            [x + width, y + height],
            [x, y + height]
        ])
        
        # Índice do canto selecionado (-1 = nenhum)
        self.selected_corner = -1
        self.dragging = False
        
        # Modo de transformação: 'perspective', 'move', 'resize', 'rotate'
        self.transform_mode = 'perspective'
        
        # Para modo de movimento
        self.drag_offset = None
        
        # Para modo de rotação
        self.rotation_angle = 0
        self.rotation_center = None
        self.initial_angle = 0
        
        # Para modo de redimensionamento
        self.resize_anchor = None
        self.initial_corners = None
        self.initial_mouse_pos = None
        
        # Botões de modo
        self.buttons = []
        self.update_buttons()
        
        # Carregar mídia
        self.load_frame()
        
    def update_buttons(self):
        """Atualizar posição dos botões acima da mídia"""
        # Calcular centro superior da mídia
        top_center_x = (self.corners[0][0] + self.corners[1][0]) / 2
        top_y = min(self.corners[0][1], self.corners[1][1]) - 60
        
        button_width = 90
        button_height = 35
        spacing = 10
        
        modes = ['Perspectiva', 'Mover', 'Redimensionar', 'Rotacionar']
        mode_keys = ['perspective', 'move', 'resize', 'rotate']
        
        total_width = len(modes) * button_width + (len(modes) - 1) * spacing + button_width + spacing
        start_x = top_center_x - total_width / 2
        
        self.buttons = []
        for i, (mode_text, mode_key) in enumerate(zip(modes, mode_keys)):
            btn = Button(
                start_x + i * (button_width + spacing),
                top_y,
                button_width,
                button_height,
                mode_text,
                color=(70, 70, 150),
                active_color=(100, 150, 255)
            )
            btn.is_active = (self.transform_mode == mode_key)
            btn.mode = mode_key
            self.buttons.append(btn)
        
        # Botão de deletar
        delete_btn = Button(
            start_x + len(modes) * (button_width + spacing),
            top_y,
            button_width,
            button_height,
            'Deletar',
            color=(150, 30, 30),
            active_color=(200, 50, 50)
        )
        delete_btn.mode = 'delete'
        self.buttons.append(delete_btn)
    
    def load_frame(self):
        """Carregar mídia"""
        if self.is_video:
            self.cap = cv2.VideoCapture(self.filepath)
            self.frame = None
            ret, frame = self.cap.read()
            if ret:
                self.frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.original_size = (frame.shape[1], frame.shape[0])
        else:
            img = cv2.imread(self.filepath)
            if img is not None:
                self.frame = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                self.original_size = (img.shape[1], img.shape[0])
    
    def update(self):
        """Atualizar frame do vídeo"""
        if self.is_video:
            ret, frame = self.cap.read()
            if not ret:
                # Reiniciar vídeo (loop)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            if ret:
                self.frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    def get_transformed_image(self, screen_size, show_grid=False):
        """Aplicar transformação de perspectiva"""
        if self.frame is None:
            return None
        
        # Se mostrar grid, criar imagem de grid
        if show_grid:
            grid_img = self.create_grid_image()
            src_img = grid_img
        else:
            src_img = self.frame
        
        # Pontos de origem (retângulo original da imagem)
        h, w = src_img.shape[:2]
        src_points = np.float32([
            [0, 0],
            [w, 0],
            [w, h],
            [0, h]
        ])
        
        # Calcular matriz de transformação
        matrix = cv2.getPerspectiveTransform(src_points, self.corners)
        
        # Aplicar transformação
        result = cv2.warpPerspective(src_img, matrix, screen_size, 
                                     borderMode=cv2.BORDER_CONSTANT, 
                                     borderValue=(0, 0, 0))
        
        return result
    
    def create_grid_image(self):
        """Criar imagem de grid para visualização"""
        h, w = self.frame.shape[:2]
        grid = np.ones((h, w, 3), dtype=np.uint8) * 128
        
        # Linhas verticais
        for i in range(0, w, 50):
            cv2.line(grid, (i, 0), (i, h), (255, 255, 255), 2)
        
        # Linhas horizontais
        for i in range(0, h, 50):
            cv2.line(grid, (0, i), (w, i), (255, 255, 255), 2)
        
        # Borda
        cv2.rectangle(grid, (0, 0), (w-1, h-1), (0, 255, 0), 4)
        
        return grid
    
    def get_center(self):
        """Obter centro da mídia"""
        return np.mean(self.corners, axis=0)
    
    def set_mode(self, mode):
        """Alterar modo de transformação"""
        if mode in ['perspective', 'move', 'resize', 'rotate']:
            self.transform_mode = mode
            for btn in self.buttons:
                btn.is_active = (btn.mode == mode)
    
    def rotate_corners(self, angle, center):
        """Rotacionar cantos em torno de um ponto"""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        new_corners = []
        for corner in self.corners:
            # Transladar para origem
            x = corner[0] - center[0]
            y = corner[1] - center[1]
            
            # Rotacionar
            new_x = x * cos_a - y * sin_a
            new_y = x * sin_a + y * cos_a
            
            # Transladar de volta
            new_corners.append([new_x + center[0], new_y + center[1]])
        
        return np.float32(new_corners)
    
    def move_corners(self, delta):
        """Mover todos os cantos"""
        self.corners += delta
    
    def scale_corners(self, scale_x, scale_y, center):
        """Redimensionar cantos a partir do centro"""
        new_corners = []
        for corner in self.corners:
            # Vetor do centro para o canto
            direction = corner - center
            # Aplicar escala
            new_corner = center + direction * np.array([scale_x, scale_y])
            new_corners.append(new_corner)
        return np.float32(new_corners)
    
    def draw_controls(self, screen, edit_mode):
        """Desenhar controles de edição"""
        if not edit_mode:
            return
        
        # Desenhar linhas entre os cantos
        for i in range(4):
            p1 = tuple(self.corners[i].astype(int))
            p2 = tuple(self.corners[(i + 1) % 4].astype(int))
            pygame.draw.line(screen, (0, 255, 255), p1, p2, 2)
        
        # Desenhar elementos específicos do modo
        if self.transform_mode == 'perspective':
            # Desenhar cantos para perspectiva
            for i, corner in enumerate(self.corners):
                color = (255, 0, 0) if i == self.selected_corner else (255, 255, 0)
                pygame.draw.circle(screen, color, corner.astype(int), 8, 0)
                pygame.draw.circle(screen, (0, 0, 0), corner.astype(int), 8, 2)
        
        elif self.transform_mode == 'move':
            # Mostrar apenas o contorno
            center = self.get_center().astype(int)
            pygame.draw.circle(screen, (0, 255, 0), center, 10, 0)
            pygame.draw.circle(screen, (0, 0, 0), center, 10, 2)
        
        elif self.transform_mode == 'resize':
            # Desenhar cantos como pontos de redimensionamento
            for corner in self.corners:
                pygame.draw.rect(screen, (255, 0, 255), 
                               (corner[0] - 6, corner[1] - 6, 12, 12))
                pygame.draw.rect(screen, (0, 0, 0), 
                               (corner[0] - 6, corner[1] - 6, 12, 12), 2)
        
        elif self.transform_mode == 'rotate':
            # Desenhar círculo de rotação
            center = self.get_center().astype(int)
            pygame.draw.circle(screen, (255, 128, 0), center, 12, 0)
            pygame.draw.circle(screen, (0, 0, 0), center, 12, 2)
            
            # Desenhar linha de indicação de ângulo
            radius = 80
            angle_rad = math.radians(self.rotation_angle)
            end_x = center[0] + radius * math.cos(angle_rad)
            end_y = center[1] + radius * math.sin(angle_rad)
            pygame.draw.line(screen, (255, 128, 0), center, (int(end_x), int(end_y)), 2)
        
        # Desenhar botões
        self.update_buttons()
        for button in self.buttons:
            button.draw(screen)
    
    def handle_mouse_down(self, pos, edit_mode):
        """Tratar clique do mouse"""
        if not edit_mode:
            return False
        
        # Verificar clique nos botões
        for button in self.buttons:
            if button.rect.collidepoint(pos):
                if button.mode == 'delete':
                    return 'delete'  # Sinal especial para deletar
                self.transform_mode = button.mode
                for btn in self.buttons:
                    btn.is_active = (btn.mode == self.transform_mode)
                print(f"Modo alterado para: {self.transform_mode}")
                return True
        
        # Comportamento específico por modo
        if self.transform_mode == 'perspective':
            # Verificar se clicou em algum canto
            for i, corner in enumerate(self.corners):
                dist = np.linalg.norm(corner - np.array(pos))
                if dist < 15:
                    self.selected_corner = i
                    self.dragging = True
                    return True
        
        elif self.transform_mode == 'move':
            # Verificar se clicou dentro da mídia
            center = self.get_center()
            if np.linalg.norm(center - np.array(pos)) < 100:
                self.dragging = True
                self.drag_offset = np.array(pos) - center
                return True
        
        elif self.transform_mode == 'resize':
            # Verificar se clicou em algum canto
            for i, corner in enumerate(self.corners):
                dist = np.linalg.norm(corner - np.array(pos))
                if dist < 15:
                    self.selected_corner = i
                    self.dragging = True
                    self.initial_corners = self.corners.copy()
                    self.initial_mouse_pos = np.array(pos, dtype=np.float32)
                    return True
        
        elif self.transform_mode == 'rotate':
            # Verificar se clicou perto do centro ou em qualquer lugar da mídia
            center = self.get_center()
            self.dragging = True
            self.rotation_center = center
            # Calcular ângulo inicial
            dx = pos[0] - center[0]
            dy = pos[1] - center[1]
            self.initial_angle = math.atan2(dy, dx)
            return True
        
        return False
    
    def handle_mouse_up(self):
        """Tratar soltar do mouse"""
        self.dragging = False
        self.selected_corner = -1
        self.drag_offset = None
        self.resize_anchor = None
        self.initial_corners = None
        self.initial_mouse_pos = None
        self.rotation_center = None
    
    def handle_mouse_move(self, pos):
        """Tratar movimento do mouse"""
        if not self.dragging:
            # Atualizar hover dos botões
            for button in self.buttons:
                button.hover = button.rect.collidepoint(pos)
            return
        
        if self.transform_mode == 'perspective':
            if self.selected_corner >= 0:
                self.corners[self.selected_corner] = np.array(pos, dtype=np.float32)
        
        elif self.transform_mode == 'move':
            if self.drag_offset is not None:
                new_center = np.array(pos) - self.drag_offset
                old_center = self.get_center()
                delta = new_center - old_center
                self.move_corners(delta)
        
        elif self.transform_mode == 'resize':
            if self.selected_corner >= 0 and self.initial_corners is not None:
                # Calcular centro da forma original
                center = np.mean(self.initial_corners, axis=0)
                
                # Calcular distância original e nova do centro ao canto
                original_dist = np.linalg.norm(self.initial_corners[self.selected_corner] - center)
                new_dist = np.linalg.norm(np.array(pos) - center)
                
                if original_dist > 0:
                    # Escala uniforme baseada na proporção das distâncias
                    scale = new_dist / original_dist
                    scale = max(0.1, min(scale, 5.0))  # Limitar entre 0.1x e 5x
                    
                    # Aplicar escala uniformemente a partir do centro
                    for i in range(4):
                        direction = self.initial_corners[i] - center
                        self.corners[i] = center + direction * scale
        
        elif self.transform_mode == 'rotate':
            if self.rotation_center is not None:
                # Calcular novo ângulo
                dx = pos[0] - self.rotation_center[0]
                dy = pos[1] - self.rotation_center[1]
                current_angle = math.atan2(dy, dx)
                
                # Diferença de ângulo
                angle_delta = current_angle - self.initial_angle
                
                # Rotacionar cantos
                self.corners = self.rotate_corners(angle_delta, self.rotation_center)
                
                # Atualizar ângulo de rotação para visualização
                self.rotation_angle = math.degrees(current_angle)
                
                # Atualizar ângulo inicial para próximo frame
                self.initial_angle = current_angle
    
    def cleanup(self):
        """Liberar recursos"""
        if self.is_video:
            self.cap.release()


class ProjectionMapper:
    """Aplicação principal de projection mapping"""
    def __init__(self):
        pygame.init()
        
        # Configurações iniciais
        self.screen_width = 1280
        self.screen_height = 720
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("BadMapper")
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Estados
        self.edit_mode = False
        self.show_grid = False
        self.fullscreen = False
        
        # Mídias carregadas
        self.medias = []
        self.current_media = None
    
    def load_media(self, filepath):
        """Carregar mídia (imagem ou vídeo)"""
        if os.path.exists(filepath):
            media = Media(filepath)
            self.medias.append(media)
            self.current_media = media
            print(f"Mídia carregada: {filepath}")
    
    def open_file_dialog(self):
        """Abrir diálogo para selecionar arquivo de mídia"""
        # Ocultar janela do Tkinter
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        # Tipos de arquivo suportados
        filetypes = (
            ('Todos os arquivos de mídia', '*.jpg *.jpeg *.png *.bmp *.gif *.mp4 *.avi *.mov *.mkv'),
            ('Imagens', '*.jpg *.jpeg *.png *.bmp *.gif'),
            ('Vídeos', '*.mp4 *.avi *.mov *.mkv'),
            ('Todos os arquivos', '*.*')
        )
        
        # Abrir diálogo
        filepath = filedialog.askopenfilename(
            title='Selecionar Mídia',
            filetypes=filetypes
        )
        
        root.destroy()
        
        # Carregar mídia se selecionada
        if filepath:
            self.load_media(filepath)
            return True
        return False
    
    def toggle_fullscreen(self):
        """Alternar tela cheia"""
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            info = pygame.display.Info()
            self.screen_width = info.current_w
            self.screen_height = info.current_h
        else:
            self.screen_width = 1280
            self.screen_height = 720
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
    
    def handle_events(self):
        """Processar eventos"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                # Toggle modo de edição
                if event.key == pygame.K_e:
                    self.edit_mode = not self.edit_mode
                    print(f"Modo de edição: {'ON' if self.edit_mode else 'OFF'}")
                
                # Atalhos numéricos para modos (1=Perspectiva, 2=Mover, 3=Redimensionar, 4=Rotacionar)
                elif event.key == pygame.K_1 and self.current_media:
                    self.current_media.set_mode('perspective')
                    print("Modo: Perspectiva")
                
                elif event.key == pygame.K_2 and self.current_media:
                    self.current_media.set_mode('move')
                    print("Modo: Mover")
                
                elif event.key == pygame.K_3 and self.current_media:
                    self.current_media.set_mode('resize')
                    print("Modo: Redimensionar")
                
                elif event.key == pygame.K_4 and self.current_media:
                    self.current_media.set_mode('rotate')
                    print("Modo: Rotacionar")
                
                # Deletar mídia (tecla DELETE ou D)
                elif event.key in [pygame.K_DELETE, pygame.K_d] and self.current_media:
                    if self.current_media in self.medias:
                        self.current_media.cleanup()
                        self.medias.remove(self.current_media)
                        self.current_media = self.medias[-1] if self.medias else None
                        print(f"Mídia deletada. Mídias restantes: {len(self.medias)}")
                
                # Toggle grid
                elif event.key == pygame.K_m:
                    self.show_grid = not self.show_grid
                    print(f"Grid: {'ON' if self.show_grid else 'OFF'}")
                
                # Toggle tela cheia
                elif event.key == pygame.K_f:
                    self.toggle_fullscreen()
                    print(f"Tela cheia: {'ON' if self.fullscreen else 'OFF'}")
                
                # Carregar mídia (tecla I - Import)
                elif event.key == pygame.K_i:
                    print("Abrindo diálogo de seleção...")
                    self.open_file_dialog()
                
                # Sair
                elif event.key == pygame.K_ESCAPE:
                    self.running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Botão esquerdo
                    if self.current_media:
                        result = self.current_media.handle_mouse_down(event.pos, self.edit_mode)
                        if result == 'delete':
                            # Deletar mídia atual
                            self.current_media.cleanup()
                            self.medias.remove(self.current_media)
                            self.current_media = self.medias[-1] if self.medias else None
                            print(f"Mídia deletada. Mídias restantes: {len(self.medias)}")
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    if self.current_media:
                        self.current_media.handle_mouse_up()
            
            elif event.type == pygame.MOUSEMOTION:
                if self.current_media:
                    self.current_media.handle_mouse_move(event.pos)
    
    def update(self):
        """Atualizar estado"""
        # Atualizar todas as mídias (vídeos)
        for media in self.medias:
            media.update()
    
    def render(self):
        """Renderizar tela"""
        # Tela preta
        self.screen.fill((0, 0, 0))
        
        # Renderizar mídia atual
        if self.current_media:
            transformed = self.current_media.get_transformed_image(
                (self.screen_width, self.screen_height),
                self.show_grid
            )
            
            if transformed is not None:
                # Converter para surface do pygame
                surface = pygame.surfarray.make_surface(transformed.swapaxes(0, 1))
                self.screen.blit(surface, (0, 0))
            
            # Desenhar controles de edição
            self.current_media.draw_controls(self.screen, self.edit_mode)
        
        # Mostrar instruções se em modo de edição
        if self.edit_mode:
            self.draw_instructions()
        
        pygame.display.flip()
    
    def draw_instructions(self):
        """Desenhar instruções na tela"""
        font = pygame.font.Font(None, 24)
        mode_names = {
            'perspective': 'PERSPECTIVA',
            'move': 'MOVER',
            'resize': 'REDIMENSIONAR',
            'rotate': 'ROTACIONAR'
        }
        
        current_mode = mode_names.get(self.current_media.transform_mode, 'EDIÇÃO') if self.current_media else 'EDIÇÃO'
        
        instructions = [
            f"MODO: {current_mode}",
            "Botões: acima da mídia | Atalhos: 1-Perspectiva 2-Mover 3-Resize 4-Rotar",
            "I-Importar | E-Edição | M-Grid | F-Fullscreen | D-Deletar | ESC-Sair"
        ]
        
        y = 10
        for text in instructions:
            surface = font.render(text, True, (255, 255, 0))
            # Fundo semi-transparente
            bg_rect = surface.get_rect(topleft=(10, y))
            bg_rect.inflate_ip(10, 5)
            s = pygame.Surface(bg_rect.size)
            s.set_alpha(180)
            s.fill((0, 0, 0))
            self.screen.blit(s, bg_rect)
            self.screen.blit(surface, (10, y))
            y += 25
    
    def run(self):
        """Loop principal"""
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(30)  # 30 FPS
        
        self.cleanup()
    
    def cleanup(self):
        """Limpar recursos"""
        for media in self.medias:
            media.cleanup()
        pygame.quit()


if __name__ == "__main__":
    app = ProjectionMapper()
    
    # Exemplo: carregar uma mídia
    # Descomente e coloque o caminho da sua mídia
    # app.load_media("caminho/para/sua/imagem.jpg")
    # app.load_media("caminho/para/seu/video.mp4")
    
    print("=" * 60)
    print("SIMPLE MAPPER - Projection Mapping")
    print("=" * 60)
    print("\nControles:")
    print("  I - Importar mídia (imagem ou vídeo)")
    print("  E - Ativar/desativar modo de edição")
    print("  M - Alternar entre mídia e grid")
    print("  F - Tela cheia")
    print("  D ou DELETE - Deletar mídia atual")
    print("  ESC - Sair")
    print("\nAtalhos de Modo (no modo de edição):")
    print("  1 - Perspectiva (ajustar warp)")
    print("  2 - Mover")
    print("  3 - Redimensionar")
    print("  4 - Rotacionar")
    print("\nModo de edição:")
    print("  - Use os botões acima da mídia ou teclas 1-4")
    print("  - Arraste para transformar a mídia")
    print("  - Botão vermelho 'Deletar' remove a mídia")
    print("\nFormatos suportados:")
    print("  Imagens: JPG, PNG, BMP, GIF")
    print("  Vídeos: MP4, AVI, MOV, MKV")
    print("=" * 60)
    
    app.run()
