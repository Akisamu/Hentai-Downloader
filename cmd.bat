@echo off
REM Activate virtual environment
call .venv\Scripts\activate

if %ERRORLEVEL% neq 0 (
    echo Failed to activate virtual environment
    pause
    exit /b
)

echo ========================================
echo  Hentai Downloader
echo ========================================
echo  1. Web UI  (Gradio)
echo  2. Terminal  (main.py)
echo ========================================
set /p MODE="Choose [1/2]: "

if "%MODE%"=="1" (
    echo.
    echo Starting Gradio web UI at http://127.0.0.1:7860
    python app.py
) else (
    echo.
    echo Running terminal version ...
    python main.py
)

pause
