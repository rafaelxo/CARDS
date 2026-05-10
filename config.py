# ─── config.py ────────────────────────────────────────────────────────────────

APP_TITLE    = "Leitor de Notas · OCR"
APP_GEOMETRY = "1280x820"
APP_MINSIZE  = (1100, 720)

PREVIEW_W = 500
PREVIEW_H = 320

OCR_COOLDOWN_DEFAULT = 3.0   # segundos entre leituras automáticas
OCR_DIFF_THRESHOLD   = 3.5   # diferença mínima entre frames (evita re-leitura)
OCR_THUMB_SIZE       = (64, 48)

CAM_WIDTH  = 640
CAM_HEIGHT = 480
CAM_FPS    = 30

C: dict[str, str] = {
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

# ── Bandeiras reconhecidas — espelho exato do Config da planilha ─────────────
BANDEIRAS_REGRAS: list[tuple[str, str]] = [
    (r'pagamento\s*p[il1]x|p[il1]x\s*bacen|\bp[il1]x\b',                          'PIX'),
    (r'pre.{0,3}pago\s*m[ao4]ster|m[ao4]ster.{0,5}pre.{0,3}pago',                'Mastercard Pré-pago'),
    (r'pre.{0,3}pago\s*v[il1]sa|v[il1]sa\s*pre.{0,3}pago',                        'Visa Pré-pago'),
    (r'pre.{0,3}pago\s*el[o0]|el[o0]\s*pre.{0,3}pago',                            'Elo Pré-pago'),
    (r'cabal\s*pre.{0,3}pago|pre.{0,3}pago\s*cabal',                              'Cabal Pré-pago'),
    (r'\bv[il1j][s5][a4]\b',                                                       'Visa'),
    (r'\bm[a4][s5]t[e3]r\s*c[a4]rd\b|\bm[a4][s5]t[e3]rc[a4]rd\b',               'Mastercard'),
    (r'\bm[a4][s5]t[e3]r\b',                                                       'Mastercard'),
    (r'\bel[o0q]\b',                                                                'Elo'),
    (r'h[il1]p[e3]r\s*c[a4]rd|h[il1]p[e3]rc[a4]rd|\bh[il1]p[e3]r\b',            'Hipercard'),
    (r'am[e3]r[il1]c[a4]n\s*[e3]xpr[e3]ss|\b[a4]m[e3]x\b',                      'American Express'),
    (r'\bc[a4]b[a4]l\b',                                                            'Cabal'),
    (r'\b[a4]l[e3]lo\b',                                                            'Alelo'),
    (r'\bs[il1]co+b\b',                                                             'PIX'),
]

TIPOS_REGRAS: list[tuple[str, str]] = [
    (r'pagamento\s*p[il1]x|p[il1]x\s*r\$|\bp[il1]x\b',                            'PIX'),
    (r'd[e3][b8][il1]t[o0].{0,8}[a4@].{0,4}v[il1][s5]t[a4]',                     'Débito à Vista'),
    (r'\bdeb[i1l]t[o0]?\s*[a4]?\s*v[i1l]st[a4]\b',                                'Débito à Vista'),
    (r'\bdeb[i1l]t[o0]?\b',                                                         'Débito à Vista'),
    (r'cr[e3]d[i1l]t[o0].{0,8}[a4@].{0,4}v[il1][s5]t[a4]',                       'Crédito à Vista'),
    (r'\bcred[i1l]t[o0]?\s*[a4]?\s*v[i1l]st[a4]\b',                               'Crédito à Vista'),
    (r'\bcred[i1l]t[o0]?\b',                                                        'Crédito à Vista'),
]
