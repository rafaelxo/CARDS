# ─── ui/camera_block.py ───────────────────────────────────────────────────────

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

import cv2
import numpy as np
from PIL import Image, ImageOps, ImageTk

import tkinter as tk
from config import C, CAM_FPS, CAM_HEIGHT, CAM_WIDTH, OCR_DIFF_THRESHOLD, OCR_THUMB_SIZE
from ui.widgets import btn, card, lbl


class CameraBlock(tk.Frame):
    def __init__(self, parent: tk.Widget,
                 on_frame: Callable[[np.ndarray], None],
                 on_status: Callable[[str, str], None],
                 get_cooldown: Callable[[], float],
                 set_cooldown: Callable[[float], None],
                 preview_w: int, preview_h: int):
        super().__init__(parent, bg=C['bg'])

        self._on_frame     = on_frame
        self._on_status    = on_status
        self._get_cooldown = get_cooldown
        self._set_cooldown = set_cooldown
        self.preview_w     = preview_w
        self.preview_h     = preview_h

        self._cap: Optional[cv2.VideoCapture] = None
        self._capturando           = False
        self._pendente_confirmacao = False
        self._ultimo_ocr           = 0.0
        self._ocr_rodando          = False
        self._ultimo_roi: Optional[np.ndarray] = None
        self._lock                 = threading.Lock()

        self._build()

    def _build(self) -> None:
        c = card(self)
        c.pack(fill='x', pady=(0, 8))

        # Header
        hdr = tk.Frame(c, bg=C['surface'])
        hdr.pack(fill='x', padx=14, pady=(10, 6))
        lbl(hdr, 'Câmera ao vivo', 11, bold=True).pack(side='left')
        self._badge = tk.Label(
            hdr, text=' INATIVA ',
            font=('Segoe UI', 8, 'bold'),
            fg=C['muted'], bg=C['surface2'], padx=6, pady=2,
        )
        self._badge.pack(side='right')

        # Preview — sem wrap extra, sem bordas pretas
        self._lbl_cam = tk.Label(
            c, bg=C['surface'],
            text='sem sinal', font=('Segoe UI', 10), fg=C['muted'],
        )
        self._lbl_cam.pack(fill='x', padx=0, pady=0)

        # Botão câmera
        self._btn_cam = btn(
            c, '▶  Iniciar câmera',
            bg=C['accent'], fg=C['bg'],
            cmd=self._toggle,
            bold=True, size=10, padx=12, pady=7,
        )
        self._btn_cam.pack(fill='x', padx=14, pady=(8, 4))

        # Intervalo — logo abaixo do botão
        ir = tk.Frame(c, bg=C['surface'])
        ir.pack(fill='x', padx=14, pady=(0, 10))
        lbl(ir, 'Intervalo de leitura:', 8, color=C['muted']).pack(side='left')
        self._lbl_int = lbl(ir, '3.0s', 8, color=C['accent2'])
        self._lbl_int.pack(side='right')
        self._var_int = tk.DoubleVar(value=self._get_cooldown())
        tk.Scale(
            ir, from_=1, to=8, resolution=0.5, orient='horizontal',
            variable=self._var_int, bg=C['surface'], fg=C['muted'],
            troughcolor=C['surface2'], highlightthickness=0,
            showvalue=False, sliderlength=14,
            command=self._on_slider,
        ).pack(side='left', fill='x', expand=True, padx=6)

    def _on_slider(self, v: str) -> None:
        val = float(v)
        self._set_cooldown(val)
        self._lbl_int.config(text=f'{val:.1f}s')

    # ── Controles públicos ────────────────────────────────────────────────────
    def marcar_pendente(self, ativo: bool) -> None:
        self._pendente_confirmacao = ativo

    def parar(self) -> None:
        self._parar_cam()

    # ── Câmera ────────────────────────────────────────────────────────────────
    def _toggle(self) -> None:
        if self._capturando:
            self._parar_cam()
        else:
            self._iniciar_cam()

    def _iniciar_cam(self) -> None:
        self._cap = cv2.VideoCapture(0)
        if not self._cap.isOpened():
            from tkinter import messagebox
            messagebox.showerror('Erro', 'Câmera não encontrada.\nVerifique a conexão.')
            return
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
        self._capturando = True
        self._btn_cam.config(text='■  Parar câmera',
                              bg=C['danger'], activebackground=C['danger'])
        self._badge.config(text=' ATIVA ', fg=C['accent2'], bg='#0D2E22')
        self._on_status('Câmera ativa — posicione a nota na moldura', C['muted2'])
        threading.Thread(target=self._loop, daemon=True).start()

    def _parar_cam(self) -> None:
        self._capturando = False
        self._ocr_rodando = False
        if self._cap:
            self._cap.release()
        self._btn_cam.config(text='▶  Iniciar câmera',
                              bg=C['accent'], activebackground=C['accent'])
        self._badge.config(text=' INATIVA ', fg=C['muted'], bg=C['surface2'])
        self._lbl_cam.config(image='', text='sem sinal')
        self._on_status('Câmera inativa', C['muted'])

    def _loop(self) -> None:
        frame_interval = 1.0 / CAM_FPS

        while self._capturando:
            t0 = time.monotonic()
            ret, frame = self._cap.read()
            if not ret:
                break

            h, w = frame.shape[:2]
            mx, my = int(w * .04), int(h * .04)

            display = frame.copy()
            if self._pendente_confirmacao:
                txt, cor = 'AGUARDANDO CONFIRMAÇÃO...', (245, 166, 35)
            elif self._ocr_rodando:
                txt, cor = 'LENDO...', (56, 217, 169)
            else:
                txt, cor = 'POSICIONE A NOTA', (79, 142, 247)

            cv2.rectangle(display, (mx, my), (w - mx, h - my), cor, 2)
            cv2.putText(display, txt, (mx + 4, my - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.44, cor, 1)

            # Disparo OCR
            if not self._pendente_confirmacao and not self._ocr_rodando:
                agora = time.monotonic()
                if agora - self._ultimo_ocr >= self._get_cooldown():
                    roi = frame[my: h - my, mx: w - mx].copy()
                    thumb = cv2.resize(roi, OCR_THUMB_SIZE, interpolation=cv2.INTER_AREA)
                    similar = (
                        self._ultimo_roi is not None
                        and float(cv2.absdiff(thumb, self._ultimo_roi).mean()) < OCR_DIFF_THRESHOLD
                    )
                    if not similar:
                        self._ultimo_roi = thumb
                        self._ultimo_ocr = agora
                        self._ocr_rodando = True
                        threading.Thread(target=self._processar_wrapper,
                                         args=(roi,), daemon=True).start()

            # Preview sem bordas pretas — crop centralizado
            rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
            img = ImageOps.fit(Image.fromarray(rgb),
                               (self.preview_w, self.preview_h),
                               Image.BILINEAR, centering=(0.5, 0.5))
            imgtk = ImageTk.PhotoImage(img)
            self.after(0, self._set_preview, imgtk)

            elapsed = time.monotonic() - t0
            time.sleep(max(0, frame_interval - elapsed))

    def _processar_wrapper(self, roi: np.ndarray) -> None:
        try:
            self._on_frame(roi)
        finally:
            self._ocr_rodando = False

    def _set_preview(self, imgtk: ImageTk.PhotoImage) -> None:
        self._lbl_cam.configure(image=imgtk, text='')
        self._lbl_cam.image = imgtk
