# VoiceType

Local AI voice dictation for Linux, inspired by Wispr Flow. Uses faster-whisper for fast, accurate transcription.

## Features

- **Fast Transcription**: Uses distil-medium.en model optimized for RTX 3050 8GB
- **Hotkey Activation**: Press SUPER+I to start/stop recording (auto-starts if not running)
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

1. Start VoiceType (daemon mode):
   ```bash
   ./src/voicetype.py
   ```
   Or with the venv:
   ```bash
   source venv/bin/activate
   python src/voicetype.py
   ```

2. Use the hotkey to start/stop recording:
   - Press `SUPER+I` (default) to toggle recording
   - First press starts VoiceType if not running (shows "Initializing..." then "Listening...")
   - Second press stops recording and transcribes
   - Text is automatically typed into the active window

### Shortcut-Triggered Mode (Auto Start)
If you prefer the shortcut to start VoiceType automatically (no need to run manually):

1. Use the wrapper script:
   ```bash
   chmod +x voicetype-toggle.sh
   ./voicetype-toggle.sh
   ```
2. Bind this script to your preferred hotkey:
   ```bash
   # In ~/.config/hypr/hyprland.conf (e.g., SUPER+I):
   bind = $mainMod, I, exec, /path/to/voicetype-toggle.sh
   ```
3. When you press the hotkey:
   - VoiceType starts (if not running) and shows "Initializing..." popup
   - After model loads, automatically starts recording ("Listening...")
   - Press hotkey again to stop recording and transcribe
 
## Command Line Options

- `--auto-record`: Start recording automatically after initialization (shows "Initializing..." popup, then "Listening...")

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

## Testing

VoiceType includes tests to verify the auto-start functionality:

```bash
# Run all tests
python run_tests.py

# Run smoke test only (checks installation)
python smoke_test.py

# Run initialization tests only
python test_initialization.py
```

The tests verify:
- Python dependencies are installed
- Configuration files exist and are valid
- Wrapper script is correctly set up
- Auto-record flag works correctly
- Hyprland binding is configured (if using Hyprland)

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

## Product Readiness & Development

VoiceType is currently a proof-of-concept with core functionality working well. To transform it into a production-ready product, we've created comprehensive improvement plans:

### 📋 [Product Readiness Plan](PRODUCT_READINESS_PLAN.md)
48-week roadmap with 4 quarters of development:
1. **Foundation** (Weeks 1-12): Architecture, error handling, platform support
2. **Quality & UX** (Weeks 13-24): Testing, GUI configuration, first-run wizard  
3. **Features & Polish** (Weeks 25-36): Multi-language, performance optimization
4. **Community & Release** (Weeks 37-48): Community infrastructure, v1.0.0 release

### 🛠️ [Implementation Guide](IMPLEMENTATION_GUIDE.md)
Detailed implementation instructions for 12 improvement areas:
- Platform compatibility & distribution
- Robustness & error handling  
- Security & privacy
- Testing & quality assurance
- Configuration & user experience
- Performance & resource management
- Advanced features (multi-language, etc.)
- Documentation & support
- Code quality & maintainability
- Accessibility & internationalization
- Monitoring & debugging
- Community & distribution

Each area includes problem statements, implementation approaches, code examples, testing strategies, and Definition of Done criteria.

### 🚀 [Getting Started Checklist](GETTING_STARTED_CHECKLIST.md)
Week-by-week checklist for implementing improvements, starting with:
1. Modular architecture refactoring
2. Comprehensive error handling
3. Multi-platform support
4. Basic testing infrastructure
5. GUI configuration

### 🎯 [Summary & Next Steps](SUMMARY_AND_NEXT_STEPS.md)
Prioritized MVP path, success metrics, risk mitigation, and release strategy.

## Contributing

We welcome contributions! Check the implementation guides for well-defined tasks suitable for different skill levels:
- **Beginners**: Documentation, testing, bug fixes
- **Intermediate**: Feature implementation, UI improvements
- **Advanced**: Architecture, performance optimization, platform support

## License
 
 MIT