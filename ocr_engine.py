# ─── ocr_engine.py ────────────────────────────────────────────────────────────
# Toda lógica de OCR: inicialização do reader, pré-processamento de imagem,
# extração de bandeira, tipo, valor e data.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Optional

import cv2
import numpy as np

from config import BANDEIRAS_REGRAS, TIPOS_REGRAS

# ── Detecção de engine disponível ──────────────────────────────────────────
try:
    import easyocr as _easyocr
    OCR_ENGINE = "easyocr"
    _reader: Optional[_easyocr.Reader] = None
except ImportError:
    try:
        import pytesseract as _pytesseract  # type: ignore
        OCR_ENGINE = "tesseract"
    except ImportError:
        OCR_ENGINE = "none"


# ── Reader singleton ────────────────────────────────────────────────────────
def get_reader() -> "_easyocr.Reader":
    """Inicializa e retorna o reader EasyOCR (singleton, thread-safe via GIL)."""
    global _reader
    if _reader is None:
        _reader = _easyocr.Reader(['pt', 'en'], gpu=False, verbose=False)
    return _reader


# ── Pré-processamento de imagem ─────────────────────────────────────────────
def _preparar_gray(frame: np.ndarray, min_width: int = 960) -> np.ndarray:
    """Converte BGR→gray, escala para largura mínima e aplica CLAHE."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    if w < min_width:
        scale = min_width / w
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)),
                          interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _rotacionar(frame: np.ndarray, angulo: float) -> np.ndarray:
    h, w = frame.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angulo, 1.0)
    return cv2.warpAffine(frame, M, (w, h),
                          flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


# ── Reconstrução de linhas a partir de bboxes ───────────────────────────────
def _readtext_para_textos(resultado: list) -> tuple[str, str]:
    """
    Converte lista EasyOCR (detail=1) em (texto_flat, texto_linhas).
    Agrupa tokens por linha usando posição Y dos bboxes.
    """
    if not resultado:
        return '', ''

    itens = sorted(resultado, key=lambda r: (r[0][0][1] + r[0][2][1]) / 2)
    linhas: list[list] = [[itens[0]]]

    for item in itens[1:]:
        y_prev = (linhas[-1][-1][0][0][1] + linhas[-1][-1][0][2][1]) / 2
        y_curr = (item[0][0][1] + item[0][2][1]) / 2
        altura = max(abs(item[0][2][1] - item[0][0][1]), 10)
        if abs(y_curr - y_prev) < altura * 0.8:
            linhas[-1].append(item)
        else:
            linhas.append([item])

    partes = [
        ' '.join(tok[1] for tok in sorted(ln, key=lambda r: r[0][0][0]))
        for ln in linhas
    ]
    return ' '.join(partes), '\n'.join(partes)


# ── OCR principal ────────────────────────────────────────────────────────────
def extrair_ocr_completo(frame: np.ndarray) -> tuple[str, str]:
    """
    Uma única passagem OCR sobre o frame BGR.
    Retorna (texto_flat, texto_linhas).
    """
    if OCR_ENGINE == "easyocr":
        gray = _preparar_gray(frame)
        rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        resultado = get_reader().readtext(rgb, detail=1, paragraph=False)
        return _readtext_para_textos(resultado)

    if OCR_ENGINE == "tesseract":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        binary = cv2.adaptiveThreshold(gray, 255,
                                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                        cv2.THRESH_BINARY, 21, 10)
        texto = _pytesseract.image_to_string(binary, config='--psm 6 -l por+eng')
        return texto, texto

    return '', ''


# ── Normalização de texto ────────────────────────────────────────────────────
def normalizar(texto: str) -> str:
    """Lowercase, remove acentos, mantém apenas [a-z0-9$] e espaços."""
    t = (texto or '').lower()
    t = ''.join(
        ch for ch in unicodedata.normalize('NFD', t)
        if unicodedata.category(ch) != 'Mn'
    )
    t = re.sub(r'[^a-z0-9$]+', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def _match_regras(texto: str, regras: list[tuple[str, str]]) -> Optional[str]:
    tl, tn = texto.lower(), normalizar(texto)
    for padrao, nome in regras:
        if re.search(padrao, tl) or re.search(padrao, tn):
            return nome
    return None


# ── Extração de campos ──────────────────────────────────────────────────────
def extrair_bandeira(texto: str) -> Optional[str]:
    return _match_regras(texto, BANDEIRAS_REGRAS)


def extrair_tipo(texto: str) -> Optional[str]:
    tn = normalizar(texto)
    # Linha Cielo: "PREPAGO MASTERCARD - DEBITO A VISTA"
    m = re.search(
        r'\b(?:prepago\s+)?(?:visa|mastercard|elo|hipercard|amex|cabal)\b\s*[-:]\s*([a-z0-9\s]{6,40})',
        tn,
    )
    if m:
        tipo = _match_regras(m.group(1), TIPOS_REGRAS)
        if tipo:
            return tipo
    return _match_regras(texto, TIPOS_REGRAS)


def extrair_pix_instituicao(texto: str) -> Optional[str]:
    tn = normalizar(texto)
    if not re.search(r'\bp[il1]x\b', tn):
        return None
    if re.search(r'\bs[il1]co+b\b', tn):
        return 'Sicoob'
    if re.search(r'\bcaixa\b|\bcef\b|caixa\s*economica', tn):
        return 'Caixa'
    return None


# ── Valor ───────────────────────────────────────────────────────────────────
def _parse_valor(raw: str) -> float:
    s = raw.strip().replace(' ', '')
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    else:
        partes = s.split('.')
        if len(partes) > 2:
            s = ''.join(partes[:-1]) + '.' + partes[-1]
    return float(s)


def _e_fragmento_data(texto: str, ini: int, fim: int) -> bool:
    janela = texto[max(0, ini - 14): min(len(texto), fim + 14)]
    antes  = texto[max(0, ini - 4): ini]
    depois = texto[fim: min(len(texto), fim + 4)]
    if re.search(r'\d{1,2}\s*[/\-.]\s*\d{1,2}\s*[/\-.]\s*\d{2,4}', janela):
        return True
    if re.search(r'\d{1,2}:\d{2}(?::\d{2})?', janela):
        return True
    if re.search(r'[-/.]\s*$', antes) or re.search(r'^\s*[-/.]', depois):
        return True
    return False


def extrair_valor(texto: str) -> Optional[float]:
    candidatos: list[float] = []

    _PADROES_PRIORITARIOS = [
        r'\bp[il1]x\b\s*(?:r\$\s*)?(\d{1,3}(?:[\.,]\d{3})*[\.,]\d{2}|\d+[\.,]\d{2})',
        r'\br\$\s*(\d{1,3}(?:[\.,]\d{3})*[\.,]\d{2}|\d+[\.,]\d{2})',
        r'\bvalor\b[\s:.-]*(?:r\$\s*)?(\d{1,3}(?:[\.,]\d{3})*[\.,]\d{2}|\d+[\.,]\d{2})',
    ]
    for p in _PADROES_PRIORITARIOS:
        for m in re.finditer(p, texto, re.IGNORECASE):
            if _e_fragmento_data(texto, m.start(1), m.end(1)):
                continue
            try:
                v = _parse_valor(m.group(1))
                if 0.01 <= v <= 99_999.99:
                    candidatos.append(v)
            except Exception:
                pass

    # Último recurso: número monetário isolado
    for m in re.finditer(
        r'(?<![\d/\-])(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+\.\d{2})(?![\d/])',
        texto, re.IGNORECASE
    ):
        if _e_fragmento_data(texto, m.start(1), m.end(1)):
            continue
        try:
            v = _parse_valor(m.group(1))
            if 0.01 <= v <= 99_999.99:
                candidatos.append(v)
        except Exception:
            pass

    return max(candidatos) if candidatos else None


def extrair_valor_pix_layout(texto_linhas: str) -> Optional[float]:
    if not texto_linhas:
        return None
    linhas = [l.strip() for l in texto_linhas.splitlines() if l.strip()]

    for ln in linhas:
        if re.search(r'\bp[il1]x\b', ln, re.IGNORECASE):
            m = re.search(
                r'\bp[il1]x\b[^0-9]{0,10}(?:r\$\s*)?'
                r'(\d{1,3}(?:[\.,]\d{3})*[\.,]\d{2}|\d+[\.,]\d{2}|\d+\s\d{2})',
                ln, re.IGNORECASE,
            )
            if m:
                try:
                    v = _parse_valor(m.group(1).replace(' ', '.'))
                    if 0.01 <= v <= 99_999.99:
                        return v
                except Exception:
                    pass
            v = extrair_valor(ln)
            if v is not None:
                return v

    for ln in linhas:
        if re.search(r'\bvalor\b', ln, re.IGNORECASE):
            v = extrair_valor(ln)
            if v is not None:
                return v
    return None


# ── Data ────────────────────────────────────────────────────────────────────
def _parse_data_str(s: str) -> Optional[date]:
    s = re.sub(r'\s+', '', s)
    m = re.match(r'^(\d{2})[/\-.](\d{2})[/\-.](\d{2,4})$', s)
    if not m:
        return None
    d, mo, a = m.groups()
    try:
        aa = int(a)
        if len(a) == 2:
            aa = 2000 + aa if aa < 50 else 1900 + aa
        return date(aa, int(mo), int(d))
    except Exception:
        return None


def extrair_data(texto: str) -> Optional[date]:
    for p in [
        r'(\d{2})\s*[/\-\.]\s*(\d{2})\s*[/\-\.]\s*(\d{4})',
        r'(\d{4})\s*[/\-\.]\s*(\d{2})\s*[/\-\.]\s*(\d{2})',
        r'(\d{2})\s*[/\-\.]\s*(\d{2})\s*[/\-\.]\s*(\d{2})\b',
    ]:
        m = re.search(p, texto)
        if m:
            try:
                g = m.groups()
                if len(g[2]) == 4:
                    return date(int(g[2]), int(g[1]), int(g[0]))
                elif len(g[0]) == 4:
                    return date(int(g[0]), int(g[1]), int(g[2]))
                else:
                    aa = 2000 + int(g[2]) if int(g[2]) < 50 else 1900 + int(g[2])
                    return date(aa, int(g[1]), int(g[0]))
            except Exception:
                pass
    return None


def extrair_data_pix_layout(texto_linhas: str) -> Optional[date]:
    if not texto_linhas:
        return None
    m = re.search(
        r'(?im)^\s*(\d{2}\s*[/\-.]\s*\d{2}\s*[/\-.]\s*\d{2,4})\s+\d{1,2}:\d{2}(?::\d{2})?',
        texto_linhas,
    )
    if m:
        d = _parse_data_str(m.group(1))
        if d:
            return d
    for ln in texto_linhas.splitlines()[:6]:
        mm = re.search(r'(\d{2}\s*[/\-.]\s*\d{2}\s*[/\-.]\s*\d{2,4})', ln)
        if mm:
            d = _parse_data_str(mm.group(1))
            if d:
                return d
    return None


# ── Pipeline completo de um frame ───────────────────────────────────────────
def processar_frame(frame) -> Optional[dict]:
    """
    Executa OCR + extração de todos os campos em um frame BGR.
    Retorna dict com bandeira, tipo, valor, data, texto_bruto
    ou None se valor não encontrado.
    """
    texto, texto_linhas = extrair_ocr_completo(frame)
    bandeira = extrair_bandeira(texto)
    tipo     = extrair_tipo(texto)
    valor    = extrair_valor(texto)
    data_nota = extrair_data(texto)

    # Fallback com leve rotação
    if bandeira is None or tipo is None:
        for angulo in (-5, 5):
            t_r, _ = extrair_ocr_completo(_rotacionar(frame, angulo))
            if t_r:
                bandeira  = bandeira  or extrair_bandeira(t_r)
                tipo      = tipo      or extrair_tipo(t_r)
                valor     = valor     if valor is not None else extrair_valor(t_r)
                data_nota = data_nota or extrair_data(t_r)
            if bandeira and tipo:
                break

    # Refinamento PIX
    pix = (
        re.search(r'\bp[il1]x\b', normalizar(texto)) is not None
        or bandeira == 'PIX'
        or tipo == 'PIX'
    )
    if pix:
        valor_pix = extrair_valor_pix_layout(texto_linhas)
        data_pix  = extrair_data_pix_layout(texto_linhas)
        if valor_pix is not None:
            valor = valor_pix
        if data_pix is not None:
            data_nota = data_pix
        inst = extrair_pix_instituicao(texto)
        bandeira = 'PIX'
        tipo     = inst or 'Caixa'
        valor    = valor    or extrair_valor_pix_layout(texto_linhas)
        data_nota = data_nota or extrair_data_pix_layout(texto_linhas)

    if valor is None:
        return None

    return {
        'bandeira':    bandeira  or 'Não identificada',
        'tipo':        tipo      or 'Não identificado',
        'valor':       valor,
        'data':        data_nota,
        'texto_bruto': texto,
    }
