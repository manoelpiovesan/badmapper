@echo off
REM BadMapper3 Installation Script for Windows

echo === BadMapper3 Installation ===

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Uninstalling conflicting opencv packages...
pip uninstall -y opencv-python opencv-contrib-python

echo Installing dependencies...
pip install --upgrade pip
pip install PyQt5>=5.15.0
pip install opencv-python-headless>=4.5.0
pip install numpy>=1.20.0

echo.
echo === Installation Complete ===
echo To run BadMapper3:
echo   venv\Scripts\activate.bat
echo   python main.py

pause
