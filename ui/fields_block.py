# ─── ui/fields_block.py ───────────────────────────────────────────────────────
# Painel de campos detectados pelo OCR.
# Bandeira → dropdown filtrável
# Tipo     → dropdown filtrável
# Valor    → entrada numérica inline
# Data     → calendário popup
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations
import re
import tkinter as tk
from datetime import date
from typing import Callable, Optional
from config import C

# Espelho exato do Config da planilha (ListaBandeiras)
BANDEIRAS = [
    'Visa', 'Visa Pré-pago',
    'Mastercard', 'Mastercard Pré-pago',
    'Elo', 'Elo Pré-pago',
    'Hipercard', 'American Express',
    'Cabal', 'Cabal Pré-pago',
    'Alelo',
    'PIX',
]

# Espelho exato do Config da planilha (ListaTipos)
TIPOS = [
    'Débito à Vista',
    'Crédito à Vista',
    'Sicoob',
    'Caixa',
    'PIX',
]


def _fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(',','X').replace('.',',').replace('X','.')


def _parse_brl(texto: str) -> Optional[float]:
    s = re.sub(r'[^\d,.]', '', texto)
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        v = float(s)
        return v if 0.01 <= v <= 99_999.99 else None
    except ValueError:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Dropdown filtrável
# ═══════════════════════════════════════════════════════════════════════════════
class _Dropdown(tk.Toplevel):
    def __init__(self, anchor: tk.Widget, opcoes: list[str],
                 atual: str, on_select: Callable[[str], None]):
        super().__init__(anchor)
        self.overrideredirect(True)
        self.configure(bg=C['border'])
        self._opcoes    = opcoes
        self._on_select = on_select

        top = tk.Frame(self, bg=C['surface2'])
        top.pack(fill='x', padx=1, pady=(1, 0))
        tk.Label(top, text='🔍', bg=C['surface2'], fg=C['muted'],
                 font=('Segoe UI', 10)).pack(side='left', padx=(8, 4))
        self._sv = tk.StringVar()
        self._sv.trace_add('write', self._filtrar)
        e = tk.Entry(top, textvariable=self._sv, font=('Segoe UI', 10),
                     bg=C['surface2'], fg=C['text'],
                     insertbackground=C['accent'], relief='flat', bd=0)
        e.pack(side='left', fill='x', expand=True, padx=(0, 8))
        e.focus_set()
        e.bind('<Return>',  self._enter)
        e.bind('<Down>',    lambda _: (self._lb.focus_set(), self._lb.selection_set(0)))
        e.bind('<Escape>',  lambda _: self.destroy())

        fr = tk.Frame(self, bg=C['surface'])
        fr.pack(fill='both', expand=True, padx=1, pady=(0, 1))
        sb = tk.Scrollbar(fr, orient='vertical', width=8,
                          bg=C['surface2'], troughcolor=C['surface'])
        self._lb = tk.Listbox(
            fr, font=('Segoe UI', 11),
            bg=C['surface'], fg=C['text'],
            selectbackground=C['accent'], selectforeground=C['bg'],
            activestyle='none', relief='flat', bd=0,
            yscrollcommand=sb.set, height=min(len(opcoes), 9),
        )
        sb.config(command=self._lb.yview)
        self._lb.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        self._lb.bind('<Return>',          self._confirmar)
        self._lb.bind('<Double-Button-1>', self._confirmar)
        self._lb.bind('<Escape>',          lambda _: self.destroy())

        self._preencher(opcoes, atual)
        self._posicionar(anchor)
        self.grab_set()

    def _preencher(self, ops, sel=''):
        self._lb.delete(0, 'end')
        self._filtrados = ops
        for op in ops:
            self._lb.insert('end', f'  {op}')
        for i, op in enumerate(ops):
            if op == sel:
                self._lb.selection_set(i); self._lb.see(i); break

    def _filtrar(self, *_):
        t = self._sv.get().lower()
        self._preencher([o for o in self._opcoes if t in o.lower()] if t else self._opcoes)

    def _enter(self, _=None):
        if self._filtrados:
            self._on_select(self._filtrados[0])
        self.destroy()

    def _confirmar(self, _=None):
        sel = self._lb.curselection()
        if sel:
            self._on_select(self._lb.get(sel[0]).strip())
        self.destroy()

    def _posicionar(self, w: tk.Widget):
        self.update_idletasks()
        x, y = w.winfo_rootx(), w.winfo_rooty() + w.winfo_height()
        self.geometry(f'{max(w.winfo_width(), 260)}x260+{x}+{y}')


# ═══════════════════════════════════════════════════════════════════════════════
# Calendário popup
# ═══════════════════════════════════════════════════════════════════════════════
class _Calendario(tk.Toplevel):
    _MESES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
              'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
    _HDR   = ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom']

    def __init__(self, anchor: tk.Widget, atual: Optional[date],
                 on_select: Callable[[date], None]):
        super().__init__(anchor)
        self.overrideredirect(True)
        self.configure(bg=C['border'])
        self._on_select = on_select
        hoje = date.today()
        self._ano = (atual or hoje).year
        self._mes = (atual or hoje).month
        self._sel = atual

        outer = tk.Frame(self, bg=C['surface'], padx=1, pady=1)
        outer.pack(fill='both', expand=True)

        nav = tk.Frame(outer, bg=C['surface2'])
        nav.pack(fill='x')
        tk.Button(nav, text='◀', font=('Segoe UI', 10), fg=C['text'],
                  bg=C['surface2'], relief='flat', bd=0, cursor='hand2',
                  activebackground=C['surface'],
                  command=self._ant).pack(side='left', padx=6, pady=5)
        self._nav_lbl = tk.Label(nav, font=('Segoe UI', 10, 'bold'),
                                  fg=C['text'], bg=C['surface2'])
        self._nav_lbl.pack(side='left', expand=True)
        tk.Button(nav, text='▶', font=('Segoe UI', 10), fg=C['text'],
                  bg=C['surface2'], relief='flat', bd=0, cursor='hand2',
                  activebackground=C['surface'],
                  command=self._prox).pack(side='right', padx=6, pady=5)

        self._grade = tk.Frame(outer, bg=C['surface'])
        self._grade.pack(padx=8, pady=(0, 8))
        self._desenhar()
        self._posicionar(anchor)
        self.grab_set()
        self.bind('<Escape>', lambda _: self.destroy())

    def _desenhar(self):
        import calendar
        for w in self._grade.winfo_children(): w.destroy()
        self._nav_lbl.config(text=f'{self._MESES[self._mes-1]}  {self._ano}')
        for col, d in enumerate(self._HDR):
            tk.Label(self._grade, text=d, width=4,
                     font=('Segoe UI', 8, 'bold'),
                     fg=C['muted'], bg=C['surface']).grid(row=0, column=col, pady=(4, 2))
        primeiro, total = calendar.monthrange(self._ano, self._mes)
        hoje = date.today()
        dia, row, col = 1, 1, primeiro
        while dia <= total:
            d = date(self._ano, self._mes, dia)
            sel   = d == self._sel
            hoje_ = d == hoje
            fg = C['bg'] if sel else C['accent'] if hoje_ else C['text']
            bg = C['accent'] if sel else C['surface2'] if hoje_ else C['surface']
            tk.Button(
                self._grade, text=str(dia), width=3,
                font=('Segoe UI', 9, 'bold' if sel or hoje_ else 'normal'),
                fg=fg, bg=bg, relief='flat', bd=0, cursor='hand2',
                activebackground=C['accent2'], activeforeground=C['bg'],
                command=lambda dd=d: (self._on_select(dd), self.destroy()),
            ).grid(row=row, column=col, padx=1, pady=1, ipady=3)
            col += 1
            if col == 7: col = 0; row += 1
            dia += 1

    def _ant(self):
        self._mes -= 1
        if self._mes == 0: self._mes = 12; self._ano -= 1
        self._desenhar()

    def _prox(self):
        self._mes += 1
        if self._mes == 13: self._mes = 1; self._ano += 1
        self._desenhar()

    def _posicionar(self, w: tk.Widget):
        self.update_idletasks()
        x, y = w.winfo_rootx(), w.winfo_rooty() + w.winfo_height()
        self.geometry(f'{self.winfo_reqwidth()}x{self.winfo_reqheight()}+{x}+{y}')


# ═══════════════════════════════════════════════════════════════════════════════
# Campo editável individual
# ═══════════════════════════════════════════════════════════════════════════════
class _Campo(tk.Frame):
    def __init__(self, parent: tk.Frame, row: int, nome: str, tipo: str):
        super().__init__(parent, bg=C['surface'])
        self._tipo      = tipo
        self._valor     = None
        self._on_change: Optional[Callable] = None
        self._data_sessao: Optional[date]   = None
        self._editando  = False

        tk.Label(self, text=nome, font=('Segoe UI', 8), fg=C['muted'],
                 bg=C['surface'], anchor='w', width=13).pack(side='left')

        self._cnt = tk.Frame(self, bg=C['surface'])
        self._cnt.pack(side='left', fill='x', expand=True)

        self._lbl = tk.Label(self._cnt, text='—',
                             font=('Segoe UI', 14, 'bold'),
                             fg=C['surface2'], bg=C['surface'],
                             anchor='w', cursor='hand2')
        self._lbl.pack(fill='x')
        self._lbl.bind('<Button-1>', self._abrir)

        self._hint_lbl = tk.Label(self, text='', font=('Segoe UI', 7),
                                   fg=C['muted'], bg=C['surface'])
        self._hint_lbl.pack(side='right', padx=(4, 2))

        self.grid(row=row, column=0, columnspan=2, sticky='ew', pady=2)

    def configurar(self, on_change: Callable, data_sessao: date, root: tk.Tk):
        self._on_change   = on_change
        self._data_sessao = data_sessao
        self._root        = root

    def set_valor(self, valor, *, fg=C['text']):
        self._valor = valor
        if isinstance(valor, float):
            texto = _fmt_brl(valor)
        elif isinstance(valor, date):
            texto = valor.strftime('%d/%m/%Y')
        elif valor:
            texto = str(valor)
        else:
            texto = '—'; fg = C['surface2']
        self._lbl.config(text=texto, fg=fg)
        self._hint_lbl.config(text='clique para editar' if valor and texto != '—' else '')

    def limpar(self):
        self._valor = None
        self._lbl.config(text='—', fg=C['surface2'])
        self._hint_lbl.config(text='')
        self._fechar_entry()

    def ativo(self) -> bool:
        return self._valor is not None

    def abrir_se_ativo(self, _=None):
        if self.ativo() and not self._editando:
            self._abrir()

    def _abrir(self, _=None):
        if self._editando or not self.ativo():
            return
        self._editando = True
        self._lbl.config(fg=C['warn'])
        self._hint_lbl.config(text='editando…', fg=C['warn'])

        if self._tipo == 'bandeira':
            _Dropdown(self._lbl, BANDEIRAS, str(self._valor or ''), self._ok_str)
        elif self._tipo == 'tipo':
            _Dropdown(self._lbl, TIPOS, str(self._valor or ''), self._ok_str)
        elif self._tipo == 'valor':
            self._lbl.pack_forget()
            val = self._valor if isinstance(self._valor, float) else 0.0
            sv = tk.StringVar(value=f"{val:.2f}".replace('.', ','))
            e = tk.Entry(self._cnt, textvariable=sv,
                         font=('Segoe UI', 14, 'bold'),
                         fg=C['accent2'], bg=C['surface2'],
                         insertbackground=C['accent2'],
                         relief='flat', bd=0, justify='left')
            e.pack(fill='x', ipady=5, padx=4)
            e.select_range(0, 'end'); e.focus_set()
            e.bind('<Return>',   lambda _, s=sv, w=e: self._ok_valor(s, w))
            e.bind('<Escape>',   lambda _, w=e: self._fechar_entry(w))
            e.bind('<FocusOut>', lambda _, w=e: self._fechar_entry(w))
            self._entry_w = e
        elif self._tipo == 'data':
            d = self._valor if isinstance(self._valor, date) else None
            _Calendario(self._lbl, d, self._ok_data)

    def _ok_str(self, valor: str):
        self._editando = False
        self._valor = valor
        self._lbl.config(text=valor, fg=C['text'])
        self._hint_lbl.config(text='clique para editar', fg=C['muted'])
        if self._on_change: self._on_change(self._tipo, valor)

    def _ok_valor(self, sv: tk.StringVar, entry: tk.Entry):
        v = _parse_brl(sv.get())
        self._fechar_entry(entry)
        if v is not None:
            self._editando = False
            self.set_valor(v, fg=C['accent2'])
            if self._on_change: self._on_change(self._tipo, v)

    def _ok_data(self, d: date):
        self._editando = False
        ok = (d == self._data_sessao)
        self.set_valor(d, fg=C['success'] if ok else C['warn'])
        if self._on_change: self._on_change(self._tipo, d)

    def _fechar_entry(self, w=None):
        self._editando = False
        if w:
            try: w.destroy()
            except Exception: pass
        self._lbl.pack(fill='x')
        if self._valor is not None:
            self._lbl.config(fg=C['text'])
        self._hint_lbl.config(
            text='clique para editar' if self.ativo() else '', fg=C['muted'])


# ═══════════════════════════════════════════════════════════════════════════════
# FieldsBlock
# ═══════════════════════════════════════════════════════════════════════════════
class FieldsBlock(tk.Frame):
    def __init__(self, parent: tk.Widget):
        super().__init__(parent, bg=C['bg'])
        self._campos: dict[str, _Campo] = {}
        self._build()

    def _build(self):
        from ui.widgets import card, lbl, sep
        c = card(self)
        c.pack(fill='x', pady=(0, 8))

        hdr = tk.Frame(c, bg=C['surface'])
        hdr.pack(fill='x', padx=14, pady=(10, 4))
        lbl(hdr, 'Campos identificados', 11, bold=True).pack(side='left')
        self._hint = lbl(hdr, 'aguardando…', 8, color=C['muted'])
        self._hint.pack(side='right')

        sep(c)

        grid = tk.Frame(c, bg=C['surface'])
        grid.pack(fill='x', padx=12, pady=8)
        grid.columnconfigure(0, weight=1)

        for row, (key, nome, tipo) in enumerate([
            ('bandeira', 'BANDEIRA',     'bandeira'),
            ('tipo',     'TIPO',         'tipo'),
            ('valor',    'VALOR',        'valor'),
            ('data',     'DATA DA NOTA', 'data'),
        ]):
            campo = _Campo(grid, row, nome, tipo)
            self._campos[key] = campo

        sep(c)
        rodape = tk.Frame(c, bg=C['surface'])
        rodape.pack(fill='x', padx=14, pady=(6, 10))
        lbl(rodape, '↵ aceitar  ·  ⌫ rejeitar',
            8, color=C['muted2']).pack(side='left')
        lbl(rodape, 'clique no campo para editar', 8, color=C['muted']).pack(side='right')

    def configurar(self, root: tk.Tk, data_sessao: date,
                   on_change: Callable[[str, object], None]):
        self._root = root
        for campo in self._campos.values():
            campo.configurar(on_change, data_sessao, root)

    def _backslash_global(self, event: tk.Event):
        for key in ('bandeira', 'tipo', 'valor', 'data'):
            campo = self._campos[key]
            if campo.ativo() and not campo._editando:
                campo.abrir_se_ativo()
                return

    def exibir(self, reg: dict, data_sessao: date):
        self._campos['bandeira'].set_valor(reg['bandeira'])
        self._campos['tipo'].set_valor(reg['tipo'])
        self._campos['valor'].set_valor(reg['valor'], fg=C['accent2'])
        if reg['data']:
            ok = reg['data'] == data_sessao
            self._campos['data'].set_valor(
                reg['data'], fg=C['success'] if ok else C['warn'])
        else:
            self._campos['data'].set_valor(None)
        self._hint.config(text='↵ aceitar   ⌫ rejeitar', fg=C['accent'])

    def limpar(self):
        for campo in self._campos.values():
            campo.limpar()
        self._hint.config(text='aguardando…', fg=C['muted'])

    def valores_atuais(self) -> dict:
        return {
            'bandeira': self._campos['bandeira']._valor or 'Não identificada',
            'tipo':     self._campos['tipo']._valor     or 'Não identificado',
            'valor':    self._campos['valor']._valor,
            'data':     self._campos['data']._valor,
        }
