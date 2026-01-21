# BadMapper3

Software de projection mapping com interface drag & drop para transformações geométricas em tempo real.

## Instalação Rápida

### Linux/macOS
```bash
./install.sh
./run.sh
```

### Windows
```
install.bat
run.bat
```

### Manual
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate.bat  # Windows

pip install -r requirements.txt
python main.py
```

## Importante: Conflito Qt/OpenCV

Este projeto usa `opencv-python-headless` para evitar conflitos entre PyQt5 e OpenCV. Se você tiver `opencv-python` instalado, remova-o antes:

```bash
pip uninstall opencv-python
pip install opencv-python-headless
```

## Uso Rápido

1. **Janela de Controle**: edite grids e máscaras
2. **Janela de Projeção**: visualize o resultado final (fullscreen recomendado)
3. **Adicionar mídia**: clique no botão central do grid
4. **Transformar máscara**: 
   - Arraste vértices para ajustar perspectiva
   - Arraste o centro para mover
5. **Transformar mídia**: 
   - Ctrl + Arrastar: mover mídia
   - Ctrl + Scroll: escalar mídia
   - Shift + Scroll: rotacionar mídia
6. **Atalhos**:
   - H: mostrar/ocultar ajuda
   - F11: fullscreen na janela de projeção

## Compatibilidade

- Windows, Linux, macOS
- Python 3.8+
