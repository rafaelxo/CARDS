# 📋 Leitor OCR de Notas de Cartão

Aplicação desktop para leitura automatizada de comprovantes de cartão via webcam.

---

## 🚀 Como usar

### Opção A — Rodar direto com Python

```bash
pip install -r requirements.txt
python app.py
```

### Opção B — Gerar o .exe (Windows)

1. Instale o Python 3.10+ em https://python.org
2. Execute o arquivo `instalar_e_compilar.bat` como administrador
3. O executável será gerado em `dist/LeituraNotas.exe`

---

## 🖥️ Funcionalidades

| Função | Descrição |
|---|---|
| 📷 Preview ao vivo | Câmera em tempo real com guia de posicionamento |
| 🔍 OCR automático | Leitura a cada N segundos (configurável) |
| 🏦 Bandeiras | Visa, Master, Elo, Hipercard, Amex, Cabal, Alelo, VR, Ticket, Sodexo e variantes Pré-pago |
| 💳 Tipo | Crédito, Débito, Pré-pago, Contactless |
| 💰 Valor | Extração precisa com regex para formatos brasileiros |
| 📅 Validação de data | Alerta quando a data da nota difere da sessão |
| 📊 Exportação | Planilha .xlsx formatada com totais automáticos |

---

## 📅 Validação de Data

- O usuário seleciona a **data da sessão** (dia que está conferindo)
- O OCR lê a data impressa na nota
- Se as datas **diferirem**, o app pergunta se deseja adicionar mesmo assim
- Notas com data divergente ficam marcadas em **amarelo** na tabela e na planilha

---

## 🏦 Bandeiras reconhecidas

**Visa:** Visa, Visa Electron, Visa Vale, Visa Pré-pago  
**Mastercard:** Mastercard, Master, Maestro, Mastercard Pré-pago  
**Elo:** Elo, Elo Pré-pago  
**Outros:** Hipercard, American Express (Amex), Cabal, Cabal Pré-pago,  
Aura, Diners Club, Alelo, Ticket, Sodexo, VR Benefícios, Sorocred, Beneflex

---

## ⚙️ Requisitos de sistema

- Windows 10/11 (64-bit)
- Python 3.10 ou superior
- Webcam USB ou integrada
- 4GB RAM recomendado (EasyOCR usa ~500MB)
- Conexão com internet apenas na primeira execução (download do modelo OCR)

---

## 🔒 Privacidade e segurança

- **100% local** — nenhum dado sai do computador
- Nenhuma API externa, nenhuma nuvem
- Os dados só existem na sessão e na planilha exportada
- Ideal para dados financeiros sensíveis

---

## 💡 Dicas de uso

1. **Iluminação:** Use boa luz natural ou lâmpada sobre a nota
2. **Distância:** Mantenha a nota a ~20-30cm da câmera
3. **Enquadramento:** Deixe a nota dentro do retângulo guia na tela
4. **Intervalo:** Configure o intervalo de captura conforme a velocidade de leitura
5. **Pré-pago:** O app detecta "pré-pago" no texto e diferencia automaticamente

---

## 🐛 Resolução de problemas

**Câmera não abre:**
- Verifique se outra aplicação está usando a câmera
- Tente reconectar o cabo USB da webcam

**OCR não detecta texto:**
- Melhore a iluminação
- Aproxime mais a nota da câmera
- Aguarde o intervalo completo entre capturas

**Erro ao gerar .exe:**
- Execute o .bat como Administrador
- Verifique se o antivírus não está bloqueando o PyInstaller
