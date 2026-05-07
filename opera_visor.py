#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
opera_visor.py — Visor de libreto + traducción sincronizada para foobar2000 (foo_run)
Uso: python opera_visor.py "%artist%" "%title%" "%path%"

Muestra dos paneles side-by-side:
  - Izquierda : texto original del aria (extraído por opera_libreto.py)
  - Derecha   : traducción al español (usando traductor.py / deep_translator)

El scroll de ambos paneles está sincronizado.
"""

import sys
import os
import re
import threading
import tkinter as tk
from tkinter import ttk, font as tkfont

# ── Rutas ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH   = os.path.join(os.path.expanduser("~"), "Desktop", "opera_visor_log.txt")

def log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

# ── Importar opera_libreto.py como módulo ────────────────────────────────────
sys.path.insert(0, SCRIPT_DIR)
try:
    import opera_libreto as libreto_mod
    LIBRETO_OK = True
except ImportError as e:
    LIBRETO_OK = False
    log(f"[ERROR] No se pudo importar opera_libreto: {e}")

# ── Importar traductor.py ─────────────────────────────────────────────────────
try:
    from traductor import traducir_a_espanol
    TRADUCTOR_OK = True
except ImportError as e:
    TRADUCTOR_OK = False
    log(f"[ERROR] No se pudo importar traductor: {e}")

    def traducir_a_espanol(texto):
        return "(Traducción no disponible: instala deep_translator)\npip install deep-translator"

# ── Extracción del aria (reutiliza opera_libreto.py) ─────────────────────────

def obtener_aria(artist_tag, title_tag, audio_path):
    """Llama a la lógica de opera_libreto y devuelve (info, texto_aria)."""
    if not LIBRETO_OK:
        return {}, "Error: opera_libreto.py no encontrado en la misma carpeta."

    # Leer título desde tag del archivo si es posible (igual que opera_libreto.main)
    if audio_path and os.path.exists(audio_path):
        try:
            ext = os.path.splitext(audio_path)[1].lower()
            if ext == '.flac' and libreto_mod.MUTAGEN_AVAILABLE:
                from mutagen.flac import FLAC as _FLAC
                _audio = _FLAC(audio_path)
                tag_title = _audio.get('title', [''])[0]
                if tag_title:
                    title_tag = tag_title
            elif ext == '.mp3' and libreto_mod.MUTAGEN_AVAILABLE:
                from mutagen.id3 import ID3 as _ID3
                _audio = _ID3(audio_path)
                tag_title = str(_audio.get('TIT2', ''))
                if tag_title:
                    title_tag = tag_title
        except Exception as e:
            log(f"[WARN] No se pudo leer tag title: {e}")

    info    = libreto_mod.parse_title(artist_tag, title_tag)
    libreto = libreto_mod.buscar_libreto(info)

    if not libreto:
        return info, "No se encontró el libreto en ninguna fuente."

    aria_texto = (libreto_mod.extract_aria(libreto, info["aria_text"], info["character"])
                  if info["aria_text"] else libreto)

    if not aria_texto:
        aria_texto = libreto

    return info, aria_texto


# ── Traducción por bloques (para no superar límite de Google) ─────────────────

def traducir_bloques(texto, max_chars=4500):
    """Divide el texto en bloques y traduce cada uno."""
    parrafos  = texto.split('\n')
    bloques   = []
    bloque    = []
    contador  = 0

    for p in parrafos:
        if contador + len(p) + 1 > max_chars and bloque:
            bloques.append('\n'.join(bloque))
            bloque   = [p]
            contador = len(p)
        else:
            bloque.append(p)
            contador += len(p) + 1

    if bloque:
        bloques.append('\n'.join(bloque))

    traducidos = []
    for b in bloques:
        if b.strip():
            try:
                traducidos.append(traducir_a_espanol(b))
            except Exception as e:
                traducidos.append(f"[Error traduciendo bloque: {e}]")
        else:
            traducidos.append('')

    return '\n'.join(traducidos)


# ── GUI ───────────────────────────────────────────────────────────────────────

class VisorOpera(tk.Tk):
    def __init__(self, info, texto_original):
        super().__init__()

        self.texto_original  = texto_original
        self.texto_traducido = ""
        self._sync_lock      = False   # evitar bucle recursivo en scroll

        # ── Ventana ──────────────────────────────────────────────────────────
        opera     = info.get("opera", "Ópera")
        aria      = info.get("aria_text", "")
        personaje = info.get("character", "")
        compositor= info.get("composer", "")

        titulo_ventana = f"{compositor} — {opera}"
        if aria:
            titulo_ventana += f'  ·  "{aria}"'
        if personaje:
            titulo_ventana += f"  ({personaje})"

        self.title(titulo_ventana)
        self.geometry("1400x800")
        self.configure(bg="#1a1a2e")
        self.minsize(800, 500)

        # ── Fuentes ───────────────────────────────────────────────────────────
        fuente_titulo = tkfont.Font(family="Georgia", size=13, weight="bold")
        fuente_texto  = tkfont.Font(family="Georgia", size=12)
        fuente_estado = tkfont.Font(family="Helvetica", size=10)

        # ── Cabecera ──────────────────────────────────────────────────────────
        frame_cab = tk.Frame(self, bg="#0f0f23", pady=10)
        frame_cab.pack(fill=tk.X)

        tk.Label(
            frame_cab,
            text=f"♪  {compositor}  —  {opera}",
            font=fuente_titulo,
            bg="#0f0f23", fg="#e0c97f"
        ).pack()

        if aria:
            tk.Label(
                frame_cab,
                text=f'"{aria}"' + (f"   ({personaje})" if personaje else ""),
                font=tkfont.Font(family="Georgia", size=11, slant="italic"),
                bg="#0f0f23", fg="#a0b8d8"
            ).pack()

        # ── Panel principal con dos columnas ──────────────────────────────────
        frame_main = tk.Frame(self, bg="#1a1a2e")
        frame_main.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 0))
        frame_main.columnconfigure(0, weight=1)
        frame_main.columnconfigure(1, weight=1)
        frame_main.rowconfigure(1, weight=1)

        # Etiquetas de columna
        lbl_cfg = dict(bg="#1a1a2e", fg="#7090b0",
                       font=tkfont.Font(family="Helvetica", size=10, weight="bold"),
                       pady=4)
        tk.Label(frame_main, text="ORIGINAL", **lbl_cfg).grid(row=0, column=0, sticky="w", padx=5)
        tk.Label(frame_main, text="TRADUCCIÓN (ES)", **lbl_cfg).grid(row=0, column=1, sticky="w", padx=5)

        # Separador central
        sep = tk.Frame(frame_main, bg="#3a3a5a", width=2)
        sep.grid(row=0, column=0, rowspan=2, sticky="nse", padx=(0,0))

        # Scrollbar compartida (vertical)
        self.scrollbar = tk.Scrollbar(frame_main, orient=tk.VERTICAL,
                                      bg="#2a2a4a", troughcolor="#1a1a2e",
                                      activebackground="#5a5a8a")
        self.scrollbar.grid(row=1, column=2, sticky="ns")

        # Text widget izquierdo — original
        self.txt_orig = tk.Text(
            frame_main,
            wrap=tk.WORD,
            font=fuente_texto,
            bg="#0d1117", fg="#e6edf3",
            insertbackground="white",
            selectbackground="#264f78",
            relief=tk.FLAT,
            padx=16, pady=12,
            spacing2=4,
            yscrollcommand=self._on_scroll_orig,
            state=tk.DISABLED,
            cursor="arrow",
        )
        self.txt_orig.grid(row=1, column=0, sticky="nsew", padx=(0, 2))

        # Text widget derecho — traducción
        self.txt_trad = tk.Text(
            frame_main,
            wrap=tk.WORD,
            font=fuente_texto,
            bg="#0d1117", fg="#c9d1d9",
            insertbackground="white",
            selectbackground="#264f78",
            relief=tk.FLAT,
            padx=16, pady=12,
            spacing2=4,
            yscrollcommand=self._on_scroll_trad,
            state=tk.DISABLED,
            cursor="arrow",
        )
        self.txt_trad.grid(row=1, column=1, sticky="nsew", padx=(2, 0))

        # Conectar scrollbar a ambos widgets
        self.scrollbar.config(command=self._scroll_ambos)

        # Bind mousewheel en ambos paneles
        for widget in (self.txt_orig, self.txt_trad):
            widget.bind("<MouseWheel>",  self._on_mousewheel)
            widget.bind("<Button-4>",   self._on_mousewheel)  # Linux scroll up
            widget.bind("<Button-5>",   self._on_mousewheel)  # Linux scroll down

        # ── Barra de estado ───────────────────────────────────────────────────
        self.frame_estado = tk.Frame(self, bg="#0f0f23", pady=4)
        self.frame_estado.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_estado = tk.Label(
            self.frame_estado,
            text="Cargando traducción...",
            font=fuente_estado,
            bg="#0f0f23", fg="#7090b0",
            anchor="w", padx=10
        )
        self.lbl_estado.pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(
            self.frame_estado, mode="indeterminate", length=120
        )
        self.progress.pack(side=tk.RIGHT, padx=10)

        # ── Volcar texto original ─────────────────────────────────────────────
        self._set_text(self.txt_orig, self.texto_original)

        # ── Traducir en hilo secundario ───────────────────────────────────────
        self.progress.start(10)
        hilo = threading.Thread(target=self._traducir_async, daemon=True)
        hilo.start()

    # ── Helpers de texto ──────────────────────────────────────────────────────

    def _set_text(self, widget, texto):
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, texto)
        widget.config(state=tk.DISABLED)

    # ── Traducción asíncrona ──────────────────────────────────────────────────

    def _traducir_async(self):
        try:
            traducido = traducir_bloques(self.texto_original)
        except Exception as e:
            traducido = f"Error en la traducción:\n{e}"
        self.texto_traducido = traducido
        # Actualizar GUI desde el hilo principal
        self.after(0, self._mostrar_traduccion)

    def _mostrar_traduccion(self):
        self._set_text(self.txt_trad, self.texto_traducido)
        self.progress.stop()
        self.progress.pack_forget()
        self.lbl_estado.config(text="✓ Traducción completada")

    # ── Scroll sincronizado ───────────────────────────────────────────────────

    def _on_scroll_orig(self, *args):
        self.scrollbar.set(*args)
        if not self._sync_lock:
            self._sync_lock = True
            self.txt_trad.yview_moveto(args[0])
            self._sync_lock = False

    def _on_scroll_trad(self, *args):
        self.scrollbar.set(*args)
        if not self._sync_lock:
            self._sync_lock = True
            self.txt_orig.yview_moveto(args[0])
            self._sync_lock = False

    def _scroll_ambos(self, *args):
        self.txt_orig.yview(*args)
        self.txt_trad.yview(*args)

    def _on_mousewheel(self, event):
        # Windows: event.delta; Linux: event.num
        if event.num == 4 or event.delta > 0:
            delta = -3
        else:
            delta = 3
        self.txt_orig.yview_scroll(delta, "units")
        self.txt_trad.yview_scroll(delta, "units")
        return "break"   # evitar que cada widget scrollee por su cuenta


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("=== opera_visor.py inicio ===\n")

    log(f"[INFO] argv: {sys.argv}")

    if len(sys.argv) < 3:
        log("[ERROR] Faltan argumentos. Uso: opera_visor.py <artist> <title...> <path>")
        # Modo demo si no hay argumentos
        info = {"composer": "Demo", "opera": "Sin argumentos",
                "aria_text": "", "character": ""}
        texto = "Ejecuta este script desde foobar2000 con foo_run.\n\nEjemplo:\npython opera_visor.py \"%artist%\" \"%title%\" \"%path%\""
        app = VisorOpera(info, texto)
        app.mainloop()
        return

    artist_tag = sys.argv[1]
    audio_path = sys.argv[-1]
    title_tag  = ", ".join(sys.argv[2:-1])

    log(f"[INFO] Artista   : {artist_tag}")
    log(f"[INFO] Título    : {title_tag}")
    log(f"[INFO] Audio     : {audio_path}")

    # Obtener aria (puede tardar unos segundos por la descarga del libreto)
    # Lo hacemos ANTES de abrir la ventana para tener el texto original listo
    # y luego la traducción se hace en background desde la GUI

    # Mostrar ventana de espera mínima mientras se descarga el libreto
    splash = tk.Tk()
    splash.title("Opera Visor — Buscando libreto...")
    splash.geometry("420x120")
    splash.configure(bg="#0f0f23")
    splash.resizable(False, False)
    tk.Label(splash, text="♪  Buscando libreto de ópera...",
             font=("Georgia", 13), bg="#0f0f23", fg="#e0c97f").pack(pady=20)
    pb = ttk.Progressbar(splash, mode="indeterminate", length=300)
    pb.pack()
    pb.start(10)
    splash.update()

    resultado = [None, None]

    def _buscar():
        info, texto = obtener_aria(artist_tag, title_tag, audio_path)
        resultado[0] = info
        resultado[1] = texto

    hilo = threading.Thread(target=_buscar, daemon=True)
    hilo.start()

    # Esperar a que termine la búsqueda actualizando el splash
    while hilo.is_alive():
        splash.update()
        splash.after(50)

    splash.destroy()

    info, texto_original = resultado
    log(f"[INFO] Texto obtenido: {len(texto_original)} chars")

    app = VisorOpera(info or {}, texto_original)
    app.mainloop()


if __name__ == "__main__":
    main()
