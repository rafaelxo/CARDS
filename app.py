# ─── app.py ───────────────────────────────────────────────────────────────────
# Entry-point da aplicação. Orquestra câmera, OCR, campos e tabela.
# Toda lógica de domínio fica nos módulos especializados.
# ──────────────────────────────────────────────────────────────────────────────

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
from ui.widgets import btn, lbl, sep


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(APP_GEOMETRY)
        self.root.configure(bg=C['bg'])
        self.root.resizable(True, True)
        self.root.minsize(*APP_MINSIZE)

        # Estado da sessão — preenchido pelo SetupDialog
        self.data_sessao  = None
        self.excel_manager: ExcelManager | None = None
        self.registros: list[dict] = []
        self._pendente: dict | None = None
        self._cooldown = OCR_COOLDOWN_DEFAULT

        self._build()
        self._bind_keys()

        # Abre o dialog de configuração inicial
        self.root.after(100, self._abrir_setup)

    # ── Setup inicial ─────────────────────────────────────────────────────────
    def _abrir_setup(self) -> None:
        dlg = SetupDialog(self.root)
        self.root.wait_window(dlg)

        if dlg.resultado is None:
            # Usuário cancelou — fecha o app
            self.root.destroy()
            return

        self.data_sessao   = dlg.resultado['data']
        self.excel_manager = ExcelManager(dlg.resultado['planilha'])

        dias = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
        d = self.data_sessao
        self._lbl_data_sessao.config(
            text=f'Sessão: {dias[d.weekday()]}  {d.strftime("%d/%m/%Y")}',
            fg=C['accent2'],
        )
        self._lbl_status.config(
            text='Sessão configurada — inicie a câmera', fg=C['muted2'])

        # Conecta edição de campos ao estado da sessão
        self._fields_block.configurar(
            self.root,
            self.data_sessao,
            self._on_campo_editado,
        )

        # Pré-carrega o reader OCR em background
        if OCR_ENGINE == 'easyocr':
            threading.Thread(target=self._precarregar_ocr, daemon=True).start()

    def _precarregar_ocr(self) -> None:
        self._set_status('Preparando OCR…', C['warn'])
        try:
            get_reader()
            self._set_status('OCR pronto', C['accent2'])
        except Exception as e:
            self._set_status(f'Falha OCR: {str(e)[:60]}', C['danger'])

    # ── Layout ───────────────────────────────────────────────────────────────
    def _build(self) -> None:
        body = tk.Frame(self.root, bg=C['bg'])
        body.pack(fill='both', expand=True)

        # ── Coluna esquerda
        left = tk.Frame(body, bg=C['bg'], width=PREVIEW_W + 34)
        left.pack(side='left', fill='y', padx=12, pady=8)
        left.pack_propagate(False)

        self._cam_block = CameraBlock(
            left,
            on_frame=self._on_frame_ocr,
            on_status=self._set_status,
            get_cooldown=lambda: self._cooldown,
            preview_w=PREVIEW_W,
            preview_h=PREVIEW_H,
        )
        self._cam_block.pack(fill='x')

        self._fields_block = FieldsBlock(left)
        self._fields_block.pack(fill='x')

        self._build_controles(left)

        # Divisor vertical
        tk.Frame(body, bg=C['border'], width=1).pack(
            side='left', fill='y', pady=12)

        # ── Coluna direita
        right = tk.Frame(body, bg=C['bg'])
        right.pack(side='right', fill='both', expand=True, padx=12, pady=8)

        self._table_block = TableBlock(
            right,
            on_exportar=self._exportar,
            on_limpar=self._limpar,
        )
        self._table_block.pack(fill='both', expand=True)

    def _build_controles(self, parent: tk.Widget) -> None:
        from ui.widgets import card

        c = card(parent)
        c.pack(fill='x', pady=(0, 6), side='bottom')

        # Intervalo de leitura
        ir = tk.Frame(c, bg=C['surface'])
        ir.pack(fill='x', padx=14, pady=(10, 6))
        lbl(ir, 'Intervalo de leitura:', 8, color=C['muted']).pack(side='left')
        self._lbl_int = lbl(ir, '3.0s', 8, color=C['accent2'])
        self._lbl_int.pack(side='right')
        var = tk.DoubleVar(value=self._cooldown)
        tk.Scale(
            ir, from_=1, to=8, resolution=0.5, orient='horizontal',
            variable=var, bg=C['surface'], fg=C['muted'],
            troughcolor=C['surface2'], highlightthickness=0,
            showvalue=False, sliderlength=14,
            command=lambda v: self._set_cooldown(float(v)),
        ).pack(side='left', fill='x', expand=True, padx=6)

        # Data da sessão
        self._lbl_data_sessao = lbl(
            c, 'Sessão: não configurada', 8, color=C['muted'])
        self._lbl_data_sessao.pack(anchor='w', padx=14, pady=(0, 4))

        # Status
        self._lbl_status = lbl(c, 'Aguardando configuração…', 8, color=C['muted'])
        self._lbl_status.pack(anchor='w', padx=14, pady=(0, 10))

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def _on_frame_ocr(self, roi) -> None:
        """Chamado pela CameraBlock quando um frame novo deve ser processado."""
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
        self._set_status('Nota identificada — Enter p/ aceitar, Backspace p/ rejeitar',
                          C['accent2'])

    def _on_campo_editado(self, tipo: str, valor) -> None:
        """Callback chamado quando o usuário edita um campo manualmente."""
        if self._pendente:
            if tipo == 'bandeira':
                self._pendente['bandeira'] = valor
            elif tipo == 'tipo':
                self._pendente['tipo'] = valor
            elif tipo == 'valor':
                self._pendente['valor'] = valor
            elif tipo == 'data':
                self._pendente['data'] = valor

    def _aceitar(self, _event=None) -> None:
        if not self._pendente:
            return
        # Pega valores possivelmente editados pelo usuário
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
            total = self.excel_manager.anexar_sessao(
                self.registros, self.data_sessao)
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

    # ── Utilitários ──────────────────────────────────────────────────────────
    def _set_status(self, msg: str, color: str) -> None:
        self.root.after(0, lambda: self._lbl_status.config(text=msg, fg=color))

    def _set_cooldown(self, v: float) -> None:
        self._cooldown = v
        self._lbl_int.config(text=f'{v:.1f}s')

    def _bind_keys(self) -> None:
        self.root.bind('<Return>',    self._aceitar)
        self.root.bind('<BackSpace>', self._rejeitar)

    def on_close(self) -> None:
        self._cam_block.parar()
        self.root.destroy()


# ── Entry-point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    root = tk.Tk()
    app  = App(root)
    root.protocol('WM_DELETE_WINDOW', app.on_close)
    root.mainloop()
