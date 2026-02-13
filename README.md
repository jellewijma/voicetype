# VoiceType

Local AI voice dictation for Linux, inspired by Wispr Flow. Uses faster-whisper for fast, accurate transcription.

## Features

- **Fast Transcription**: Uses distil-medium.en model optimized for RTX 3050 8GB
- **Hotkey Activation**: Double-tap Ctrl to start/stop recording
- **Cross-App Support**: Works in any application via xdotool
- **Smart Text Processing**:
  - Removes filler words (um, uh, like, you know)
  - Auto-capitalization and punctuation
  - Personal dictionary for custom words
  - Snippets for text expansion
- **System Tray**: Easy access menu and status indicator

## Requirements

- Arch Linux
- NVIDIA GPU with CUDA support (optional, for faster transcription)
- Python 3.10+

## Installation

```bash
cd voicetype
chmod +x install.sh
./install.sh
```

## Usage

1. Start VoiceType:
   ```bash
   ./src/voicetype.py
   ```
   Or with the venv:
   ```bash
   source venv/bin/activate
   python src/voicetype.py
   ```

2. Double-tap `Ctrl` to start recording
3. Speak your text
4. Double-tap `Ctrl` again to stop and transcribe
5. Text is automatically typed into the active window

## Configuration

Edit `~/.config/voicetype/config.yaml`:

```yaml
# Change hotkey
hotkey:
  key: "ctrl"  # Options: ctrl, alt, shift, or any letter
  double_tap: true

# Change model (for different GPU/memory)
model:
  name: "distil-medium.en"  # Options: tiny.en, small.en, medium.en, distil-medium.en
  device: "cuda"  # Options: cuda, cpu

# Personal dictionary
dictionary:
  "voicetype": "VoiceType"
  "arch": "Arch Linux"

# Snippets
snippets:
  "my email": "your.email@example.com"
```

## Models

For RTX 3050 8GB, recommended models in order of quality/speed:

| Model | VRAM | Speed | Quality |
|-------|------|-------|---------|
| tiny.en | ~1GB | Fastest | Good |
| small.en | ~2GB | Fast | Better |
| **distil-medium.en** | ~3GB | Fast | Best |
| medium.en | ~5GB | Slower | Excellent |

## Autostart

To start VoiceType on login:

```bash
mkdir -p ~/.config/autostart
cp ~/.local/share/applications/voicetype.desktop ~/.config/autostart/
```

## Troubleshooting

### "No audio detected"
- Check your microphone is working: `arecord -l`
- Test recording: `arecord -d 5 test.wav`

### CUDA errors
- Ensure NVIDIA drivers are installed: `nvidia-smi`
- Install CUDA: `sudo pacman -S cuda cudnn`
- Set device to "cpu" in config if needed

### Text not inserting
- Ensure xdotool is installed: `sudo pacman -S xdotool`
- Check active window allows text input

## License

MIT