@echo off
echo ============================================
echo  INSTALADOR - Leitor OCR de Notas de Cartao
echo ============================================
echo.

:: Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo Baixe em: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Atualizando pip...
python -m pip install --upgrade pip --quiet

echo [2/4] Instalando dependencias...
pip install easyocr opencv-python Pillow openpyxl numpy pyinstaller --quiet

echo [3/4] Gerando executavel...
pyinstaller --onefile --windowed --name "LeituraNotas" ^
    --add-data "." ^
    --hidden-import "easyocr" ^
    --hidden-import "cv2" ^
    --hidden-import "PIL" ^
    --hidden-import "openpyxl" ^
    app.py

echo [4/4] Concluido!
echo.
echo O executavel esta em: dist\LeituraNotas.exe
echo.
pause
