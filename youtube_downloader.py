import os
import re
import sys
import queue
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


APP_TITLE = "YouTube Downloader"
APP_VERSION = "1.0"


def safe_title(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = value.strip().rstrip(".")
    return value or "audio_youtube"


class AudioDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_TITLE} • {APP_VERSION}")
        self.root.geometry("760x650")
        self.root.minsize(680, 570)
        self.root.configure(bg="#f4f6fb")

        self.events = queue.Queue()
        self.downloading = False
        self.download_thread = None
        self.cancel_event = threading.Event()

        self.folder_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.url_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Pronto para baixar.")
        self.progress_var = tk.DoubleVar(value=0)
        self.percent_var = tk.StringVar(value="0%")
        self.current_file_var = tk.StringVar(value="Nenhum download em andamento")

        self._configure_style()
        self._build_ui()
        self._poll_events()

    def _configure_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#f4f6fb")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("TLabel", background="#f4f6fb", foreground="#172033", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 21, "bold"), foreground="#172033")
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10), foreground="#667085")
        style.configure("CardTitle.TLabel", background="#ffffff", font=("Segoe UI", 11, "bold"), foreground="#172033")
        style.configure("CardText.TLabel", background="#ffffff", foreground="#475467")
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 8))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(16, 10))
        style.configure("Horizontal.TProgressbar", troughcolor="#e8ecf4", background="#4f46e5", thickness=12)

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=(24, 20, 24, 18))
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 18))
        ttk.Label(header, text="YouTube Downloader", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Baixe um video ou o áudio de um vídeo e salve em MP3 diretamente do Youtube.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        # Destination card
        folder_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        folder_card.pack(fill="x", pady=(0, 12))
        ttk.Label(folder_card, text="1. Pasta de destino", style="CardTitle.TLabel").pack(anchor="w")
        folder_row = ttk.Frame(folder_card, style="Card.TFrame")
        folder_row.pack(fill="x", pady=(10, 0))
        self.folder_entry = ttk.Entry(folder_row, textvariable=self.folder_var)
        self.folder_entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.browse_button = ttk.Button(folder_row, text="Selecionar pasta…", command=self.choose_folder)
        self.browse_button.pack(side="left", padx=(10, 0))

        # URL card
        url_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        url_card.pack(fill="x", pady=(0, 12))
        ttk.Label(url_card, text="2. Link do vídeo", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            url_card,
            text="Cole a URL de um vídeo do YouTube. O nome do arquivo será baseado no título do vídeo.",
            style="CardText.TLabel",
        ).pack(anchor="w", pady=(4, 8))
        url_row = ttk.Frame(url_card, style="Card.TFrame")
        url_row.pack(fill="x")
        self.url_entry = ttk.Entry(url_row, textvariable=self.url_var)
        self.url_entry.pack(fill="x", expand=True, ipady=6)
        self.url_entry.bind("<Return>", lambda _event: self.start_download())

        action_row = ttk.Frame(url_card, style="Card.TFrame")
        action_row.pack(fill="x", pady=(12, 0))
        self.download_button = ttk.Button(
            action_row,
            text="⬇  Baixar áudio MP3",
            style="Accent.TButton",
            command=lambda: self.start_download("audio"),
        )
        self.download_button.pack(side="left")

        self.video_button = ttk.Button(
            action_row,
            text="🎬  Baixar vídeo",
            style="Accent.TButton",
            command=lambda: self.start_download("video"),
        )
        self.video_button.pack(side="left", padx=(8, 0))

        self.open_folder_button = ttk.Button(action_row, text="Abrir pasta", command=self.open_folder)
        self.open_folder_button.pack(side="left", padx=(8, 0))
        self.cancel_button = ttk.Button(action_row, text="Cancelar", command=self.cancel_download, state="disabled")
        self.cancel_button.pack(side="right")

        # Progress card
        progress_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        progress_card.pack(fill="x", pady=(0, 12))
        progress_head = ttk.Frame(progress_card, style="Card.TFrame")
        progress_head.pack(fill="x")
        ttk.Label(progress_head, text="3. Progresso", style="CardTitle.TLabel").pack(side="left")
        ttk.Label(progress_head, textvariable=self.percent_var, style="CardText.TLabel").pack(side="right")
        self.progress = ttk.Progressbar(
            progress_card, orient="horizontal", mode="determinate", maximum=100, variable=self.progress_var
        )
        self.progress.pack(fill="x", pady=(10, 8))
        ttk.Label(progress_card, textvariable=self.status_var, style="CardText.TLabel").pack(anchor="w")
        ttk.Label(progress_card, textvariable=self.current_file_var, style="CardText.TLabel").pack(
            anchor="w", pady=(4, 0)
        )

        # Log card
        log_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        log_card.pack(fill="both", expand=True)
        ttk.Label(log_card, text="Atividade", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 8))
        log_frame = ttk.Frame(log_card, style="Card.TFrame")
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(
            log_frame, height=7, wrap="word", state="disabled", relief="flat",
            bg="#f8fafc", fg="#344054", font=("Consolas", 9), padx=10, pady=8
        )
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        footer = ttk.Label(
            outer,
            text="Use somente para conteúdo que você tem autorização para baixar. Requer internet e FFmpeg.",
            style="Subtitle.TLabel",
        )
        footer.pack(anchor="w", pady=(12, 0))

    def choose_folder(self):
        selected = filedialog.askdirectory(
            title="Escolha a pasta onde o arquivo será salvos",
            initialdir=self.folder_var.get() if os.path.isdir(self.folder_var.get()) else str(Path.home()),
        )
        if selected:
            self.folder_var.set(selected)

    def open_folder(self):
        folder = self.folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("Pasta inválida", "Selecione uma pasta existente primeiro.")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as exc:
            messagebox.showerror("Não foi possível abrir", str(exc))

    def log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def start_download(self, mode="audio"):
        if self.downloading:
            return
        if yt_dlp is None:
            messagebox.showerror(
                "Dependência ausente",
                "A biblioteca yt-dlp não está instalada.\n\nAbra o terminal e execute:\npython -m pip install -U yt-dlp",
            )
            return

        url = self.url_var.get().strip()
        folder = self.folder_var.get().strip()

        if not url:
            messagebox.showwarning("Falta o link", "Cole o link de um vídeo do YouTube.")
            self.url_entry.focus_set()
            return
        if not (url.startswith("https://") or url.startswith("http://")):
            messagebox.showwarning("Link inválido", "Informe uma URL completa começando com https:// ou http://.")
            return
        if not folder:
            messagebox.showwarning("Falta a pasta", "Selecione uma pasta de destino.")
            return
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Pasta inválida", f"Não foi possível acessar a pasta:\n{exc}")
            return

        self.downloading = True
        self.cancel_event.clear()
        self.progress_var.set(0)
        self.percent_var.set("0%")
        self.status_var.set("Preparando download…")
        self.current_file_var.set("Obtendo informações do vídeo")
        self.download_button.configure(state="disabled")
        self.video_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.url_entry.configure(state="disabled")
        self.log(f"Iniciando: {url}")
        self.download_mode = mode
        self.download_thread = threading.Thread(
            target=self._download_worker,
            args=(url, folder, mode),
            daemon=True,
        )
        self.download_thread.start()

    def _download_worker(self, url, folder, mode):
        cancel_flag = {"cancelled": False}

        def progress_hook(data):
            if self.cancel_event.is_set():
                raise yt_dlp.utils.DownloadError("Download cancelado pelo usuário.")
            if data.get("status") == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                downloaded = data.get("downloaded_bytes", 0)
                percent = (downloaded / total * 100) if total else 0
                filename = os.path.basename(data.get("filename", "Baixando faixa de áudio…"))
                speed = data.get("_speed_str", "")
                eta = data.get("_eta_str", "")
                self.events.put(("progress", percent, filename, speed, eta))
            elif data.get("status") == "finished":
                self.events.put(("status", "Download recebido; convertendo para MP3…"))

        def logger_message(message):
            # Keep yt-dlp messages visible without overwhelming the UI.
            msg = str(message).strip()
            if msg:
                self.events.put(("log", msg))

        options = {
            "format": (
                "bestaudio/best"
                if mode == "audio"
                else "bestvideo+bestaudio/best"
            ),
            "outtmpl": os.path.join(folder, "%(title)s.%(ext)s"),
            "noplaylist": True,
            "windowsfilenames": True,
            "restrictfilenames": False,
            "overwrites": False,
            "progress_hooks": [progress_hook],
            "logger": YtDlpLogger(self.events),
            "quiet": True,
            "no_warnings": False,
        }

        if mode == "audio":
            options["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        else:
            options["merge_output_format"] = "mp4"
            
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title") or "áudio"
            self.events.put(("success", title, folder, mode))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def cancel_download(self):
        if self.downloading:
            self.cancel_event.set()
            self.status_var.set("Solicitando cancelamento…")
            self.cancel_button.configure(state="disabled")
            self.log("Cancelamento solicitado.")

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "progress":
                    _, percent, filename, speed, eta = event
                    self.progress_var.set(max(0, min(100, percent)))
                    self.percent_var.set(f"{percent:.1f}%")
                    self.current_file_var.set(filename)
                    parts = ["Baixando áudio"]
                    if speed:
                        parts.append(f"velocidade: {speed}")
                    if eta:
                        parts.append(f"tempo restante: {eta}")
                    self.status_var.set(" • ".join(parts))
                elif kind == "status":
                    self.status_var.set(event[1])
                    self.progress_var.set(100)
                    self.percent_var.set("100%")
                elif kind == "log":
                    self.log(event[1])
                elif kind == "success":
                    _, title, folder, mode = event

                    extension = ".mp3" if mode == "audio" else ".mp4"
                    kind_name = "Áudio" if mode == "audio" else "Vídeo"

                    self.downloading = False
                    self.progress_var.set(100)
                    self.percent_var.set("100%")
                    self.status_var.set("Download concluído!")
                    self.current_file_var.set(f"{safe_title(title)}{extension}")
                    self.log(f"Concluído: {safe_title(title)}{extension}")
                    self.log(f"Salvo em: {folder}")
                    self._set_idle()

                    messagebox.showinfo(
                        "Concluído",
                        f"{kind_name} salvo em:\n{folder}",
                    )
                elif kind == "error":
                    self.downloading = False
                    if self.cancel_event.is_set():
                        self.status_var.set("Download cancelado.")
                        self.current_file_var.set("Nenhum download em andamento")
                        self.log("Download cancelado pelo usuário.")
                        self._set_idle()
                        continue
                    self.status_var.set("Não foi possível concluir o download.")
                    self.current_file_var.set("Verifique o link, a conexão e as dependências.")
                    self.log(f"ERRO: {event[1]}")
                    self._set_idle()
                    messagebox.showerror(
                        "Erro no download",
                        "Não foi possível baixar ou converter o áudio.\n\n"
                        + event[1]
                        + "\n\nConfirme se o FFmpeg está instalado e atualizado.",
                    )
        except queue.Empty:
            pass
        self.root.after(120, self._poll_events)

    def _set_idle(self):
        self.download_button.configure(state="normal")
        self.video_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self.url_entry.configure(state="normal")

class YtDlpLogger:
    def __init__(self, events):
        self.events = events

    def debug(self, message):
        pass

    def warning(self, message):
        self.events.put(("log", f"Aviso: {message}"))

    def error(self, message):
        self.events.put(("log", f"Erro: {message}"))


def main():
    root = tk.Tk()
    app = AudioDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
