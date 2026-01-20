# Simple Mapper - Projection Mapping

Software de projection mapping para mapear vídeos e imagens em superfícies irregulares através de projeção.

## Recursos

- 🎬 Suporte para vídeos (MP4, AVI, MOV, MKV) com loop automático
- 🖼️ Suporte para imagens (JPG, PNG, etc)
- 🎨 Transformação de perspectiva (warp) para mapeamento
- ✏️ Modo de edição com controles visuais
- 📐 Grid de visualização para facilitar alinhamento
- 🖥️ Modo tela cheia

## Instalação

1. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Como Usar

1. Execute o programa:
```bash
python main.py
```

2. Para carregar uma mídia, edite o arquivo `main.py` e descomente/adicione:
```python
app.load_media("caminho/para/sua/imagem.jpg")
app.load_media("caminho/para/seu/video.mp4")
```

## Controles

| Tecla | Função |
|-------|--------|
| **E** | Ativar/desativar modo de edição |
| **M** | Alternar entre mídia original e grid |
| **F** | Tela cheia (toggle) |
| **ESC** | Sair |

### Modo de Edição

Quando o modo de edição está ativo (tecla **E**):
- Você verá 4 círculos amarelos nos cantos da mídia
- Arraste esses cantos para ajustar a perspectiva
- As linhas ciano conectam os cantos mostrando a área mapeada
- O canto selecionado fica vermelho

### Grid de Visualização

Pressione **M** para alternar entre:
- Mídia original
- Grid de linhas brancas (facilita visualizar os limites e distorções)

## Casos de Uso

Este software é ideal para:
- Projection mapping em paredes, objetos e superfícies irregulares
- VJing e performances audiovisuais
- Instalações artísticas
- Cenografia digital
- Mapeamento de vídeo em superfícies 3D

## Estrutura do Projeto

```
simplemapper/
├── main.py              # Código principal
├── requirements.txt     # Dependências Python
└── README.md           # Este arquivo
```

## Próximas Funcionalidades

- [ ] Interface para carregar arquivos (dialog)
- [ ] Salvar/carregar configurações de mapeamento
- [ ] Múltiplas mídias simultâneas
- [ ] Controle de opacidade
- [ ] Efeitos e filtros
- [ ] Máscaras customizadas
