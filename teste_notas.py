"""
Teste offline: roda o OCR nas imagens de notas e imprime o que foi detectado.
Uso: python teste_notas.py imagem1.png imagem2.png ...
"""
import sys, os, cv2, re
from datetime import date

# Importa as funções do app principal
sys.path.insert(0, os.path.dirname(__file__))
from app import (extrair_texto, extrair_bandeira, extrair_tipo,
                 extrair_valor, extrair_data, fmt_brl, OCR_ENGINE)

VERDE  = '\033[92m'
AMARELO= '\033[93m'
VERMELHO='\033[91m'
RESET  = '\033[0m'
NEGRITO= '\033[1m'

def cor(val, ok, warn=None):
    if val is None:       return f"{VERMELHO}{val}{RESET}"
    if warn and warn(val):return f"{AMARELO}{val}{RESET}"
    return f"{VERDE}{val}{RESET}"

def testar(caminho):
    print(f"\n{NEGRITO}{'─'*55}{RESET}")
    print(f"{NEGRITO}Nota: {os.path.basename(caminho)}{RESET}")

    frame = cv2.imread(caminho)
    if frame is None:
        print(f"  {VERMELHO}Erro: imagem não encontrada{RESET}")
        return

    texto = extrair_texto(frame)
    bandeira = extrair_bandeira(texto)
    tipo     = extrair_tipo(texto)
    valor    = extrair_valor(texto)
    data     = extrair_data(texto)

    # PIX unify
    if bandeira == 'PIX' and tipo is None: tipo = 'PIX'
    if tipo == 'PIX' and bandeira is None: bandeira = 'PIX'

    print(f"  Bandeira : {cor(bandeira, bandeira is not None)}")
    print(f"  Tipo     : {cor(tipo, tipo is not None)}")
    print(f"  Valor    : {cor(fmt_brl(valor) if valor else None, valor is not None)}")
    print(f"  Data     : {cor(data.strftime('%d/%m/%Y') if data else None, data is not None)}")
    print(f"  OCR raw  : {texto[:120].replace(chr(10),' ')!r}")

if __name__ == '__main__':
    print(f"Engine OCR: {NEGRITO}{OCR_ENGINE}{RESET}")
    imagens = sys.argv[1:]
    if not imagens:
        # tenta pegar imagens na mesma pasta
        pasta = os.path.dirname(__file__)
        imagens = [os.path.join(pasta, f)
                   for f in os.listdir(pasta)
                   if f.lower().endswith(('.png','.jpg','.jpeg'))]
    if not imagens:
        print("Uso: python teste_notas.py nota1.png nota2.png ...")
        sys.exit(1)
    for img in sorted(imagens):
        testar(img)
    print(f"\n{NEGRITO}{'─'*55}{RESET}\n")
