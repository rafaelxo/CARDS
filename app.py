import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import threading
import time
import re
from datetime import datetime, date
from PIL import Image, ImageTk, ImageFilter, ImageEnhance
import numpy as np
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import os
import sys

# ─── Tentar importar EasyOCR (preferido) ou pytesseract como fallback ───
try:
    import easyocr
    OCR_ENGINE = "easyocr"
    reader = None  # inicializa lazy
except ImportError:
    try:
        import pytesseract
        OCR_ENGINE = "tesseract"
    except ImportError:
        OCR_ENGINE = "none"

# ══════════════════════════════════════════════════════════════
#  CONFIGURAÇÕES DE BANDEIRAS
# ══════════════════════════════════════════════════════════════

BANDEIRAS = {
    # Visa
    r'\bvisa\s*electron\b': 'Visa Electron',
    r'\bvisa\s*vale\b': 'Visa Vale',
    r'\bvisa\s*(pre.?pago|prepago)\b': 'Visa Pré-pago',
    r'\bvisa\b': 'Visa',

    # Mastercard
    r'\bmastercard\s*(pre.?pago|prepago)\b': 'Mastercard Pré-pago',
    r'\bmaster\s*(pre.?pago|prepago)\b': 'Mastercard Pré-pago',
    r'\bmaestro\b': 'Maestro',
    r'\bmastercard\b': 'Mastercard',
    r'\bmaster\b': 'Mastercard',

    # Elo
    r'\belo\s*(pre.?pago|prepago)\b': 'Elo Pré-pago',
    r'\belo\b': 'Elo',

    # Hipercard
    r'\bhipercard\b': 'Hipercard',
    r'\bhiper\b': 'Hipercard',

    # Amex
    r'\bamerican\s*express\b': 'American Express',
    r'\bamex\b': 'American Express',

    # Cabal
    r'\bcabal\s*(pre.?pago|prepago)\b': 'Cabal Pré-pago',
    r'\bcabal\b': 'Cabal',

    # Outros
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
    r'\bdebito\b|\bd[ée]bito\b|\bdebit\b': 'Débito',
    r'\bcredito\b|\bcr[eé]dito\b|\bcredit\b': 'Crédito',
    r'\bpre.?pago\b|\bprepago\b': 'Pré-pago',
    r'\bcontactless\b|\bsem\s*contato\b': 'Contactless',
}

# ══════════════════════════════════════════════════════════════
#  PROCESSAMENTO DE IMAGEM / OCR
# ══════════════════════════════════════════════════════════════

def preprocessar_imagem(frame):
    """Pré-processa frame para melhor OCR."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Aumentar contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    # Denoising suave
    gray = cv2.fastNlMeansDenoising(gray, h=10)
    # Binarização adaptativa
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 21, 10
    )
    return binary


def extrair_texto_ocr(frame):
    """Extrai texto do frame usando o engine disponível."""
    global reader

    if OCR_ENGINE == "easyocr":
        if reader is None:
            reader = easyocr.Reader(['pt', 'en'], gpu=False)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resultados = reader.readtext(rgb)
        return ' '.join([r[1] for r in resultados])

    elif OCR_ENGINE == "tesseract":
        img_proc = preprocessar_imagem(frame)
        config = '--psm 6 -l por+eng'
        return pytesseract.image_to_string(img_proc, config=config)

    else:
        return ""


def extrair_bandeira(texto):
    texto_lower = texto.lower()
    # Testa padrões do mais específico para o mais genérico
    for padrao, nome in BANDEIRAS.items():
        if re.search(padrao, texto_lower):
            return nome
    return "Não identificada"


def extrair_tipo(texto):
    texto_lower = texto.lower()
    # Verifica pré-pago antes de crédito/débito
    if re.search(r'\bpre.?pago\b|\bprepago\b', texto_lower):
        return 'Pré-pago'
    for padrao, tipo in TIPOS.items():
        if re.search(padrao, texto_lower):
            return tipo
    return "Não identificado"


def extrair_valor(texto):
    """Extrai valor monetário do texto (R$ x.xxx,xx ou x,xx)."""
    padroes = [
        r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2}))',
        r'R\$\s*(\d+[,\.]\d{2})',
        r'TOTAL[:\s]*R?\$?\s*(\d+[,\.]\d{2})',
        r'VALOR[:\s]*R?\$?\s*(\d+[,\.]\d{2})',
        r'(?<!\d)(\d{1,3}(?:\.\d{3})*,\d{2})(?!\d)',
    ]
    for padrao in padroes:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            val_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                val = float(val_str)
                if 0.01 <= val <= 99999.99:
                    return val
            except ValueError:
                continue
    return None


def extrair_data(texto):
    """Extrai data do texto em vários formatos."""
    padroes = [
        r'(\d{2})[/\-\.](\d{2})[/\-\.](\d{4})',
        r'(\d{2})[/\-\.](\d{2})[/\-\.](\d{2})(?!\d)',
        r'(\d{4})[/\-\.](\d{2})[/\-\.](\d{2})',
    ]
    for padrao in padroes:
        match = re.search(padrao, texto)
        if match:
            try:
                g = match.groups()
                if len(g[2]) == 4:  # DD/MM/YYYY
                    d = date(int(g[2]), int(g[1]), int(g[0]))
                elif len(g[0]) == 4:  # YYYY/MM/DD
                    d = date(int(g[0]), int(g[1]), int(g[2]))
                else:  # DD/MM/YY
                    ano = 2000 + int(g[2]) if int(g[2]) < 50 else 1900 + int(g[2])
                    d = date(ano, int(g[1]), int(g[0]))
                return d
            except ValueError:
                continue
    return None


def analisar_nota(frame):
    """Pipeline completo de análise de uma nota."""
    texto = extrair_texto_ocr(frame)
    if not texto.strip():
        return None

    return {
        'bandeira': extrair_bandeira(texto),
        'tipo': extrair_tipo(texto),
        'valor': extrair_valor(texto),
        'data': extrair_data(texto),
        'texto_bruto': texto,
    }


# ══════════════════════════════════════════════════════════════
#  EXPORTAÇÃO EXCEL
# ══════════════════════════════════════════════════════════════

def exportar_excel(registros, data_sessao, caminho):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Notas {data_sessao}"

    # Estilos
    header_fill = PatternFill("solid", fgColor="1A1A2E")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    alt_fill = PatternFill("solid", fgColor="F0F4FF")
    ok_fill = PatternFill("solid", fgColor="D4EDDA")
    warn_fill = PatternFill("solid", fgColor="FFF3CD")
    err_fill = PatternFill("solid", fgColor="F8D7DA")
    border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC'),
    )

    # Cabeçalho
    headers = ['#', 'Bandeira', 'Tipo', 'Valor (R$)', 'Data da Nota', 'Data Sessão', 'Status Data', 'Hora Captura']
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border

    ws.row_dimensions[1].height = 25

    # Dados
    total = 0.0
    for i, reg in enumerate(registros, 1):
        row = i + 1
        data_nota = reg['data'].strftime('%d/%m/%Y') if reg['data'] else '—'
        status = reg.get('status_data', 'OK')

        valores_row = [
            i,
            reg['bandeira'],
            reg['tipo'],
            reg['valor'] if reg['valor'] else 0,
            data_nota,
            data_sessao,
            status,
            reg.get('hora', ''),
        ]

        fill = ok_fill if status == 'OK' else warn_fill
        if i % 2 == 0 and status == 'OK':
            fill = alt_fill

        for col, val in enumerate(valores_row, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.fill = fill
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center')
            if col == 4 and isinstance(val, (int, float)):
                cell.number_format = 'R$ #,##0.00'

        if reg['valor']:
            total += reg['valor']

    # Linha de totais
    row_total = len(registros) + 2
    ws.cell(row=row_total, column=1, value='TOTAL').font = Font(bold=True)
    ws.cell(row=row_total, column=3, value=f'{len(registros)} nota(s)').font = Font(bold=True)
    cell_total = ws.cell(row=row_total, column=4, value=total)
    cell_total.font = Font(bold=True, color="1A1A2E")
    cell_total.number_format = 'R$ #,##0.00'

    # Larguras das colunas
    larguras = [5, 22, 16, 14, 16, 14, 14, 14]
    for col, larg in enumerate(larguras, 1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = larg

    wb.save(caminho)
    return total


# ══════════════════════════════════════════════════════════════
#  INTERFACE GRÁFICA
# ══════════════════════════════════════════════════════════════

class AppOCR:
    def __init__(self, root):
        self.root = root
        self.root.title("📋 Leitor de Notas de Cartão")
        self.root.geometry("1280x780")
        self.root.configure(bg="#0F0F1A")
        self.root.resizable(True, True)

        self.cap = None
        self.capturando = False
        self.frame_atual = None
        self.registros = []
        self.data_sessao = date.today()
        self.thread_camera = None
        self.lock = threading.Lock()

        # Estado da leitura
        # 'idle'       → câmera ao vivo, aguardando nota
        # 'scanning'   → OCR rodando em background
        # 'preview'    → nota detectada, aguardando Enter/Esc do usuário
        self.estado = 'idle'
        self.resultado_pendente = None   # nota detectada aguardando confirmação
        self.ocr_em_andamento = False
        self.cooldown_scan = 2.0         # seg entre tentativas de OCR no modo idle

        self._build_ui()
        self._atualizar_status_engine()

        # Bind de teclado global
        self.root.bind('<Return>', self._on_enter)
        self.root.bind('<KP_Enter>', self._on_enter)
        self.root.bind('<Escape>', self._on_esc)

    # ── UI ─────────────────────────────────────────────────────

    def _build_ui(self):
        font_title = ("Courier New", 16, "bold")
        font_label = ("Courier New", 10)
        font_mono  = ("Courier New", 9)

        style = ttk.Style()

        # ══ Painel esquerdo: câmera + preview da nota ══
        left = tk.Frame(self.root, bg="#0F0F1A", width=530)
        left.pack(side="left", fill="y", padx=(14, 6), pady=14)
        left.pack_propagate(False)

        # Título + engine
        top_row = tk.Frame(left, bg="#0F0F1A")
        top_row.pack(fill="x", pady=(0, 10))
        tk.Label(top_row, text="◈ OCR NOTAS CARTÃO", font=font_title,
                 bg="#0F0F1A", fg="#00D4FF").pack(side="left")
        self.label_engine = tk.Label(top_row, text="", font=("Courier New", 8),
                                      bg="#0F0F1A", fg="#444455")
        self.label_engine.pack(side="right")

        # Seleção de data da sessão
        date_frame = tk.Frame(left, bg="#1A1A2E")
        date_frame.pack(fill="x", pady=(0, 8))
        tk.Label(date_frame, text="  DATA DA SESSÃO:", font=font_label,
                 bg="#1A1A2E", fg="#888888").pack(side="left", padx=(8, 4), pady=8)

        self.var_dia = tk.StringVar(value=str(date.today().day).zfill(2))
        self.var_mes = tk.StringVar(value=str(date.today().month).zfill(2))
        self.var_ano = tk.StringVar(value=str(date.today().year))

        spin_opts = dict(bg="#1A1A2E", fg="#00D4FF", font=("Courier New", 11, "bold"),
                         bd=0, relief="flat", insertbackground="#00D4FF",
                         highlightthickness=1, highlightcolor="#00D4FF",
                         highlightbackground="#333355")
        tk.Spinbox(date_frame, from_=1, to=31, textvariable=self.var_dia,
                   width=3, **spin_opts, command=self._update_data_sessao).pack(side="left")
        tk.Label(date_frame, text="/", bg="#1A1A2E", fg="#555566",
                 font=("Courier New", 12)).pack(side="left")
        tk.Spinbox(date_frame, from_=1, to=12, textvariable=self.var_mes,
                   width=3, **spin_opts, command=self._update_data_sessao).pack(side="left")
        tk.Label(date_frame, text="/", bg="#1A1A2E", fg="#555566",
                 font=("Courier New", 12)).pack(side="left")
        tk.Spinbox(date_frame, from_=2020, to=2099, textvariable=self.var_ano,
                   width=6, **spin_opts, command=self._update_data_sessao).pack(side="left", padx=(0, 8))

        # ── Preview câmera ──
        cam_border = tk.Frame(left, bg="#1A3A5C", bd=1)
        cam_border.pack(fill="x", pady=(0, 6))
        self.label_cam = tk.Label(cam_border, bg="#0A0A14",
                                   text="[ CÂMERA INATIVA ]",
                                   font=("Courier New", 11), fg="#222244",
                                   width=66, height=16)
        self.label_cam.pack(padx=1, pady=1)

        # Status ao vivo
        self.label_status = tk.Label(left, text="● AGUARDANDO",
                                      font=("Courier New", 10, "bold"),
                                      bg="#0F0F1A", fg="#555566")
        self.label_status.pack(anchor="w", pady=(0, 6))

        # ══ PAINEL DE PREVIEW DA NOTA (aparece quando detecta) ══
        self.frame_preview = tk.Frame(left, bg="#0A1A0A",
                                       highlightthickness=2,
                                       highlightbackground="#00FF88")
        # Não empacota ainda — só aparece quando há nota detectada

        tk.Label(self.frame_preview, text="NOTA DETECTADA — CONFIRME OS DADOS",
                 font=("Courier New", 9, "bold"), bg="#0A1A0A", fg="#00FF88"
                 ).pack(anchor="w", padx=10, pady=(8, 4))

        # Campos do preview (editáveis pelo usuário)
        campos_frame = tk.Frame(self.frame_preview, bg="#0A1A0A")
        campos_frame.pack(fill="x", padx=10, pady=4)

        lbl_style = dict(bg="#0A1A0A", fg="#888899", font=("Courier New", 9), anchor="w", width=12)
        val_style = dict(bg="#0F1A0F", fg="#FFFFFF", font=("Courier New", 11, "bold"),
                         relief="flat", bd=0, insertbackground="#00FF88",
                         highlightthickness=1, highlightcolor="#00FF88",
                         highlightbackground="#224422")

        # Bandeira
        tk.Label(campos_frame, text="Bandeira:", **lbl_style).grid(row=0, column=0, sticky="w", pady=3)
        self.entry_bandeira = tk.Entry(campos_frame, width=26, **val_style)
        self.entry_bandeira.grid(row=0, column=1, sticky="ew", pady=3, padx=(4, 0))

        # Tipo
        tk.Label(campos_frame, text="Tipo:", **lbl_style).grid(row=1, column=0, sticky="w", pady=3)
        self.var_tipo = tk.StringVar()
        tipo_opts = ['Crédito', 'Débito', 'Pré-pago', 'Contactless', 'Não identificado']
        self.combo_tipo = ttk.Combobox(campos_frame, textvariable=self.var_tipo,
                                        values=tipo_opts, width=24, state="readonly",
                                        font=("Courier New", 10))
        self.combo_tipo.grid(row=1, column=1, sticky="ew", pady=3, padx=(4, 0))

        # Valor
        tk.Label(campos_frame, text="Valor (R$):", **lbl_style).grid(row=2, column=0, sticky="w", pady=3)
        self.entry_valor = tk.Entry(campos_frame, width=26, **val_style)
        self.entry_valor.grid(row=2, column=1, sticky="ew", pady=3, padx=(4, 0))

        # Data da nota
        tk.Label(campos_frame, text="Data nota:", **lbl_style).grid(row=3, column=0, sticky="w", pady=3)
        self.entry_data = tk.Entry(campos_frame, width=26, **val_style)
        self.entry_data.grid(row=3, column=1, sticky="ew", pady=3, padx=(4, 0))

        campos_frame.columnconfigure(1, weight=1)

        # Alerta de data
        self.label_alerta_data = tk.Label(self.frame_preview, text="",
                                           font=("Courier New", 9, "bold"),
                                           bg="#0A1A0A", fg="#FFCC00")
        self.label_alerta_data.pack(anchor="w", padx=10)

        # Botões de confirmação
        btn_confirm_row = tk.Frame(self.frame_preview, bg="#0A1A0A")
        btn_confirm_row.pack(fill="x", padx=10, pady=(6, 10))

        self.btn_confirmar = tk.Button(
            btn_confirm_row,
            text="✔  CONFIRMAR  [ ENTER ]",
            font=("Courier New", 10, "bold"),
            bg="#00FF88", fg="#0A1A0A", activebackground="#00CC66",
            relief="flat", cursor="hand2", height=2,
            command=self._confirmar_nota
        )
        self.btn_confirmar.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_rejeitar = tk.Button(
            btn_confirm_row,
            text="✕ DESCARTAR  [ ESC ]",
            font=("Courier New", 10, "bold"),
            bg="#1A0A0A", fg="#FF4466", activebackground="#2A0A0A",
            relief="flat", cursor="hand2", height=2,
            command=self._rejeitar_nota
        )
        self.btn_rejeitar.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # ── Botão principal de câmera ──
        self.btn_iniciar = tk.Button(
            left, text="▶  INICIAR CÂMERA",
            font=("Courier New", 11, "bold"),
            bg="#00D4FF", fg="#0F0F1A", activebackground="#00AACC",
            relief="flat", cursor="hand2", height=2,
            command=self._toggle_camera
        )
        self.btn_iniciar.pack(fill="x", pady=(6, 0))

        # ══ Painel direito: tabela ══
        right = tk.Frame(self.root, bg="#0F0F1A")
        right.pack(side="right", fill="both", expand=True, padx=(0, 14), pady=14)

        hdr = tk.Frame(right, bg="#0F0F1A")
        hdr.pack(fill="x", pady=(22, 8))
        tk.Label(hdr, text="REGISTROS DA SESSÃO",
                 font=("Courier New", 13, "bold"),
                 bg="#0F0F1A", fg="#FFFFFF").pack(side="left")

        self.btn_exportar = tk.Button(
            hdr, text="⬇  EXPORTAR EXCEL",
            font=("Courier New", 9, "bold"),
            bg="#00FF88", fg="#0F0F1A", activebackground="#00CC66",
            relief="flat", cursor="hand2", padx=12, pady=4,
            command=self._exportar
        )
        self.btn_exportar.pack(side="right")

        self.btn_limpar = tk.Button(
            hdr, text="✕ LIMPAR",
            font=("Courier New", 9),
            bg="#1A1A2E", fg="#FF4466", activebackground="#2A1A2E",
            relief="flat", cursor="hand2", padx=8, pady=4,
            command=self._limpar_tabela
        )
        self.btn_limpar.pack(side="right", padx=(0, 8))

        # Tabela
        cols = ('n', 'bandeira', 'tipo', 'valor', 'data_nota', 'status', 'hora')
        self.tree = ttk.Treeview(right, columns=cols, show='headings', height=24)

        style.configure("Treeview",
                         background="#0F0F1A", foreground="#CCCCDD",
                         fieldbackground="#0F0F1A", rowheight=26,
                         font=("Courier New", 9))
        style.configure("Treeview.Heading",
                         background="#1A1A2E", foreground="#00D4FF",
                         font=("Courier New", 9, "bold"), relief="flat")
        style.map("Treeview", background=[('selected', '#2A2A4E')])

        for col, label, width in [
            ('n', '#', 38), ('bandeira', 'Bandeira', 160), ('tipo', 'Tipo', 100),
            ('valor', 'Valor', 100), ('data_nota', 'Data Nota', 100),
            ('status', 'Status', 90), ('hora', 'Hora', 75)
        ]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, anchor='center')

        self.tree.tag_configure('ok',   background='#0A1A0A', foreground='#00FF88')
        self.tree.tag_configure('warn', background='#1A1500', foreground='#FFCC00')
        self.tree.tag_configure('alt',  background='#0F0F20', foreground='#AAAACC')

        sb = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)

        tree_wrap = tk.Frame(right, bg="#00D4FF", bd=1)
        tree_wrap.pack(fill="both", expand=True)
        self.tree.pack(in_=tree_wrap, fill="both", expand=True, padx=1, pady=1)
        sb.pack(side="right", fill="y")

        # Rodapé totais
        footer = tk.Frame(right, bg="#1A1A2E")
        footer.pack(fill="x", pady=(8, 0))

        self.lbl_qtd = tk.Label(footer, text="Notas: 0",
                                 font=("Courier New", 11, "bold"),
                                 bg="#1A1A2E", fg="#888899", pady=10)
        self.lbl_qtd.pack(side="left", padx=16)

        self.lbl_total = tk.Label(footer, text="Total: R$ 0,00",
                                   font=("Courier New", 14, "bold"),
                                   bg="#1A1A2E", fg="#00FF88", pady=10)
        self.lbl_total.pack(side="right", padx=16)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Câmera ─────────────────────────────────────────────────

    def _toggle_camera(self):
        if self.capturando:
            self._parar_camera()
        else:
            self._iniciar_camera()

    def _iniciar_camera(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror("Erro", "Câmera não encontrada.\nVerifique a conexão.")
            return
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.capturando = True
        self.estado = 'idle'
        self.btn_iniciar.config(text="■  PARAR CÂMERA", bg="#FF4466",
                                 fg="#FFFFFF", activebackground="#CC2244")
        self.label_status.config(text="● POSICIONE A NOTA NA CÂMERA", fg="#00D4FF")
        self.thread_camera = threading.Thread(target=self._loop_camera, daemon=True)
        self.thread_camera.start()

    def _parar_camera(self):
        self.capturando = False
        self.estado = 'idle'
        if self.cap:
            self.cap.release()
            self.cap = None
        self.btn_iniciar.config(text="▶  INICIAR CÂMERA", bg="#00D4FF",
                                 fg="#0F0F1A", activebackground="#00AACC")
        self.label_cam.config(image='', text="[ CÂMERA INATIVA ]")
        self.label_status.config(text="● CÂMERA PARADA", fg="#555566")
        self._esconder_preview()

    def _loop_camera(self):
        ultimo_scan = 0.0

        while self.capturando:
            ret, frame = self.cap.read()
            if not ret:
                break

            with self.lock:
                self.frame_atual = frame.copy()

            h, w = frame.shape[:2]
            mx, my = int(w * 0.05), int(h * 0.05)

            # ── Modo PREVIEW: congela imagem e aguarda usuário ──
            if self.estado == 'preview':
                display = frame.copy()
                cv2.rectangle(display, (mx, my), (w - mx, h - my), (0, 255, 136), 3)
                cv2.putText(display, "ENTER = confirmar   ESC = descartar",
                            (mx + 4, h - 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 136), 1)
                self._mostrar_frame(display)
                time.sleep(0.033)
                continue

            # ── Modo IDLE: câmera ao vivo + OCR periódico ──
            display = frame.copy()
            agora = time.time()

            if self.estado == 'scanning':
                cor = (255, 200, 0)
                cv2.putText(display, "LENDO...", (mx + 4, my - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 1)
            else:
                cor = (0, 180, 255)
                cv2.putText(display, "POSICIONE A NOTA",
                            (mx + 4, my - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 1)

                # Disparar OCR se cooldown passou e não há OCR rodando
                if not self.ocr_em_andamento and (agora - ultimo_scan) >= self.cooldown_scan:
                    ultimo_scan = agora
                    self.estado = 'scanning'
                    self.ocr_em_andamento = True
                    threading.Thread(target=self._processar_frame,
                                     args=(frame.copy(),), daemon=True).start()

            cv2.rectangle(display, (mx, my), (w - mx, h - my), cor, 2)
            self._mostrar_frame(display)
            time.sleep(0.033)

    def _mostrar_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(rgb).resize((500, 310), Image.LANCZOS)
        imgtk = ImageTk.PhotoImage(img_pil)
        self.root.after(0, self._update_cam_label, imgtk)

    def _update_cam_label(self, imgtk):
        self.label_cam.configure(image=imgtk, text='')
        self.label_cam.image = imgtk

    # ── OCR e fluxo de confirmação ──────────────────────────────

    def _processar_frame(self, frame):
        """Roda em thread separada. Ao detectar nota válida, entra em modo preview."""
        self.root.after(0, lambda: self.label_status.config(
            text="⟳ ANALISANDO NOTA...", fg="#FFCC00"))

        resultado = analisar_nota(frame)

        self.ocr_em_andamento = False

        if resultado is None or resultado['valor'] is None:
            # Nada útil detectado → volta para idle silenciosamente
            self.estado = 'idle'
            self.root.after(0, lambda: self.label_status.config(
                text="● POSICIONE A NOTA NA CÂMERA", fg="#00D4FF"))
            return

        # Nota detectada! Guarda e mostra o painel de confirmação
        self.resultado_pendente = resultado
        self.estado = 'preview'
        self.root.after(0, self._mostrar_painel_preview, resultado)

    def _mostrar_painel_preview(self, resultado):
        """Preenche e exibe o painel de confirmação com os dados lidos."""
        # Preenche os campos (editáveis pelo usuário)
        self.entry_bandeira.delete(0, 'end')
        self.entry_bandeira.insert(0, resultado['bandeira'])

        self.var_tipo.set(resultado['tipo'] if resultado['tipo'] in
                          ['Crédito', 'Débito', 'Pré-pago', 'Contactless'] else 'Não identificado')

        self.entry_valor.delete(0, 'end')
        self.entry_valor.insert(0, f"{resultado['valor']:.2f}".replace('.', ','))

        data_str = resultado['data'].strftime('%d/%m/%Y') if resultado['data'] else ''
        self.entry_data.delete(0, 'end')
        self.entry_data.insert(0, data_str)

        # Alerta de data
        data_nota = resultado['data']
        if data_nota is None:
            self.label_alerta_data.config(
                text="⚠  Data não identificada na nota", fg="#FFCC00")
        elif data_nota != self.data_sessao:
            self.label_alerta_data.config(
                text=f"⚠  Data da nota ({data_nota.strftime('%d/%m/%Y')}) ≠ sessão ({self.data_sessao.strftime('%d/%m/%Y')})",
                fg="#FF6644")
        else:
            self.label_alerta_data.config(
                text=f"✔  Data OK ({data_nota.strftime('%d/%m/%Y')})", fg="#00FF88")

        # Exibe o painel
        self.frame_preview.pack(fill="x", pady=(0, 8), before=self.btn_iniciar)

        self.label_status.config(
            text="◉ NOTA DETECTADA — CONFIRME OU DESCARTE", fg="#00FF88")

        # Foco no botão confirmar para que Enter funcione diretamente
        self.btn_confirmar.focus_set()

    def _esconder_preview(self):
        self.frame_preview.pack_forget()

    def _on_enter(self, event=None):
        if self.estado == 'preview':
            self._confirmar_nota()

    def _on_esc(self, event=None):
        if self.estado == 'preview':
            self._rejeitar_nota()

    def _confirmar_nota(self):
        """Lê os campos (possivelmente editados), valida e adiciona à tabela."""
        if self.estado != 'preview' or self.resultado_pendente is None:
            return

        # Lê valores dos campos (o usuário pode ter corrigido)
        bandeira = self.entry_bandeira.get().strip() or "Não identificada"
        tipo     = self.var_tipo.get() or "Não identificado"
        data_str = self.entry_data.get().strip()

        # Valor — aceita vírgula ou ponto
        try:
            valor = float(self.entry_valor.get().replace(',', '.'))
        except ValueError:
            messagebox.showwarning("Valor inválido",
                                   "Corrija o valor antes de confirmar.\nUse ponto ou vírgula como decimal.")
            return

        # Parse da data do campo (pode ter sido editada)
        data_nota = None
        if data_str:
            try:
                data_nota = datetime.strptime(data_str, '%d/%m/%Y').date()
            except ValueError:
                pass

        # Determina status de data
        if data_nota is None:
            status_data = "S/DATA"
        elif data_nota != self.data_sessao:
            # Pede confirmação apenas se data diverge
            ok = messagebox.askyesno(
                "⚠ Data diferente",
                f"A data da nota ({data_str}) é diferente da sessão "
                f"({self.data_sessao.strftime('%d/%m/%Y')}).\n\nConfirmar mesmo assim?"
            )
            if not ok:
                return  # Fica no modo preview
            status_data = "⚠ DIF."
        else:
            status_data = "OK"

        reg = {
            'bandeira': bandeira,
            'tipo': tipo,
            'valor': valor,
            'data': data_nota,
            'status_data': status_data,
            'hora': datetime.now().strftime('%H:%M:%S'),
        }
        self._adicionar_registro(reg)
        self._fechar_preview()

    def _rejeitar_nota(self):
        """Descarta a nota detectada e volta a escanear."""
        self._fechar_preview()

    def _fechar_preview(self):
        self.resultado_pendente = None
        self.estado = 'idle'
        self._esconder_preview()
        self.label_status.config(text="● POSICIONE A NOTA NA CÂMERA", fg="#00D4FF")

    def _adicionar_registro(self, reg):
        self.registros.append(reg)
        n = len(self.registros)
        data_str = reg['data'].strftime('%d/%m/%Y') if reg['data'] else '—'
        status = reg.get('status_data', 'OK')
        tag = 'warn' if status != 'OK' else ('alt' if n % 2 == 0 else 'ok')

        self.tree.insert('', 'end', values=(
            n, reg['bandeira'], reg['tipo'],
            f"R$ {reg['valor']:.2f}".replace('.', ','),
            data_str, status, reg['hora'],
        ), tags=(tag,))
        self.tree.yview_moveto(1.0)
        self._atualizar_totais()

    def _update_txt_ocr(self, texto):
        pass  # mantido por compatibilidade

    # ── Utilitários ────────────────────────────────────────────

    def _update_data_sessao(self):
        try:
            self.data_sessao = date(
                int(self.var_ano.get()),
                int(self.var_mes.get()),
                int(self.var_dia.get())
            )
        except ValueError:
            pass

    def _atualizar_totais(self):
        total = sum(r['valor'] for r in self.registros if r['valor'])
        self.lbl_qtd.config(text=f"Notas: {len(self.registros)}")
        self.lbl_total.config(text=f"Total: R$ {total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

    def _atualizar_status_engine(self):
        msgs = {
            "easyocr": "Engine: EasyOCR ✓",
            "tesseract": "Engine: Tesseract ✓",
            "none": "⚠ Nenhum OCR instalado",
        }
        cores = {"easyocr": "#00FF88", "tesseract": "#00FF88", "none": "#FF4466"}
        self.label_engine.config(text=msgs[OCR_ENGINE], fg=cores[OCR_ENGINE])

    def _exportar(self):
        if not self.registros:
            messagebox.showwarning("Vazio", "Nenhum registro para exportar.")
            return
        nome = f"notas_{self.data_sessao.strftime('%Y%m%d')}_{datetime.now().strftime('%H%M%S')}.xlsx"
        caminho = os.path.join(os.path.expanduser("~"), "Desktop", nome)
        try:
            total = exportar_excel(self.registros, self.data_sessao.strftime('%d/%m/%Y'), caminho)
            messagebox.showinfo(
                "Exportado!",
                f"Planilha salva em:\n{caminho}\n\n"
                f"Notas: {len(self.registros)}\nTotal: R$ {total:,.2f}"
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar:\n{e}")

    def _limpar_tabela(self):
        if self.registros and messagebox.askyesno("Limpar", "Deseja limpar todos os registros?"):
            self.registros.clear()
            for item in self.tree.get_children():
                self.tree.delete(item)
            self._atualizar_totais()

    def _on_close(self):
        self._parar_camera()
        self.root.destroy()


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    app = AppOCR(root)
    root.mainloop()
