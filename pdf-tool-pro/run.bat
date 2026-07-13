@echo off
rem ═══════════════════════════════════════════════════════════
rem  PDF Tool Pro — Windows Launcher
rem  Double-click this file to start the modern PDF editing UI
rem  in your default browser.
rem
rem  It will check that Python and required packages are
rem  installed before launching.
rem ═══════════════════════════════════════════════════════════

title PDF Tool Pro

echo.
echo ============================================
echo   [PDF] PDF Tool Pro
echo   Modern PDF Editing ^& Compression
echo ============================================
echo.

rem ── Get script directory ──
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

rem ── Find Python ──
set "PYTHON="
where python3 >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON=python3"
    goto :found_python
)
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON=python"
    goto :found_python
)

echo.
echo  [ERROR]  Python not found!
echo.
echo  PDF Tool Pro requires Python 3.9 or newer.
echo.
echo  Install it from:
echo    https://www.python.org/downloads/
echo.
echo  Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:found_python
echo   [OK] Python found: %PYTHON%
%PYTHON% --version
echo.

rem ── Check required packages ──
set "ALL_OK=1"

echo  Checking required packages...
echo.

%PYTHON% -c "import fitz" 2>nul
if %errorlevel% neq 0 (
    echo   [MISSING] PyMuPDF (fitz) is NOT installed
    set "ALL_OK=0"
) else (
    echo   [OK] PyMuPDF is installed
)

%PYTHON% -c "import pypdf" 2>nul
if %errorlevel% neq 0 (
    echo   [MISSING] pypdf is NOT installed
    set "ALL_OK=0"
) else (
    echo   [OK] pypdf is installed
)

%PYTHON% -c "import streamlit" 2>nul
if %errorlevel% neq 0 (
    echo   [MISSING] Streamlit is NOT installed
    set "ALL_OK=0"
) else (
    echo   [OK] Streamlit is installed
)

echo.

rem ── Handle missing packages ──
if "%ALL_OK%"=="0" (
    echo ============================================================
    echo   [ERROR]  Missing required Python packages
    echo ============================================================
    echo.
    echo  Please install them by running this command in a terminal:
    echo.
    echo    pip install PyMuPDF pypdf streamlit
    echo.
    echo  Or use the provided requirements.txt:
    echo.
    echo    pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

rem ── All good — launch the app! ──
echo   [OK] All dependencies satisfied!
echo.
echo  ============================================
echo   [LAUNCH] Launching PDF Tool Pro...
echo  ============================================
echo.
echo  Your browser will open shortly.
echo  If it doesn't, check the terminal output for the URL.
echo.
echo  Close this window or press Ctrl+C to stop the app.
echo.

rem Launch Streamlit
%PYTHON% -m streamlit run "%SCRIPT_DIR%pdf_ui.py" --server.headless true

echo.
echo App closed.
pause
