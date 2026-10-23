# YouTube Downloader

Interface gráfica em Python (Tkinter) para baixar um vídeo ou o áudio de um vídeo do YouTube e convertê-lo para MP3.

## Requisitos

- Python 3.10 ou superior (recomendado)
- FFmpeg instalado e disponível no PATH
- Conexão com a internet

## Instalação

1. Instale o Python.
2. Instale a dependência:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Instale o FFmpeg:
   - Windows: instale uma compilação do FFmpeg e adicione a pasta `bin` ao PATH.
   - macOS: `brew install ffmpeg`
   - Ubuntu/Debian: `sudo apt install ffmpeg`

## Executar

Na pasta do projeto:

```bash
python youtube_downloader.py
```

## Recursos

- Seleção da pasta de destino.
- Campo para URL do vídeo.
- Download do melhor fluxo de áudio disponível.
- Conversão para MP3 (192 kbps) com FFmpeg.
- Progresso, velocidade/ETA quando fornecidos pelo yt-dlp e registro de atividade.
- Nome de arquivo baseado no título do vídeo.
- Abertura da pasta de destino.

## Observações

- Use apenas para conteúdo que você tem autorização para baixar e respeite os termos aplicáveis.
- A disponibilidade de vídeos pode variar; vídeos privados, restritos por idade, protegidos ou indisponíveis podem falhar.
- O YouTube pode mudar seus mecanismos; mantenha `yt-dlp` atualizado.
- A interface não incorpora o YouTube. Um botão de download dentro de uma página/iframe do YouTube não é confiável nem suportado por esta aplicação; use o campo de URL.
