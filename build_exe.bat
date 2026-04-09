@echo off
echo ====================================================
echo Rox-Invoice-App EXE Builder (Windows)
echo ====================================================

REM 1. Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/
    pause
    exit /b
)

REM 2. Create virtual environment if it doesn't exist
if not exist "venv_build" (
    echo [INFO] Creating build virtual environment...
    python -m venv venv_build
)

REM 3. Activate virtual environment and install dependencies
echo [INFO] Installing dependencies...
call venv_build\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

REM 4. Build the EXE
echo [INFO] Building EXE with PyInstaller...
pyinstaller --noconfirm --onefile --windowed --name "Rox-Invoice-App" main.py

echo ====================================================
echo [SUCCESS] Build complete!
echo Your executable is located in the "dist" folder.
echo NOTE: Make sure "config.json" is in the same folder as the EXE.
echo ====================================================

