# Checagem ponta-a-ponta do OCR: python test_ocr.py
import time
from datetime import date

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ocr_engine import get_reader, processar_frame


def nota(linhas: list[str]) -> np.ndarray:
    """Comprovante sintético no tamanho da ROI da câmera 1280x720."""
    im = Image.new('RGB', (1180, 660), (232, 230, 225))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 30)
    for i, s in enumerate(linhas):
        d.text((300, 60 + i * 70), s, font=f, fill=(40, 40, 40))
    bgr = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
    return cv2.GaussianBlur(bgr, (3, 3), 0)


CASOS = [
    (['CIELO', 'PREPAGO MASTERCARD - DEBITO A VISTA', '25/10/26   14:32',
      'VALOR APROVADO: R$ 1.234,56'],
     ('Mastercard Pré-pago', 'Débito à Vista', 1234.56, date(2026, 10, 25))),
    (['STONE', 'VISA', 'CREDITO A VISTA', '26/10/2026 09:10', 'VALOR: R$ 87,90'],
     ('Visa', 'Crédito à Vista', 87.90, date(2026, 10, 26))),
    (['26/10/2026 11:02:33', 'PAGAMENTO PIX', 'SICOOB', 'PIX R$ 50,00'],
     ('PIX', 'Sicoob', 50.00, date(2026, 10, 26))),
]

if __name__ == '__main__':
    get_reader()
    for linhas, esperado in CASOS:
        t = time.perf_counter()
        r = processar_frame(nota(linhas))
        ms = (time.perf_counter() - t) * 1000
        assert r, linhas
        got = (r['bandeira'], r['tipo'], r['valor'], r['data'])
        assert got == esperado, (got, esperado, r['texto_bruto'])
        print(f'OK {ms:5.0f} ms  {got}')
