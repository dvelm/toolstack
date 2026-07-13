@echo off
rem ═══════════════════════════════════════════════════════════
rem  PDF Tool Pro — Windows Launcher
rem  Double-click this file to start the modern PDF editing UI
rem  in your default browser.
rem
rem  It will check that Python and required packages are
rem  installed before launching.
rem ═══════════════════════════════════════════════════════════

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PORT=8501"

rem ── Handle --help flag ──
if /I "%~1"=="--help" goto :show_help
if /I "%~1"=="-h" goto :show_help

rem ── Handle --stop flag ──
if /I "%~1"=="--stop" goto :stop_streamlit
if /I "%~1"=="-s" goto :stop_streamlit

cls
echo.
echo ============================================
echo   [PDF] PDF Tool Pro
echo   Modern PDF Editing ^& Compression
echo ============================================
echo.

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
    echo    pip install PyMuPDF streamlit
    echo.
    echo  Or use the provided requirements.txt:
    echo.
    echo    pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

rem ── All good — check for existing instance ──
echo   [OK] All dependencies satisfied!
echo.

netstat -ano | findstr /C:":%PORT% " | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo  [INFO] Port %PORT% is already in use.
    echo  [INFO] Opening browser to existing instance...
    echo.
    echo  Tip: run "run.bat --stop" to stop the existing server.
    echo.
    start "" http://localhost:%PORT%
    echo  Press any key to exit this launcher.
    pause
    exit /b 0
)

rem ── Launch Streamlit ──
echo  ============================================
echo   [LAUNCH] Launching PDF Tool Pro...
echo  ============================================
echo.
echo  Your browser will open shortly.
echo  Close this window or press Ctrl+C to stop the app.
echo.

rem Run Streamlit in foreground — closing the window or Ctrl+C stops it
%PYTHON% -m streamlit run "%SCRIPT_DIR%pdf_ui.py" --server.port %PORT% --server.headless true --browser.gatherUsageStats false

echo.
echo App closed.
pause
exit /b 0

rem ── Stop Streamlit ──
:stop_streamlit
set "FOUND_COUNT=0"
for /F "tokens=5 delims= " %%P in ('netstat -ano ^| findstr /C:":%PORT% " ^| findstr "LISTENING"') do (
    set /A FOUND_COUNT+=1
    echo Stopping Streamlit (PID: %%P)...
    taskkill /PID %%P /F >nul 2>&1
)

if %FOUND_COUNT% gtr 0 (
    echo [OK] Streamlit stopped.
) else (
    echo [INFO] Streamlit is not running on port %PORT%.
)
exit /b 0

rem ── Show help ──
:show_help
echo PDF Tool Pro Launcher
echo.
echo Usage:
echo   run.bat           Start PDF Tool Pro (opens browser)
echo   run.bat --stop    Stop the running server
echo   run.bat --help    Show this help
echo.
echo Operations (available in the web UI):
echo.
echo   Compress        Reduce file size (auto, lossless, smart, aggressive, raster)
echo   Merge           Combine multiple PDFs into one
echo   Split           Extract pages into separate files
echo   Rotate          Rotate all pages (90, 180, or 270 degrees)
echo   Crop            Remove margins from pages
echo   Extract Text    Pull all text from a PDF
echo   Extract Images  Save all embedded images
echo   Select Pages    Extract specific pages (e.g. 1,3,5-8)
echo   Watermark       Add text overlay to every page
echo   Info            View metadata, page count, file details
echo.
echo Notes:
echo   - Close the window or press Ctrl+C to stop
exit /b 0
