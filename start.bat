@echo off
REM Script para iniciar o Agente de Compras no Windows

echo.
echo 🛒 AGENTE DE COMPRAS - Inicialização
echo ====================================
echo.

REM Verificar Python
echo ✓ Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python não encontrado. Instale Python 3.8+
    pause
    exit /b 1
)
python --version

REM Verificar pip
echo ✓ Verificando pip...
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ pip não encontrado
    pause
    exit /b 1
)

REM Instalar/atualizar dependências
echo.
echo 📦 Instalando dependências...
if exist "requirements.txt" (
    pip install -q -r requirements.txt
    echo ✓ Dependências instaladas
) else (
    echo ❌ requirements.txt não encontrado
    pause
    exit /b 1
)

REM Verificar OPENAI_API_KEY
echo.
echo 🔑 Verificando chave OpenAI...
if "%OPENAI_API_KEY%"=="" (
    echo ⚠️  OPENAI_API_KEY não está definida
    echo.
    echo Configure com:
    echo   set OPENAI_API_KEY=sk-...
    echo.
    set /p "choice=Deseja continuar mesmo assim? (s/n): "
    if /i not "%choice%"=="s" (
        exit /b 1
    )
) else (
    echo ✓ OPENAI_API_KEY configurada
)

REM Iniciar servidor
echo.
echo 🚀 Iniciando servidor...
echo    Acesse: http://localhost:8000
echo.
echo Pressione Ctrl+C para parar
echo ====================================
echo.

python server.py

pause
