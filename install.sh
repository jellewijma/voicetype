#!/bin/bash
# VoiceType Installation Script for Arch Linux

set -e

echo "=== VoiceType Installation Script ==="

GREEN='\033[0;32m'
NC='\033[0m'

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

if ! command_exists pacman; then
    echo "This script is designed for Arch Linux. Aborting."
    exit 1
fi

echo -e "${GREEN}[1/6] Installing system dependencies...${NC}"
sudo pacman -S --needed --noconfirm \
    python \
    python-pip \
    python-pyaudio \
    portaudio \
    ffmpeg \
    xdotool \
    xclip \
    gtk3 \
    gobject-introspection \
    libnotify

if command_exists nvidia-smi; then
    echo -e "${GREEN}[2/6] NVIDIA GPU detected. Installing CUDA support...${NC}"
    sudo pacman -S --needed --noconfirm cuda cudnn
else
    echo -e "${GREEN}[2/6] No NVIDIA GPU detected. Using CPU mode...${NC}"
    sed -i 's/device: "cuda"/device: "cpu"/' config/config.yaml
fi

echo -e "${GREEN}[3/6] Creating virtual environment...${NC}"
python -m venv venv
source venv/bin/activate

echo -e "${GREEN}[4/6] Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}[5/6] Setting up configuration...${NC}"
mkdir -p ~/.config/voicetype
if [ ! -f ~/.config/voicetype/config.yaml ]; then
    cp config/config.yaml ~/.config/voicetype/config.yaml
    echo "Configuration file created at ~/.config/voicetype/config.yaml"
fi

echo -e "${GREEN}[6/6] Creating desktop entry...${NC}
cat > ~/.local/share/applications/voicetype.desktop << 'EOF'
[Desktop Entry]
Name=VoiceType
Comment=Voice dictation with local AI
Exec=/home/jelle/Dev/sandbox/voicetype/venv/bin/python /home/jelle/Dev/sandbox/voicetype/src/voicetype.py
Icon=audio-input-microphone
Terminal=false
Type=Application
Categories=Utility;AudioVideo;
StartupNotify=true
EOF

chmod +x ~/.local/share/applications/voicetype.desktop

chmod +x src/voicetype.py

echo -e "${GREEN}=== Installation Complete ===${NC}
echo ""
echo "VoiceType has been installed successfully!"
echo ""
echo "Usage:"
echo "  1. Run: ./src/voicetype.py"
echo "  2. Double-tap CTRL to start/stop recording"
echo "  3. Your speech will be transcribed and typed into the active window"
echo ""
echo "Configuration: ~/.config/voicetype/config.yaml"
echo ""
echo "To autostart on login, copy the desktop file:"
echo "  cp ~/.local/share/applications/voicetype.desktop ~/.config/autostart/"