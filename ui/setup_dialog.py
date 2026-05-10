# ─── ui/setup_dialog.py ───────────────────────────────────────────────────────
# Dialog modal exibido na inicialização do app.
# Coleta: (1) data das notinhas, (2) caminho da planilha mestre.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import os
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox

from config import C
from ui.widgets import btn, card, lbl, sep


class SetupDialog(tk.Toplevel):
    """
    Janela modal de configuração inicial.
    Resultado acessível em `.resultado` após fechar:
        {'data': date, 'planilha': str}  ou  None se cancelado.
    """

    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.title('Configuração da sessão')
        self.resizable(False, False)
        self.configure(bg=C['bg'])
        self.grab_set()           # modal
        self.protocol('WM_DELETE_WINDOW', self._cancelar)

        self.resultado: dict | None = None
        self._planilha_path = tk.StringVar(value='')

        hoje = date.today()
        self._var_d = tk.StringVar(value=f'{hoje.day:02d}')
        self._var_m = tk.StringVar(value=f'{hoje.month:02d}')
        self._var_a = tk.StringVar(value=str(hoje.year))

        self._build()
        self._centralizar(parent)

    # ── Layout ───────────────────────────────────────────────────────────────
    def _build(self) -> None:
        pad = dict(padx=24, pady=6)

        # Título
        lbl(self, 'Nova sessão de leitura', 14, bold=True,
            bg=C['bg']).pack(pady=(24, 2), **{k: v for k, v in pad.items() if k == 'padx'})
        lbl(self, 'Configure a data e selecione a planilha antes de iniciar.',
            9, color=C['muted'], bg=C['bg']).pack(padx=24, pady=(0, 14))

        sep(self, padx=0)

        # ── Data da sessão ───────────────────────────────────────────────────
        bloco = card(self)
        bloco.pack(fill='x', padx=20, pady=(16, 8))

        lbl(bloco, 'DATA DAS NOTINHAS', 8, bold=True,
            color=C['muted']).pack(anchor='w', padx=14, pady=(10, 4))

        row = tk.Frame(bloco, bg=C['surface'])
        row.pack(padx=14, pady=(0, 12))

        def _entry(parent, var, w, label):
            f = tk.Frame(parent, bg=C['surface'])
            f.pack(side='left', padx=4)
            lbl(f, label, 7, color=C['muted2']).pack()
            tk.Entry(
                f, textvariable=var, width=w,
                font=('Segoe UI', 13, 'bold'),
                bg=C['surface2'], fg=C['text'],
                insertbackground=C['accent'],
                relief='flat', justify='center',
            ).pack(ipady=6)

        _entry(row, self._var_d, 3,  'DIA')
        lbl(row, '/', 14, color=C['muted'], bg=C['surface']).pack(side='left', pady=4)
        _entry(row, self._var_m, 3,  'MÊS')
        lbl(row, '/', 14, color=C['muted'], bg=C['surface']).pack(side='left', pady=4)
        _entry(row, self._var_a, 5,  'ANO')

        # ── Planilha mestre ──────────────────────────────────────────────────
        bloco2 = card(self)
        bloco2.pack(fill='x', padx=20, pady=(0, 8))

        lbl(bloco2, 'PLANILHA MESTRE (.xlsx)', 8, bold=True,
            color=C['muted']).pack(anchor='w', padx=14, pady=(10, 4))

        row2 = tk.Frame(bloco2, bg=C['surface'])
        row2.pack(fill='x', padx=14, pady=(0, 12))

        self._lbl_arquivo = tk.Label(
            row2,
            textvariable=self._planilha_path,
            text='Nenhum arquivo selecionado',
            font=('Segoe UI', 9),
            fg=C['muted'], bg=C['surface'],
            anchor='w', width=38,
        )
        self._lbl_arquivo.pack(side='left', fill='x', expand=True)

        btn(row2, '📂  Selecionar',
            bg=C['accent'], fg=C['bg'],
            cmd=self._selecionar_arquivo,
            bold=True, size=9, padx=10, pady=5,
        ).pack(side='right', padx=(8, 0))

        lbl(bloco2,
            'Pode selecionar uma planilha existente ou criar uma nova.',
            8, color=C['muted2']).pack(anchor='w', padx=14, pady=(0, 10))

        sep(self, padx=0)

        # ── Botões ───────────────────────────────────────────────────────────
        rodape = tk.Frame(self, bg=C['bg'])
        rodape.pack(fill='x', padx=20, pady=16)

        btn(rodape, 'Cancelar',
            bg=C['surface'], fg=C['muted'],
            cmd=self._cancelar, size=10,
        ).pack(side='left')

        btn(rodape, '✓  Iniciar sessão',
            bg=C['accent2'], fg=C['bg'],
            cmd=self._confirmar, bold=True, size=10,
        ).pack(side='right')

    # ── Ações ────────────────────────────────────────────────────────────────
    def _selecionar_arquivo(self) -> None:
        caminho = filedialog.askopenfilename(
            title='Selecionar planilha mestre',
            filetypes=[('Excel', '*.xlsx'), ('Todos', '*.*')],
        )
        if not caminho:
            # Usuário pode também criar uma nova
            caminho = filedialog.asksaveasfilename(
                title='Ou criar nova planilha…',
                defaultextension='.xlsx',
                filetypes=[('Excel', '*.xlsx')],
            )
        if caminho:
            self._planilha_path.set(caminho)
            nome = os.path.basename(caminho)
            self._lbl_arquivo.config(
                text=nome, fg=C['accent2'],
                textvariable=None,          # desprende StringVar para texto estático
            )

    def _confirmar(self) -> None:
        if not self._planilha_path.get():
            messagebox.showwarning(
                'Planilha não selecionada',
                'Selecione ou crie uma planilha antes de continuar.',
                parent=self,
            )
            return
        try:
            d = int(self._var_d.get())
            m = int(self._var_m.get())
            a = int(self._var_a.get())
            data = date(a, m, d)
        except (ValueError, TypeError):
            messagebox.showerror('Data inválida',
                                 'Verifique os campos de data.', parent=self)
            return

        self.resultado = {'data': data, 'planilha': self._planilha_path.get()}
        self.destroy()

    def _cancelar(self) -> None:
        self.resultado = None
        self.destroy()

    # ── Utilitário ───────────────────────────────────────────────────────────
    def _centralizar(self, parent: tk.Tk) -> None:
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_x(), parent.winfo_y()
        w, h = self.winfo_width(), self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f'+{x}+{y}')
