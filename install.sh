#!/bin/bash

# BadMapper3 Installation Script

echo "=== BadMapper3 Installation ==="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Uninstalling conflicting opencv packages..."
pip uninstall -y opencv-python opencv-contrib-python 2>/dev/null

echo "Installing dependencies..."
pip install --upgrade pip
pip install PyQt5>=5.15.0
pip install opencv-python-headless>=4.5.0
pip install numpy>=1.20.0

echo ""
echo "=== Installation Complete ==="
echo "To run BadMapper3:"
echo "  source venv/bin/activate"
echo "  python main.py"
