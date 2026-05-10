# ─── ui/widgets.py ────────────────────────────────────────────────────────────
# Funções e classes utilitárias para construção da interface Tkinter.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from config import C


# ── Primitivas de estilo ─────────────────────────────────────────────────────

def card(parent: tk.Widget, **kw) -> tk.Frame:
    """Frame com borda sutil no estilo da paleta."""
    return tk.Frame(
        parent,
        bg=kw.pop('bg', C['surface']),
        highlightthickness=kw.pop('ht', 1),
        highlightbackground=kw.pop('hb', C['border']),
        **kw,
    )


def sep(parent: tk.Widget, padx: int = 0) -> tk.Frame:
    """Divisor horizontal de 1px."""
    f = tk.Frame(parent, bg=C['border'], height=1)
    f.pack(fill='x', padx=padx)
    return f


def lbl(parent: tk.Widget, text: str, size: int = 10, *,
        bold: bool = False, color: str | None = None,
        bg: str | None = None, **kw) -> tk.Label:
    return tk.Label(
        parent,
        text=text,
        font=('Segoe UI', size, 'bold' if bold else 'normal'),
        fg=color or C['text'],
        bg=bg or parent.cget('bg'),
        **kw,
    )


def btn(parent: tk.Widget, text: str, *,
        bg: str, fg: str, cmd=None,
        bold: bool = False, size: int = 10,
        padx: int = 14, pady: int = 7, **kw) -> tk.Button:
    return tk.Button(
        parent,
        text=text,
        font=('Segoe UI', size, 'bold' if bold else 'normal'),
        bg=bg, fg=fg,
        activebackground=bg, activeforeground=fg,
        relief='flat', cursor='hand2',
        padx=padx, pady=pady,
        command=cmd,
        **kw,
    )


# ── Configuração de estilo Treeview ─────────────────────────────────────────

def configurar_treeview_style(style_name: str = 'N.Treeview') -> None:
    style = ttk.Style()
    style.theme_use('clam')
    style.configure(
        style_name,
        background=C['surface'], foreground=C['text'],
        fieldbackground=C['surface'], rowheight=32,
        font=('Segoe UI', 10), borderwidth=0,
    )
    style.configure(
        f'{style_name}.Heading',
        background=C['surface2'], foreground=C['muted2'],
        font=('Segoe UI', 9, 'bold'), relief='flat',
    )
    style.map(
        style_name,
        background=[('selected', '#2A2E3A')],
        foreground=[('selected', C['accent'])],
    )
