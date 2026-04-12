import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import threading
import time
import re
from datetime import datetime, date
from PIL import Image, ImageTk
import openpyxl
from openpyxl.styles import Font as XLFont, PatternFill, Alignment, Border, Side
import os

# ─── OCR ENGINE ───────────────────────────────────────────────
try:
    import easyocr
    OCR_ENGINE = "easyocr"
    _reader = None
except ImportError:
    try:
        import pytesseract
        OCR_ENGINE = "tesseract"
    except ImportError:
        OCR_ENGINE = "none"

# ══════════════════════════════════════════════════════════════
#  TEMA
# ══════════════════════════════════════════════════════════════
C = {
    'bg':       '#111318',
    'surface':  '#1C1F26',
    'surface2': '#242830',
    'border':   '#2E3340',
    'accent':   '#4F8EF7',
    'accent2':  '#38D9A9',
    'warn':     '#F5A623',
    'danger':   '#F05C5C',
    'text':     '#E8EAF0',
    'muted':    '#6B7280',
    'muted2':   '#9CA3AF',
    'success':  '#34D399',
    'panel':    '#161A21',
}

# ══════════════════════════════════════════════════════════════
#  DICIONÁRIOS OCR
# ══════════════════════════════════════════════════════════════
BANDEIRAS = {
    r'\bvisa\s*electron\b': 'Visa Electron',
    r'\bvisa\s*vale\b': 'Visa Vale',
    r'\bvisa\s*(pre.?pago|prepago)\b': 'Visa Pré-pago',
    r'\bvisa\b': 'Visa',
    r'\bmastercard\s*(pre.?pago|prepago)\b': 'Mastercard Pré-pago',
    r'\bmaster\s*(pre.?pago|prepago)\b': 'Mastercard Pré-pago',
    r'\bmaestro\b': 'Maestro',
    r'\bmastercard\b': 'Mastercard',
    r'\bmaster\b': 'Mastercard',
    r'\belo\s*(pre.?pago|prepago)\b': 'Elo Pré-pago',
    r'\belo\b': 'Elo',
    r'\bhipercard\b': 'Hipercard',
    r'\bhiper\b': 'Hipercard',
    r'\bamerican\s*express\b': 'American Express',
    r'\bamex\b': 'American Express',
    r'\bcabal\s*(pre.?pago|prepago)\b': 'Cabal Pré-pago',
    r'\bcabal\b': 'Cabal',
    r'\baura\b': 'Aura',
    r'\bdinersclub\b|\bdiners\s*club\b|\bdiners\b': 'Diners Club',
    r'\balelo\b': 'Alelo',
    r'\bbeneflex\b': 'Beneflex',
    r'\bsorocred\b': 'Sorocred',
    r'\bvr\s*(beneficios|refeicao|alimentacao)\b': 'VR Benefícios',
    r'\bticket\b': 'Ticket',
    r'\bsodexo\b': 'Sodexo',
}

TIPOS = {
    r'\bpre.?pago\b|\bprepago\b': 'Pré-pago',
    r'\bdebito\b|\bd[ée]bito\b|\bdebit\b': 'Débito',
    r'\bcredito\b|\bcr[eé]dito\b|\bcredit\b': 'Crédito',
    r'\bcontactless\b|\bsem\s*contato\b': 'Contactless',
}

# ══════════════════════════════════════════════════════════════
#  FUNÇÕES OCR
# ══════════════════════════════════════════════════════════════
def get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(['pt', 'en'], gpu=False)
    return _reader

def extrair_texto(frame):
    if OCR_ENGINE == "easyocr":
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = get_reader().readtext(rgb)
        return ' '.join([r[1] for r in res])
    elif OCR_ENGINE == "tesseract":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                        cv2.THRESH_BINARY, 21, 10)
        return pytesseract.image_to_string(binary, config='--psm 6 -l por+eng')
    return ""

def extrair_bandeira(t):
    tl = t.lower()
    for p, n in BANDEIRAS.items():
        if re.search(p, tl): return n
    return None

def extrair_tipo(t):
    tl = t.lower()
    for p, n in TIPOS.items():
        if re.search(p, tl): return n
    return None

def extrair_valor(texto):
    for p in [
        r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2}))',
        r'R\$\s*(\d+[,\.]\d{2})',
        r'TOTAL[:\s]*R?\$?\s*(\d+[,\.]\d{2})',
        r'VALOR[:\s]*R?\$?\s*(\d+[,\.]\d{2})',
        r'(?<!\d)(\d{1,3}(?:\.\d{3})*,\d{2})(?!\d)',
    ]:
        m = re.search(p, texto, re.IGNORECASE)
        if m:
            try:
                v = float(m.group(1).replace('.', '').replace(',', '.'))
                if 0.01 <= v <= 99999.99:
                    return v
            except: pass
    return None

def extrair_data(texto):
    for p in [
        r'(\d{2})[/\-\.](\d{2})[/\-\.](\d{4})',
        r'(\d{2})[/\-\.](\d{2})[/\-\.](\d{2})(?!\d)',
        r'(\d{4})[/\-\.](\d{2})[/\-\.](\d{2})',
    ]:
        m = re.search(p, texto)
        if m:
            try:
                g = m.groups()
                if len(g[2]) == 4: return date(int(g[2]), int(g[1]), int(g[0]))
                elif len(g[0]) == 4: return date(int(g[0]), int(g[1]), int(g[2]))
                else:
                    a = 2000+int(g[2]) if int(g[2]) < 50 else 1900+int(g[2])
                    return date(a, int(g[1]), int(g[0]))
            except: pass
    return None

def fmt_brl(valor):
    return f"R$ {valor:,.2f}".replace(',','X').replace('.',',').replace('X','.')

# ══════════════════════════════════════════════════════════════
#  EXPORTAÇÃO
# ══════════════════════════════════════════════════════════════
def exportar_excel(registros, data_sessao_str, caminho):
    from collections import defaultdict
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Notas {data_sessao_str}"

    def cell(r, c, v, bold=False, color="E8EAF0", bg=None, fmt=None, align='center'):
        cel = ws.cell(row=r, column=c, value=v)
        cel.font = XLFont(color=color, bold=bold, size=10)
        if bg: cel.fill = PatternFill("solid", fgColor=bg)
        if fmt: cel.number_format = fmt
        cel.alignment = Alignment(horizontal=align, vertical='center')
        return cel

    headers = ['#','Bandeira','Tipo','Valor (R$)','Data Nota','Data Sessão','Status','Hora']
    for c, h in enumerate(headers, 1):
        cell(1, c, h, bold=True, color="4F8EF7", bg="111318")
    ws.row_dimensions[1].height = 24

    total = 0.0
    for i, reg in enumerate(registros, 1):
        r = i + 1
        d = reg['data'].strftime('%d/%m/%Y') if reg['data'] else '—'
        st = reg.get('status_data', 'OK')
        bg = "0A1A0F" if st == 'OK' else "1A1500"
        if i % 2 == 0 and st == 'OK': bg = "161A21"
        vals = [i, reg['bandeira'], reg['tipo'],
                reg['valor'] or 0, d, data_sessao_str, st, reg.get('hora','')]
        for c, v in enumerate(vals, 1):
            fmt = 'R$ #,##0.00' if c == 4 else None
            cell(r, c, v, bg=bg, fmt=fmt)
        if reg['valor']: total += reg['valor']

    # Subtotais
    rs = len(registros) + 3
    ws.cell(row=rs, column=1, value='SUBTOTAIS').font = XLFont(bold=True, color="4F8EF7")
    rs += 1
    for h, col in [('Bandeira',1),('Tipo',2),('Qtd',3),('Total',4)]:
        cell(rs, col, h, bold=True, color="9CA3AF")
    rs += 1

    sub = defaultdict(lambda: {'qtd':0,'valor':0.0})
    for reg in registros:
        k = (reg['bandeira'], reg['tipo'])
        sub[k]['qtd'] += 1
        sub[k]['valor'] += reg['valor'] or 0

    for i, ((b, t), d) in enumerate(sorted(sub.items())):
        bg = "161A21" if i%2==0 else "1C1F26"
        cell(rs,1,b,bg=bg); cell(rs,2,t,bg=bg)
        cell(rs,3,d['qtd'],bg=bg)
        cell(rs,4,d['valor'],bg=bg,fmt='R$ #,##0.00')
        rs += 1

    rs += 1
    cell(rs,2,'TOTAL GERAL',bold=True,color="38D9A9",bg="0E1420")
    cell(rs,3,len(registros),bold=True,color="38D9A9",bg="0E1420")
    cell(rs,4,total,bold=True,color="38D9A9",bg="0E1420",fmt='R$ #,##0.00')

    for col, w in zip(range(1,9),[5,22,16,14,14,14,16,10]):
        ws.column_dimensions[ws.cell(row=1,column=col).column_letter].width = w

    wb.save(caminho)
    return total

# ══════════════════════════════════════════════════════════════
#  APP
# ══════════════════════════════════════════════════════════════
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Leitor de Notas · OCR")
        self.root.geometry("1280x820")
        self.root.configure(bg=C['bg'])
        self.root.resizable(True, True)
        self.root.minsize(1100, 720)

        self.cap = None
        self.capturando = False
        self.ocr_ativo = False
        self.frame_atual = None
        self.lock = threading.Lock()
        self.ultimo_ocr = 0
        self.cooldown = 3.0
        self.preview_width = 560
        self.preview_height = 315
        self.data_sessao = date.today()
        self.registros = []
        self.subtotais = {}   # {(bandeira, tipo): {qtd, valor}}
        self.pendente = None

        self._build()
        self.root.bind('<Return>', self._aceitar)
        self.root.bind('<BackSpace>', self._rejeitar)

    # ────────────────────────────────────────── UI BUILD ──────
    def _build(self):
        # TOPBAR
        top = tk.Frame(self.root, bg=C['surface'], height=50,
                       highlightthickness=1, highlightbackground=C['border'])
        top.pack(fill='x')
        top.pack_propagate(False)

        tk.Label(top, text='  ◈  LEITOR DE NOTAS DE CARTÃO',
                 font=('Segoe UI', 13, 'bold'),
                 fg=C['accent'], bg=C['surface']).pack(side='left', padx=4, pady=8)

        self.lbl_clock = tk.Label(top, text='', font=('Segoe UI', 10),
                                   fg=C['muted2'], bg=C['surface'])
        self.lbl_clock.pack(side='right', padx=16)

        tk.Label(top, text=f'engine: {OCR_ENGINE}',
                 font=('Segoe UI', 9), fg=C['muted'], bg=C['surface']).pack(side='right')
        self._tick()

        # BODY
        body = tk.Frame(self.root, bg=C['bg'])
        body.pack(fill='both', expand=True)

        # COLUNA ESQUERDA
        left = tk.Frame(body, bg=C['bg'], width=self.preview_width + 34)
        left.pack(side='left', fill='y', padx=12, pady=12)
        left.pack_propagate(False)

        self._bloco_camera(left)
        self._bloco_campos(left)
        self._bloco_controles(left)

        # DIVISOR
        tk.Frame(body, bg=C['border'], width=1).pack(side='left', fill='y', pady=12)

        # COLUNA DIREITA
        right = tk.Frame(body, bg=C['bg'])
        right.pack(side='right', fill='both', expand=True, padx=12, pady=12)
        self._bloco_tabela(right)

    # ── BLOCO CÂMERA ──────────────────────────────────────────
    def _bloco_camera(self, parent):
        card = self._card(parent)
        card.pack(fill='x', pady=(0, 8))

        # header
        hdr = tk.Frame(card, bg=C['surface'])
        hdr.pack(fill='x', padx=14, pady=(10, 6))
        self._lbl(hdr, 'Câmera ao vivo', 11, bold=True).pack(side='left')
        self.badge = tk.Label(hdr, text=' INATIVA ',
                               font=('Segoe UI', 8, 'bold'),
                               fg=C['muted'], bg=C['surface2'], padx=6, pady=2)
        self.badge.pack(side='right')

        # preview
        cam_wrap = tk.Frame(
            card,
            bg=C['border'],
            width=self.preview_width + 2,
            height=self.preview_height + 2,
        )
        cam_wrap.pack(fill='x', padx=14, pady=(0, 8))
        cam_wrap.pack_propagate(False)
        self.lbl_cam = tk.Label(cam_wrap, bg='#0A0C10',
                                 text='sem sinal', font=('Segoe UI', 10),
                                 fg=C['muted'])
        self.lbl_cam.pack(fill='both', expand=True, padx=1, pady=1)

        # data sessão
        self._sep(card)
        dr = tk.Frame(card, bg=C['surface'])
        dr.pack(fill='x', padx=14, pady=(8, 6))
        self._lbl(dr, 'Data da sessão:', 9, color=C['muted']).pack(side='left', padx=(0,8))

        sp_kw = dict(bg=C['surface2'], fg=C['accent'],
                     font=('Segoe UI', 10, 'bold'), bd=0, relief='flat',
                     highlightthickness=1, highlightcolor=C['accent'],
                     highlightbackground=C['border'],
                     insertbackground=C['accent'],
                     buttonbackground=C['surface2'])
        self.var_d = tk.StringVar(value=str(date.today().day).zfill(2))
        self.var_m = tk.StringVar(value=str(date.today().month).zfill(2))
        self.var_a = tk.StringVar(value=str(date.today().year))

        tk.Spinbox(dr, from_=1, to=31, textvariable=self.var_d,
                   width=3, command=self._sync_data, **sp_kw).pack(side='left')
        self._lbl(dr, '/', 11, color=C['muted']).pack(side='left', padx=2)
        tk.Spinbox(dr, from_=1, to=12, textvariable=self.var_m,
                   width=3, command=self._sync_data, **sp_kw).pack(side='left')
        self._lbl(dr, '/', 11, color=C['muted']).pack(side='left', padx=2)
        tk.Spinbox(dr, from_=2020, to=2099, textvariable=self.var_a,
                   width=6, command=self._sync_data, **sp_kw).pack(side='left')

        dias = ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom']
        dia_nome = dias[date.today().weekday()]
        self.lbl_dia_nome = self._lbl(dr,
                                       f'  {dia_nome}, {date.today().strftime("%d/%m/%Y")}',
                                       8, color=C['muted2'])
        self.lbl_dia_nome.pack(side='left')

    # ── BLOCO CAMPOS DETECTADOS ────────────────────────────────
    def _bloco_campos(self, parent):
        card = self._card(parent)
        card.pack(fill='x', pady=(0, 8))

        hdr = tk.Frame(card, bg=C['surface'])
        hdr.pack(fill='x', padx=14, pady=(10, 4))
        self._lbl(hdr, 'Campos identificados', 11, bold=True).pack(side='left')
        self.lbl_hint = self._lbl(hdr, 'aguardando…', 8, color=C['muted'])
        self.lbl_hint.pack(side='right')

        self._sep(card)

        grid = tk.Frame(card, bg=C['surface'])
        grid.pack(fill='x', padx=18, pady=12)
        grid.columnconfigure(1, weight=1)

        self.f_bandeira = self._campo_row(grid, 0, 'BANDEIRA')
        self.f_tipo     = self._campo_row(grid, 1, 'TIPO')
        self.f_valor    = self._campo_row(grid, 2, 'VALOR')
        self.f_data     = self._campo_row(grid, 3, 'DATA DA NOTA')

    def _campo_row(self, parent, row, nome):
        self._lbl(parent, nome, 8, color=C['muted']).grid(
            row=row, column=0, sticky='w', pady=5, padx=(0, 16))
        lbl = tk.Label(parent, text='—', font=('Segoe UI', 12, 'bold'),
                       fg=C['surface2'], bg=C['surface'], anchor='w')
        lbl.grid(row=row, column=1, sticky='ew', pady=5)
        return lbl

    # ── BLOCO CONTROLES ────────────────────────────────────────
    def _bloco_controles(self, parent):
        card = self._card(parent)
        card.pack(fill='x', pady=(0, 8))

        # Botões câmera
        br = tk.Frame(card, bg=C['surface'])
        br.pack(fill='x', padx=14, pady=(10, 6))

        self.btn_cam = self._btn(br, '▶  Iniciar câmera',
                                  bg=C['accent'], fg=C['bg'],
                                  cmd=self._toggle_cam)
        self.btn_cam.pack(side='left')

        self.btn_ocr_toggle = self._btn(br, '◎  Leitura auto',
                                         bg=C['surface2'], fg=C['muted'],
                                         cmd=self._toggle_ocr)
        self.btn_ocr_toggle.config(state='disabled')
        self.btn_ocr_toggle.pack(side='left', padx=(8, 0))

        # Intervalo
        ir = tk.Frame(card, bg=C['surface'])
        ir.pack(fill='x', padx=14, pady=(0, 6))
        self._lbl(ir, 'Intervalo:', 8, color=C['muted']).pack(side='left')
        self.lbl_int = self._lbl(ir, '3.0s', 8, color=C['accent2'])
        self.lbl_int.pack(side='right')
        self.var_interval = tk.DoubleVar(value=3.0)
        tk.Scale(ir, from_=1, to=8, resolution=0.5, orient='horizontal',
                 variable=self.var_interval, bg=C['surface'], fg=C['muted'],
                 troughcolor=C['surface2'], highlightthickness=0,
                 showvalue=False, sliderlength=14,
                 command=lambda v: [setattr(self,'cooldown',float(v)),
                                    self.lbl_int.config(text=f'{float(v):.1f}s')]
                 ).pack(side='left', fill='x', expand=True, padx=6)

        self._sep(card)

        # Aceitar / Rejeitar
        ar = tk.Frame(card, bg=C['surface'])
        ar.pack(fill='x', padx=14, pady=8)

        self.btn_aceitar = self._btn(ar, '↵  Aceitar  (Enter)',
                                      bg=C['success'], fg=C['bg'],
                                      cmd=self._aceitar, bold=True)
        self.btn_aceitar.config(state='disabled')
        self.btn_aceitar.pack(side='left', fill='x', expand=True, padx=(0, 6))

        self.btn_rejeitar = self._btn(ar, '⌫  Rejeitar  (Backspace)',
                                       bg=C['surface2'], fg=C['danger'],
                                       cmd=self._rejeitar)
        self.btn_rejeitar.config(state='disabled')
        self.btn_rejeitar.pack(side='left', fill='x', expand=True)

        self.lbl_status = self._lbl(card, 'Câmera inativa', 8, color=C['muted'])
        self.lbl_status.pack(pady=(0, 10))

    # ── BLOCO TABELA ──────────────────────────────────────────
    def _bloco_tabela(self, parent):
        hdr = tk.Frame(parent, bg=C['bg'])
        hdr.pack(fill='x', pady=(0, 8))
        self._lbl(hdr, 'Totalizador da sessão', 13, bold=True,
                  bg=C['bg']).pack(side='left')

        self._btn(hdr, '✕ Limpar', bg=C['surface'], fg=C['danger'],
                  cmd=self._limpar).pack(side='right')
        self._btn(hdr, '⬇  Exportar Excel', bg=C['accent2'], fg=C['bg'],
                  cmd=self._exportar, bold=True).pack(side='right', padx=(0,8))

        # Treeview
        card = self._card(parent)
        card.pack(fill='both', expand=True)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('N.Treeview',
                         background=C['surface'], foreground=C['text'],
                         fieldbackground=C['surface'], rowheight=32,
                         font=('Segoe UI', 10), borderwidth=0)
        style.configure('N.Treeview.Heading',
                         background=C['surface2'], foreground=C['muted2'],
                         font=('Segoe UI', 9, 'bold'), relief='flat')
        style.map('N.Treeview',
                  background=[('selected', '#2A2E3A')],
                  foreground=[('selected', C['accent'])])

        cols = ('bandeira', 'tipo', 'qtd', 'valor')
        self.tree = ttk.Treeview(card, columns=cols, show='headings',
                                  style='N.Treeview')

        for col, label_txt, w in [
            ('bandeira','Bandeira',220), ('tipo','Tipo',120),
            ('qtd','Qtd',70), ('valor','Valor Total',160)
        ]:
            self.tree.heading(col, text=label_txt)
            self.tree.column(col, width=w, anchor='center', minwidth=60)

        self.tree.tag_configure('even',  background='#161A21', foreground=C['text'])
        self.tree.tag_configure('odd',   background=C['surface'], foreground=C['text'])
        self.tree.tag_configure('total', background='#0D1320',
                                foreground=C['accent2'],
                                font=('Segoe UI', 10, 'bold'))

        sb = ttk.Scrollbar(card, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side='left', fill='both', expand=True, padx=(12,0), pady=8)
        sb.pack(side='right', fill='y', pady=8)

        # Footer totais
        self._sep(parent)
        footer = tk.Frame(parent, bg=C['surface'],
                          highlightthickness=1, highlightbackground=C['border'])
        footer.pack(fill='x')

        self.lbl_qtd = tk.Label(footer, text='0 notas',
                                 font=('Segoe UI', 11), fg=C['muted2'],
                                 bg=C['surface'])
        self.lbl_qtd.pack(side='left', padx=16, pady=14)

        self._lbl(footer, 'Total geral:', 9, color=C['muted'],
                  bg=C['surface']).pack(side='right', padx=(0,4), pady=14)

        self.lbl_total = tk.Label(footer, text='R$ 0,00',
                                   font=('Segoe UI', 17, 'bold'),
                                   fg=C['accent2'], bg=C['surface'])
        self.lbl_total.pack(side='right', padx=(0,16), pady=14)

    # ── HELPERS UI ─────────────────────────────────────────────
    def _card(self, parent):
        return tk.Frame(parent, bg=C['surface'],
                        highlightthickness=1, highlightbackground=C['border'])

    def _sep(self, parent):
        tk.Frame(parent, bg=C['border'], height=1).pack(fill='x', padx=0)

    def _lbl(self, parent, text, size=10, bold=False, color=None, bg=None):
        return tk.Label(parent, text=text,
                        font=('Segoe UI', size, 'bold' if bold else 'normal'),
                        fg=color or C['text'],
                        bg=bg if bg else parent.cget('bg'))

    def _btn(self, parent, text, bg, fg, cmd, bold=False):
        return tk.Button(parent, text=text,
                          font=('Segoe UI', 10, 'bold' if bold else 'normal'),
                          bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                          relief='flat', cursor='hand2', padx=14, pady=7,
                          command=cmd)

    # ── CÂMERA ─────────────────────────────────────────────────
    def _toggle_cam(self):
        if self.capturando: self._parar_cam()
        else: self._iniciar_cam()

    def _iniciar_cam(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror('Erro', 'Câmera não encontrada.\nVerifique a conexão.')
            return
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.capturando = True
        self.btn_cam.config(text='■  Parar câmera', bg=C['danger'],
                             activebackground=C['danger'])
        self.btn_ocr_toggle.config(state='normal', fg=C['text'])
        self.badge.config(text=' ATIVA ', fg=C['accent2'], bg='#0D2E22')
        self.lbl_status.config(text='Câmera ativa — ative a leitura automática',
                                fg=C['muted2'])
        threading.Thread(target=self._loop_cam, daemon=True).start()

    def _parar_cam(self):
        self.ocr_ativo = False
        self.capturando = False
        if self.cap: self.cap.release()
        self.btn_cam.config(text='▶  Iniciar câmera', bg=C['accent'],
                             activebackground=C['accent'])
        self.btn_ocr_toggle.config(state='disabled', fg=C['muted'],
                                    text='◎  Leitura auto', bg=C['surface2'])
        self.badge.config(text=' INATIVA ', fg=C['muted'], bg=C['surface2'])
        self.lbl_cam.config(image='', text='sem sinal')
        self.lbl_status.config(text='Câmera inativa', fg=C['muted'])

    def _loop_cam(self):
        while self.capturando:
            ret, frame = self.cap.read()
            if not ret: break
            with self.lock:
                self.frame_atual = frame.copy()

            display = frame.copy()
            h, w = display.shape[:2]
            mx, my = int(w*.04), int(h*.04)
            cor = (56,217,169) if self.ocr_ativo else (79,142,247)
            cv2.rectangle(display, (mx,my), (w-mx,h-my), cor, 2)
            txt = 'AGUARDANDO CONFIRMACAO...' if self.pendente else \
                  ('LENDO...' if self.ocr_ativo else 'POSICIONE A NOTA')
            cv2.putText(display, txt, (mx+4, my-8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.44, cor, 1)

            if self.ocr_ativo and self.pendente is None:
                agora = time.time()
                if agora - self.ultimo_ocr >= self.cooldown:
                    self.ultimo_ocr = agora
                    threading.Thread(target=self._processar,
                                     args=(frame.copy(),), daemon=True).start()

            rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb).resize(
                (self.preview_width, self.preview_height),
                Image.LANCZOS,
            )
            imgtk = ImageTk.PhotoImage(img)
            self.root.after(0, lambda i=imgtk: self._set_cam(i))
            time.sleep(0.033)

    def _set_cam(self, imgtk):
        self.lbl_cam.configure(image=imgtk, text='')
        self.lbl_cam.image = imgtk

    def _toggle_ocr(self):
        self.ocr_ativo = not self.ocr_ativo
        if self.ocr_ativo:
            self.btn_ocr_toggle.config(text='◉  Pausar leitura',
                                        bg=C['warn'], fg=C['bg'],
                                        activebackground=C['warn'])
            self.lbl_status.config(text='Leitura automática ativa…', fg=C['accent2'])
        else:
            self.btn_ocr_toggle.config(text='◎  Leitura auto',
                                        bg=C['surface2'], fg=C['text'],
                                        activebackground=C['surface2'])
            self.lbl_status.config(text='Leitura pausada', fg=C['muted'])

    # ── OCR ────────────────────────────────────────────────────
    def _processar(self, frame):
        self.root.after(0, lambda: self.lbl_status.config(
            text='Processando…', fg=C['warn']))
        texto = extrair_texto(frame)
        bandeira = extrair_bandeira(texto)
        tipo = extrair_tipo(texto)
        valor = extrair_valor(texto)
        data = extrair_data(texto)

        if valor is None:
            self.root.after(0, lambda: self.lbl_status.config(
                text='Valor não identificado — reposicione a nota', fg=C['muted']))
            return

        self.root.after(0, self._exibir_campos, {
            'bandeira': bandeira or 'Não identificada',
            'tipo': tipo or 'Não identificado',
            'valor': valor, 'data': data,
        })

    def _exibir_campos(self, r):
        self.pendente = r
        self.f_bandeira.config(text=r['bandeira'], fg=C['text'])
        self.f_tipo.config(text=r['tipo'], fg=C['text'])
        self.f_valor.config(text=fmt_brl(r['valor']), fg=C['accent2'])

        if r['data']:
            ok = r['data'] == self.data_sessao
            self.f_data.config(text=r['data'].strftime('%d/%m/%Y'),
                                fg=C['success'] if ok else C['warn'])
        else:
            self.f_data.config(text='Não identificada', fg=C['muted'])

        self.btn_aceitar.config(state='normal')
        self.btn_rejeitar.config(state='normal')
        self.lbl_hint.config(text='↵ aceitar   ⌫ rejeitar', fg=C['accent'])
        self.lbl_status.config(text='Nota identificada — confirme ou rejeite',
                                fg=C['accent2'])

    def _aceitar(self, event=None):
        if not self.pendente: return
        r = self.pendente
        data_nota = r['data']

        if data_nota and data_nota != self.data_sessao:
            s = self.data_sessao.strftime('%d/%m/%Y')
            n = data_nota.strftime('%d/%m/%Y')
            if not messagebox.askyesno('Data divergente',
                f'Data da nota ({n}) difere da sessão ({s}).\nAdicionar mesmo assim?'):
                self._limpar_campos()
                return
            r['status_data'] = '⚠ Divergente'
        elif not data_nota:
            r['status_data'] = 'S/data'
        else:
            r['status_data'] = 'OK'

        r['hora'] = datetime.now().strftime('%H:%M:%S')
        self.registros.append(r)
        self._atualizar_tabela(r)
        self._limpar_campos()

    def _rejeitar(self, event=None):
        if not self.pendente: return
        self._limpar_campos()
        self.lbl_status.config(text='Nota rejeitada — aguardando próxima…',
                                fg=C['muted'])

    def _limpar_campos(self):
        self.pendente = None
        for f in (self.f_bandeira, self.f_tipo, self.f_valor, self.f_data):
            f.config(text='—', fg=C['surface2'])
        self.btn_aceitar.config(state='disabled')
        self.btn_rejeitar.config(state='disabled')
        self.lbl_hint.config(text='aguardando…', fg=C['muted'])
        if self.ocr_ativo:
            self.lbl_status.config(text='Leitura automática ativa…', fg=C['accent2'])

    # ── TABELA SUBTOTAIS ───────────────────────────────────────
    def _atualizar_tabela(self, reg):
        key = (reg['bandeira'], reg['tipo'])
        if key not in self.subtotais:
            self.subtotais[key] = {'qtd': 0, 'valor': 0.0}
        self.subtotais[key]['qtd'] += 1
        self.subtotais[key]['valor'] += reg['valor'] or 0.0

        for item in self.tree.get_children():
            self.tree.delete(item)

        total_qtd = 0
        total_val = 0.0
        for i, ((b, t), d) in enumerate(sorted(self.subtotais.items())):
            self.tree.insert('', 'end',
                              values=(b, t, d['qtd'], fmt_brl(d['valor'])),
                              tags=('even' if i%2==0 else 'odd',))
            total_qtd += d['qtd']
            total_val += d['valor']

        self.tree.insert('', 'end',
                          values=('TOTAL GERAL', '—', total_qtd, fmt_brl(total_val)),
                          tags=('total',))

        self.lbl_qtd.config(text=f'{total_qtd} nota{"s" if total_qtd!=1 else ""}')
        self.lbl_total.config(text=fmt_brl(total_val))

    # ── UTILITÁRIOS ────────────────────────────────────────────
    def _sync_data(self):
        try:
            self.data_sessao = date(int(self.var_a.get()),
                                    int(self.var_m.get()),
                                    int(self.var_d.get()))
            dias = ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom']
            d = self.data_sessao
            self.lbl_dia_nome.config(
                text=f'  {dias[d.weekday()]}, {d.strftime("%d/%m/%Y")}')
        except ValueError:
            pass

    def _tick(self):
        self.lbl_clock.config(text=datetime.now().strftime('%H:%M:%S'))
        self.root.after(1000, self._tick)

    def _exportar(self):
        if not self.registros:
            messagebox.showwarning('Vazio', 'Nenhum registro para exportar.')
            return
        nome = (f"notas_{self.data_sessao.strftime('%Y%m%d')}_"
                f"{datetime.now().strftime('%H%M%S')}.xlsx")
        caminho = os.path.join(os.path.expanduser('~'), 'Desktop', nome)
        try:
            total = exportar_excel(self.registros,
                                   self.data_sessao.strftime('%d/%m/%Y'), caminho)
            messagebox.showinfo('Exportado!',
                                f'Arquivo salvo em:\n{caminho}\n\n'
                                f'{len(self.registros)} nota(s) · {fmt_brl(total)}')
        except Exception as e:
            messagebox.showerror('Erro ao exportar', str(e))

    def _limpar(self):
        if self.registros and messagebox.askyesno('Limpar', 'Limpar todos os registros?'):
            self.registros.clear()
            self.subtotais.clear()
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.lbl_qtd.config(text='0 notas')
            self.lbl_total.config(text='R$ 0,00')

    def on_close(self):
        self._parar_cam()
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.protocol('WM_DELETE_WINDOW', app.on_close)
    root.mainloop()
