# VoiceType

Local AI voice dictation for Linux, inspired by Wispr Flow. Uses faster-whisper for fast, accurate transcription.

**Modular Architecture**: Refactored into clean, maintainable modules:
- `src/core/`: Core functionality (audio, transcription, text processing, configuration)
- `src/ui/`: User interface (system tray, popups, configuration dialog)
- `src/integration/`: External integrations (Hyprland socket server)
- `src/utils/`: Utilities (error handling, recovery, logging)

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
- **Modular Design**: Clean separation of concerns for easier maintenance
- **Robust Error Handling**: Graceful recovery from audio, model, and configuration errors
- **Hyprland Integration**: Socket-based communication for hotkey handling

## Requirements

- Arch Linux (other distributions may work with manual dependency installation)
- System dependencies (installed automatically by `install.sh`):
  - `python`, `python-pip`, `python-pyaudio`, `portaudio`, `ffmpeg`
  - `xdotool`, `xclip`, `gtk3`, `gobject-introspection`, `libnotify`
- NVIDIA GPU with CUDA support (optional, for faster transcription)
- Python 3.10+

## Installation

### Automated Installation (Arch Linux)

The `install.sh` script handles everything for Arch Linux:

```bash
cd voicetype
chmod +x install.sh
./install.sh
```

This will:
1. Install system dependencies via pacman
2. Set up CUDA support if NVIDIA GPU detected
3. Create Python virtual environment
4. Install Python dependencies from `requirements.txt`
5. Copy configuration to `~/.config/voicetype/config.yaml`
6. Create desktop entry for autostart

### Manual Installation (Other Distributions)

1. Install system dependencies equivalent to those listed in Requirements
2. Create virtual environment and install Python packages:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy configuration manually:
   ```bash
   mkdir -p ~/.config/voicetype
   cp config/config.yaml ~/.config/voicetype/config.yaml
   ```
4. Make the main script executable:
   ```bash
   chmod +x src/voicetype.py
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
- `--debug`: Enable debug logging for troubleshooting

## Configuration

Edit `~/.config/voicetype/config.yaml`:

```yaml
# Model settings
model:
  name: "distil-medium.en"  # Options: tiny.en, small.en, medium.en, distil-medium.en
  device: "cuda"  # Options: cuda, cpu
  compute_type: "float16"  # Options: float16, int8_float16, int8

# Audio settings
audio:
  sample_rate: 16000
  channels: 1
  silence_threshold: 0.01
  silence_duration: 1.5  # seconds before auto-stop

# Text processing
text_processing:
  remove_fillers: true  # Remove um, uh, like, you know
  auto_capitalize: true
  auto_punctuate: true
  trailing_punctuation: true

# Personal dictionary - words to always recognize
dictionary:
  # Example:
  # "voicetype": "VoiceType"
  # "arch": "Arch Linux"

# Snippets - short phrases that expand
snippets:
  # Example:
  # "my email": "your.email@example.com"
  # "my address": "123 Main St, City, State"

# Application-specific settings
# Override default behavior for specific apps
app_overrides: {}
  # Example:
  # "code":  # VSCode
  #   auto_format: false
  # "discord":
  #   remove_fillers: true
```

**Note**: Hotkey configuration is handled via Hyprland window manager bindings. See the [Usage](#usage) section for details.

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

VoiceType includes a comprehensive test suite to verify functionality across the modular architecture:

```bash
# Run all tests
python run_tests.py

# Run specific test suites:
python smoke_test.py                 # Installation and basic functionality
python test_initialization.py        # Model loading and initialization
python test_integration.py           # Component integration tests
python test_real_integration.py      # End-to-end integration with audio and transcription

# Run with options:
python run_tests.py --skip-smoke     # Skip smoke test
python run_tests.py --skip-init      # Skip initialization test
python run_tests.py --skip-all       # Show summary only
```

The tests verify:
- Python dependencies are installed
- Configuration files exist and are valid
- Modular components (audio, transcription, text processing, UI) work correctly
- Error handling and recovery mechanisms
- Socket communication for hotkey handling
- Auto-record flag works correctly
- Hyprland binding is configured (if using Hyprland)

## Development

VoiceType follows a modular architecture and includes comprehensive development guidelines in [`AGENTS.md`](AGENTS.md). Key development commands:

### Environment Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Code Quality
```bash
black src/ tests/                # Format code
isort src/ tests/                # Sort imports
flake8 src/ tests/               # Lint
mypy src/ --ignore-missing-imports  # Type checking
```

### Testing
```bash
pytest                           # Run all tests (if test suite expanded)
python run_tests.py              # Run integration tests
```

### Architecture
- `src/core/`: Core functionality (audio, transcription, text processing, configuration)
- `src/ui/`: User interface components
- `src/integration/`: External integrations
- `src/utils/`: Utilities and error handling

Refer to [`AGENTS.md`](AGENTS.md) for detailed contributor guidelines, git conventions, and code style.

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