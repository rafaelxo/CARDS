# ─── ui/table_block.py ────────────────────────────────────────────────────────
# Painel direito: tabela de subtotais por bandeira/tipo e rodapé com total geral.
# Inclui botões de "Anexar relatório" e "Limpar".
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from collections import defaultdict
from typing import Callable

import tkinter as tk
from tkinter import ttk

from config import C
from ui.widgets import btn, card, configurar_treeview_style, lbl, sep


def _fmt_brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


class TableBlock(tk.Frame):
    """
    Painel direito com tabela de subtotais e rodapé de total.

    Callbacks:
        on_exportar()   — botão "Anexar relatório diário"
        on_limpar()     — botão "Limpar"
    """

    def __init__(self, parent: tk.Widget,
                 on_exportar: Callable[[], None],
                 on_limpar: Callable[[], None]):
        super().__init__(parent, bg=C['bg'])
        self._on_exportar = on_exportar
        self._on_limpar   = on_limpar
        self._subtotais: dict[tuple, dict] = {}
        self._build()

    # ── Layout ───────────────────────────────────────────────────────────────
    def _build(self) -> None:
        # Cabeçalho com botões
        hdr = tk.Frame(self, bg=C['bg'])
        hdr.pack(fill='x', pady=(0, 8))
        lbl(hdr, 'Totalizador da sessão', 13, bold=True,
            bg=C['bg']).pack(side='left')

        btn(hdr, '✕ Limpar',
            bg=C['surface'], fg=C['danger'],
            cmd=self._on_limpar,
        ).pack(side='right')

        btn(hdr, '📎  Anexar relatório diário',
            bg=C['accent2'], fg=C['bg'],
            cmd=self._on_exportar, bold=True,
        ).pack(side='right', padx=(0, 8))

        # Treeview
        configurar_treeview_style('N.Treeview')
        c = card(self)
        c.pack(fill='both', expand=True)

        cols = ('bandeira', 'tipo', 'qtd', 'valor')
        self._tree = ttk.Treeview(c, columns=cols, show='headings',
                                   style='N.Treeview')

        for col, label, w in [
            ('bandeira', 'Bandeira', 220),
            ('tipo',     'Tipo',     120),
            ('qtd',      'Qtd',       70),
            ('valor',    'Valor Total', 160),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=w, anchor='center', minwidth=60)

        self._tree.tag_configure('even',  background='#161A21', foreground=C['text'])
        self._tree.tag_configure('odd',   background=C['surface'], foreground=C['text'])
        self._tree.tag_configure(
            'total',
            background='#0D1320',
            foreground=C['accent2'],
            font=('Segoe UI', 10, 'bold'),
        )

        sb = ttk.Scrollbar(c, orient='vertical', command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side='left', fill='both', expand=True, padx=(12, 0), pady=8)
        sb.pack(side='right', fill='y', pady=8)

        # Rodapé
        sep(self)
        footer = tk.Frame(self, bg=C['surface'],
                          highlightthickness=1, highlightbackground=C['border'])
        footer.pack(fill='x')

        self._lbl_qtd = tk.Label(
            footer, text='0 notas',
            font=('Segoe UI', 11), fg=C['muted2'], bg=C['surface'],
        )
        self._lbl_qtd.pack(side='left', padx=16, pady=14)

        lbl(footer, 'Total geral:', 9, color=C['muted'],
            bg=C['surface']).pack(side='right', padx=(0, 4), pady=14)

        self._lbl_total = tk.Label(
            footer, text='R$ 0,00',
            font=('Segoe UI', 17, 'bold'), fg=C['accent2'], bg=C['surface'],
        )
        self._lbl_total.pack(side='right', padx=(0, 16), pady=14)

    # ── API pública ──────────────────────────────────────────────────────────
    def adicionar(self, reg: dict) -> None:
        """Atualiza subtotais e redesenha a tabela."""
        key = (reg['bandeira'], reg['tipo'])
        if key not in self._subtotais:
            self._subtotais[key] = {'qtd': 0, 'valor': 0.0}
        self._subtotais[key]['qtd']   += 1
        self._subtotais[key]['valor'] += reg['valor'] or 0.0
        self._redesenhar()

    def limpar(self) -> None:
        self._subtotais.clear()
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._lbl_qtd.config(text='0 notas')
        self._lbl_total.config(text='R$ 0,00')

    # ── Privado ──────────────────────────────────────────────────────────────
    def _redesenhar(self) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)

        total_qtd = 0
        total_val = 0.0
        for i, ((b, t), d) in enumerate(sorted(self._subtotais.items())):
            self._tree.insert(
                '', 'end',
                values=(b, t, d['qtd'], _fmt_brl(d['valor'])),
                tags=('even' if i % 2 == 0 else 'odd',),
            )
            total_qtd += d['qtd']
            total_val += d['valor']

        self._tree.insert(
            '', 'end',
            values=('TOTAL GERAL', '—', total_qtd, _fmt_brl(total_val)),
            tags=('total',),
        )
        self._lbl_qtd.config(
            text=f'{total_qtd} nota{"s" if total_qtd != 1 else ""}')
        self._lbl_total.config(text=_fmt_brl(total_val))
