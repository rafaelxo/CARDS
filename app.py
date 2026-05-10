# ─── app.py ───────────────────────────────────────────────────────────────────

from __future__ import annotations

import threading
from datetime import datetime

import tkinter as tk
from tkinter import messagebox

from config import (
    APP_GEOMETRY, APP_MINSIZE, APP_TITLE,
    OCR_COOLDOWN_DEFAULT, PREVIEW_H, PREVIEW_W, C,
)
from excel_manager import ExcelManager, fmt_brl
from ocr_engine import get_reader, OCR_ENGINE, processar_frame
from ui.camera_block import CameraBlock
from ui.fields_block import FieldsBlock
from ui.setup_dialog import SetupDialog
from ui.table_block import TableBlock
from ui.widgets import btn, card, lbl, sep


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(APP_GEOMETRY)
        self.root.configure(bg=C['bg'])
        self.root.resizable(True, True)
        self.root.minsize(*APP_MINSIZE)

        self.data_sessao            = None
        self.excel_manager: ExcelManager | None = None
        self.registros: list[dict]  = []
        self._pendente: dict | None = None
        self._cooldown              = OCR_COOLDOWN_DEFAULT

        self._build()
        self._bind_keys()
        self.root.after(100, self._abrir_setup)

    # ── Setup ─────────────────────────────────────────────────────────────────
    def _abrir_setup(self) -> None:
        dlg = SetupDialog(self.root)
        self.root.wait_window(dlg)

        if dlg.resultado is None:
            self.root.destroy()
            return

        self.data_sessao   = dlg.resultado['data']
        self.excel_manager = ExcelManager(dlg.resultado['planilha'])

        dias = ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom']
        d = self.data_sessao
        self._lbl_data_sessao.config(
            text=f'Sessão: {dias[d.weekday()]}  {d.strftime("%d/%m/%Y")}',
            fg=C['accent2'],
        )
        self._set_status('Sessão configurada — inicie a câmera', C['muted2'])

        self._fields_block.configurar(
            self.root, self.data_sessao, self._on_campo_editado)

        if OCR_ENGINE == 'easyocr':
            threading.Thread(target=self._precarregar_ocr, daemon=True).start()

    def _precarregar_ocr(self) -> None:
        self._set_status('Preparando OCR…', C['warn'])
        try:
            get_reader()
            self._set_status('OCR pronto', C['accent2'])
        except Exception as e:
            self._set_status(f'Falha OCR: {str(e)[:60]}', C['danger'])

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self) -> None:
        body = tk.Frame(self.root, bg=C['bg'])
        body.pack(fill='both', expand=True)

        # Coluna esquerda — largura fixa
        left = tk.Frame(body, bg=C['bg'], width=PREVIEW_W + 34)
        left.pack(side='left', fill='y', padx=12, pady=8)
        left.pack_propagate(False)

        # 1) Câmera (com intervalo embutido)
        self._cam_block = CameraBlock(
            left,
            on_frame=self._on_frame_ocr,
            on_status=self._set_status,
            get_cooldown=lambda: self._cooldown,
            set_cooldown=self._set_cooldown,
            preview_w=PREVIEW_W,
            preview_h=PREVIEW_H,
        )
        self._cam_block.pack(fill='x')

        # 2) Campos OCR
        self._fields_block = FieldsBlock(left)
        self._fields_block.pack(fill='x')

        # 3) Rodapé (data sessão + status) — ancorado na base
        self._build_rodape(left)

        # Divisor
        tk.Frame(body, bg=C['border'], width=1).pack(
            side='left', fill='y', pady=12)

        # Coluna direita
        right = tk.Frame(body, bg=C['bg'])
        right.pack(side='right', fill='both', expand=True, padx=12, pady=8)
        self._table_block = TableBlock(
            right,
            on_exportar=self._exportar,
            on_limpar=self._limpar,
        )
        self._table_block.pack(fill='both', expand=True)

    def _build_rodape(self, parent: tk.Widget) -> None:
        c = card(parent)
        c.pack(fill='x', pady=(6, 0), side='bottom')

        self._lbl_data_sessao = lbl(
            c, 'Sessão: não configurada', 8, color=C['muted'])
        self._lbl_data_sessao.pack(anchor='w', padx=14, pady=(8, 2))

        self._lbl_status = lbl(c, 'Aguardando configuração…', 8, color=C['muted'])
        self._lbl_status.pack(anchor='w', padx=14, pady=(0, 8))

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def _on_frame_ocr(self, roi) -> None:
        self._set_status('Processando…', C['warn'])
        resultado = processar_frame(roi)
        if resultado is None:
            self._set_status('Valor não encontrado — reposicione a nota', C['muted'])
            return
        self.root.after(0, self._exibir_campos, resultado)

    def _exibir_campos(self, reg: dict) -> None:
        self._pendente = reg
        self._cam_block.marcar_pendente(True)
        self._fields_block.exibir(reg, self.data_sessao)
        self._set_status('Nota identificada — Enter: aceitar   Backspace: rejeitar',
                          C['accent2'])

    def _on_campo_editado(self, tipo: str, valor) -> None:
        if self._pendente:
            self._pendente[tipo] = valor

    def _aceitar(self, _event=None) -> None:
        if not self._pendente:
            return
        atual = self._fields_block.valores_atuais()
        reg = {**self._pendente, **atual}
        reg['status_data'] = 'OK' if reg['data'] == self.data_sessao else 'S/data'
        reg['hora'] = datetime.now().strftime('%H:%M:%S')
        self.registros.append(reg)
        self._table_block.adicionar(reg)
        self._limpar_campos()

    def _rejeitar(self, _event=None) -> None:
        if not self._pendente:
            return
        self._limpar_campos()
        self._set_status('Nota rejeitada — aguardando próxima…', C['muted'])

    def _limpar_campos(self) -> None:
        self._pendente = None
        self._cam_block.marcar_pendente(False)
        self._fields_block.limpar()
        self._set_status('Câmera ativa — posicione a nota na moldura', C['muted2'])

    # ── Exportação ────────────────────────────────────────────────────────────
    def _exportar(self) -> None:
        if not self.registros:
            messagebox.showwarning('Vazio', 'Nenhum registro para exportar.')
            return
        if self.excel_manager is None:
            messagebox.showerror('Erro', 'Planilha não configurada.')
            return
        try:
            total = self.excel_manager.anexar_sessao(self.registros, self.data_sessao)
            messagebox.showinfo(
                'Relatório anexado!',
                f'Dados adicionados à planilha:\n{self.excel_manager.caminho}\n\n'
                f'{len(self.registros)} nota(s) · {fmt_brl(total)}',
            )
        except Exception as e:
            messagebox.showerror('Erro ao exportar', str(e))

    def _limpar(self) -> None:
        if self.registros and messagebox.askyesno('Limpar', 'Limpar todos os registros?'):
            self.registros.clear()
            self._table_block.limpar()

    # ── Utilitários ───────────────────────────────────────────────────────────
    def _set_status(self, msg: str, color: str) -> None:
        self.root.after(0, lambda: self._lbl_status.config(text=msg, fg=color))

    def _set_cooldown(self, v: float) -> None:
        self._cooldown = v

    def _bind_keys(self) -> None:
        self.root.bind('<Return>',    self._aceitar)
        self.root.bind('<BackSpace>', self._rejeitar)

    def on_close(self) -> None:
        self._cam_block.parar()
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app  = App(root)
    root.protocol('WM_DELETE_WINDOW', app.on_close)
    root.mainloop()
