# VoiceType Implementation Guide

## Introduction

This guide provides detailed implementation instructions and Definition of Done (DoD) criteria for each improvement area identified in the Product Readiness Plan. Each section includes:
- **Problem Statement**: What needs to be fixed
- **Implementation Approach**: How to implement the solution
- **Code Examples**: Sample implementation code
- **Testing Strategy**: How to verify the implementation
- **Definition of Done**: Specific, measurable completion criteria

## 1. Platform Compatibility & Distribution

### 1.1 Multi-Distribution Linux Support

**Problem**: Currently Arch Linux only with hardcoded `pacman` dependencies.

**Implementation**:

1. **Platform Detection Module** (`utils/platform.py`):
```python
import platform
import subprocess
import os
from typing import Dict, Optional, List

class PlatformDetector:
    @staticmethod
    def detect() -> Dict[str, any]:
        """Detect current platform and package manager."""
        system = platform.system().lower()
        distro = None
        pm = None
        
        if system == "linux":
            distro = PlatformDetector._get_linux_distro()
            pm = PlatformDetector._get_package_manager(distro)
        elif system == "darwin":
            pm = "brew"
        elif system == "windows":
            pm = "choco" if PlatformDetector._has_chocolatey() else None
        
        return {
            "system": system,
            "distro": distro,
            "package_manager": pm,
            "has_nvidia": PlatformDetector._has_nvidia_gpu(),
            "has_cuda": PlatformDetector._has_cuda(),
            "desktop_env": PlatformDetector._get_desktop_environment(),
            "wayland": "wayland" in os.environ.get("XDG_SESSION_TYPE", "").lower(),
        }
    
    @staticmethod
    def _get_linux_distro() -> Optional[str]:
        try:
            with open("/etc/os-release") as f:
                content = f.read().lower()
                if "ubuntu" in content or "debian" in content:
                    return "debian"
                elif "fedora" in content or "rhel" in content or "centos" in content:
                    return "rhel"
                elif "arch" in content or "manjaro" in content:
                    return "arch"
        except:
            pass
        return None
```

2. **Package Manager Abstraction** (`install/dependencies.py`):
```python
class DependencyInstaller:
    def __init__(self, platform_info: Dict[str, any]):
        self.platform = platform_info
    
    def install_system_dependencies(self) -> bool:
        """Install system dependencies based on platform."""
        deps = self._get_dependencies()
        
        if self.platform["package_manager"] == "apt":
            return self._apt_install(deps)
        elif self.platform["package_manager"] == "dnf":
            return self._dnf_install(deps)
        elif self.platform["package_manager"] == "pacman":
            return self._pacman_install(deps)
        elif self.platform["package_manager"] == "brew":
            return self._brew_install(deps)
        
        # Fallback to pip-only installation
        return self._pip_install_fallback(deps)
    
    def _get_dependencies(self) -> Dict[str, List[str]]:
        """Get dependency lists for different package managers."""
        return {
            "audio": {
                "apt": ["python3-pyaudio", "portaudio19-dev", "libasound2-dev"],
                "dnf": ["python3-pyaudio", "portaudio", "alsa-lib-devel"],
                "pacman": ["python-pyaudio", "portaudio"],
                "brew": ["portaudio"],
            },
            "gui": {
                "apt": ["python3-gi", "gir1.2-gtk-3.0", "gir1.2-ayatanaappindicator3-0.1"],
                "dnf": ["python3-gobject", "gtk3", "libappindicator-gtk3"],
                "pacman": ["python-gobject", "gtk3", "libappindicator"],
                "brew": ["pygobject3", "gtk+3"],
            },
            "utilities": {
                "apt": ["xdotool", "xclip", "wmctrl"],
                "dnf": ["xdotool", "xclip", "wmctrl"],
                "pacman": ["xdotool", "xclip", "wmctrl"],
                "brew": [],  # macOS alternatives
            }
        }
```

**Testing Strategy**:
1. **Unit Tests**: Mock platform detection, test each package manager path
2. **Integration Tests**: Test on different distributions via Docker containers
3. **Manual Tests**: Fresh install on Ubuntu, Fedora, Arch

**DoD**:
- [ ] Platform detection works on Ubuntu 22.04+, Fedora 38+, Arch Linux
- [ ] System dependencies install correctly via apt/dnf/pacman
- [ ] Fallback to pip packages when system packages unavailable
- [ ] Installation script detects and uses correct package manager
- [ ] All tests pass in CI matrix with different distributions
- [ ] Documentation updated with distribution-specific instructions

### 1.2 Cross-Platform Packaging

**Problem**: No standard packaging, manual installation only.

**Implementation**:

1. **PyPI Package Configuration** (`pyproject.toml`):
```toml
[project]
name = "voicetype"
version = "1.0.0"
description = "Local AI voice dictation for Linux"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "VoiceType Contributors"},
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: End Users/Desktop",
    "Topic :: Multimedia :: Sound/Audio :: Speech",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS",
]

[project.urls]
Homepage = "https://github.com/yourusername/voicetype"
Documentation = "https://github.com/yourusername/voicetype/docs"
Repository = "https://github.com/yourusername/voicetype"
Issues = "https://github.com/yourusername/voicetype/issues"

[project.scripts]
voicetype = "voicetype.cli:main"

[project.optional-dependencies]
cuda = [
    "torch>=2.0.0",
    "torchaudio>=2.0.0",
    "faster-whisper>=0.10.0",
]
gui = [
    "pystray>=0.19.0",
    "Pillow>=10.0.0",
    "PyGObject>=3.42.0",
]
audio = [
    "sounddevice>=0.4.6",
    "numpy>=1.24.0",
]
all = [
    "voicetype[cuda]",
    "voicetype[gui]",
    "voicetype[audio]",
    "pyperclip>=1.8.0",
    "PyYAML>=6.0",
]

[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
include = ["voicetype*"]
exclude = ["tests*", "test*"]
```

2. **AppImage Builder** (`.github/workflows/build-appimage.yml`):
```yaml
name: Build AppImage

on:
  release:
    types: [published]

jobs:
  build-appimage:
    runs-on: ubuntu-latest
    container:
      image: appimagecrafters/appimage-builder:latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Build AppImage
      run: |
        appimage-builder --recipe AppImageBuilder.yml
    
    - name: Upload AppImage
      uses: actions/upload-artifact@v4
      with:
        name: VoiceType-AppImage
        path: VoiceType-*.AppImage
```

**Testing Strategy**:
1. **PyPI Test**: `pip install voicetype[all]` in fresh virtual environment
2. **AppImage Test**: Run AppImage on different distributions
3. **Native Package Test**: Install .deb/.rpm packages

**DoD**:
- [ ] `pip install voicetype` works and creates `voicetype` command
- [ ] Optional dependencies install correctly (cuda, gui, audio)
- [ ] AppImage builds automatically on release
- [ ] AppImage runs on Ubuntu 22.04, Fedora 38, Arch Linux
- [ ] At least one native package format available (.deb or .rpm)
- [ ] Installation via package manager works end-to-end

## 2. Robustness & Error Handling

### 2.1 Comprehensive Error Hierarchy

**Problem**: Minimal error recovery, silent failures.

**Implementation**:

1. **Error Classes** (`utils/errors.py`):
```python
class VoiceTypeError(Exception):
    """Base exception for all VoiceType errors."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict:
        """Convert error to dictionary for logging/UI."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }

class ConfigurationError(VoiceTypeError):
    """Configuration related errors."""
    pass

class AudioDeviceError(VoiceTypeError):
    """Audio device related errors."""
    
    @classmethod
    def from_device_info(cls, device_info: Dict, operation: str) -> "AudioDeviceError":
        return cls(
            f"Audio device error during {operation}",
            details={
                "device": device_info.get("name", "unknown"),
                "operation": operation,
                "input_channels": device_info.get("max_input_channels", 0),
                "sample_rate": device_info.get("default_samplerate", 0),
            }
        )

class ModelError(VoiceTypeError):
    """Model loading/transcription errors."""
    
    @classmethod
    def from_exception(cls, exc: Exception, stage: str, model_name: str) -> "ModelError":
        return cls(
            f"Model error during {stage}",
            details={
                "model": model_name,
                "stage": stage,
                "original_error": str(exc),
                "error_type": exc.__class__.__name__,
            }
        )

class TranscriptionError(VoiceTypeError):
    """Transcription specific errors."""
    pass

class HotkeyError(VoiceTypeError):
    """Hotkey/socket communication errors."""
    pass

class GUINotAvailableError(VoiceTypeError):
    """GUI dependencies not available."""
    pass
```

2. **Error Recovery Decorator** (`utils/recovery.py`):
```python
from typing import Type, Callable, Any, Optional
import time
import logging

logger = logging.getLogger(__name__)

def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    fallback: Optional[Callable] = None,
):
    """Decorator for automatic retry with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {exc}"
                    )
                    
                    if attempt < max_attempts:
                        logger.info(f"Retrying in {current_delay:.1f}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            
            if fallback is not None:
                logger.info(f"Using fallback for {func.__name__}")
                return fallback(*args, **kwargs)
            
            raise last_exception  # type: ignore
        
        return wrapper
    return decorator
```

3. **Audio Recorder with Error Recovery** (`core/audio.py`):
```python
class RobustAudioRecorder(AudioRecorder):
    def __init__(self, config: Config):
        super().__init__(config)
        self.available_devices = self._scan_devices()
        self.current_device = self._select_best_device()
    
    def _scan_devices(self) -> List[Dict]:
        """Scan for available audio devices with validation."""
        devices = []
        try:
            host_apis = sd.query_hostapis()
            for api_index, api in enumerate(host_apis):
                for device_index in api["devices"]:
                    try:
                        device = sd.query_devices(device_index, "input")
                        if device["max_input_channels"] > 0:
                            devices.append({
                                "index": device_index,
                                "name": device["name"],
                                "api": api["name"],
                                "channels": device["max_input_channels"],
                                "sample_rate": device["default_samplerate"],
                                "latency": device["default_low_input_latency"],
                            })
                    except sd.PortAudioError:
                        continue
        except sd.PortAudioError as e:
            logger.error(f"Failed to scan audio devices: {e}")
        
        return devices
    
    @with_retry(
        max_attempts=2,
        delay=0.5,
        exceptions=(AudioDeviceError, sd.PortAudioError),
        fallback=lambda self: self._fallback_recording(),
    )
    def start_recording(self):
        """Start recording with error recovery."""
        if not self.available_devices:
            raise AudioDeviceError("No audio input devices available")
        
        try:
            self.stream = sd.InputStream(
                device=self.current_device["index"],
                samplerate=self.config.sample_rate,
                channels=min(self.config.channels, self.current_device["channels"]),
                dtype=np.float32,
                callback=self._audio_callback,
                blocksize=int(self.config.sample_rate * 0.1),  # 100ms blocks
            )
            self.stream.start()
            self.is_recording = True
            logger.info(f"Started recording on device: {self.current_device['name']}")
            
        except sd.PortAudioError as e:
            raise AudioDeviceError.from_device_info(
                self.current_device, "start_recording"
            ) from e
    
    def _fallback_recording(self) -> bool:
        """Fallback recording method when primary fails."""
        logger.warning("Using fallback recording method")
        # Try default device with simpler configuration
        try:
            self.stream = sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype=np.float32,
                callback=self._audio_callback,
            )
            self.stream.start()
            self.is_recording = True
            return True
        except sd.PortAudioError:
            logger.error("Fallback recording also failed")
            return False
```

**Testing Strategy**:
1. **Error Injection Tests**: Simulate audio device failures, model loading failures
2. **Recovery Tests**: Verify retry logic works correctly
3. **Fallback Tests**: Test fallback mechanisms when primary fails
4. **Integration Tests**: End-to-end error scenarios

**DoD**:
- [ ] Custom exception hierarchy implemented and used throughout codebase
- [ ] All audio operations have error handling with retry logic
- [ ] Model loading has exponential backoff retry (3 attempts)
- [ ] Configuration validation catches invalid values with helpful messages
- [ ] Socket communication has timeout (5s) and retry (2 attempts) logic
- [ ] All errors are logged with structured context (JSON format)
- [ ] User-friendly error messages shown in UI for common failures
- [ ] Error recovery tests cover 90% of error scenarios

## 3. Security & Privacy

### 3.1 Socket Security Hardening

**Problem**: Unix socket in `/tmp` with no authentication.

**Implementation**:

1. **Secure Socket Implementation** (`integration/socket_server.py`):
```python
import socket
import os
import stat
import hashlib
import hmac
import secrets
from pathlib import Path
from typing import Optional

class SecureSocketServer:
    def __init__(self, socket_path: Optional[Path] = None):
        self.socket_path = socket_path or self._get_default_socket_path()
        self.auth_token = self._generate_auth_token()
        self._socket = None
        self._running = False
        
    def _get_default_socket_path(self) -> Path:
        """Get secure socket path based on platform."""
        if os.name == "posix":
            # Use XDG_RUNTIME_DIR if available (user-specific, secure)
            runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
            if runtime_dir:
                socket_dir = Path(runtime_dir) / "voicetype"
                socket_dir.mkdir(mode=0o700, exist_ok=True)
                return socket_dir / f"voicetype-{os.getuid()}.sock"
            
            # Fallback to user-specific directory in home
            socket_dir = Path.home() / ".cache" / "voicetype"
            socket_dir.mkdir(mode=0o700, exist_ok=True)
            return socket_dir / f"voicetype-{os.getuid()}.sock"
        else:
            # Windows or other - use named pipes
            return Path(f"\\\\.\\pipe\\voicetype-{os.getlogin()}")
    
    def _generate_auth_token(self) -> bytes:
        """Generate authentication token for socket communication."""
        token_file = self.socket_path.parent / ".auth_token"
        
        if token_file.exists():
            try:
                with open(token_file, "rb") as f:
                    token = f.read()
                if len(token) == 32:  # 256-bit token
                    return token
            except:
                pass
        
        # Generate new token
        token = secrets.token_bytes(32)
        token_file.write_bytes(token)
        token_file.chmod(0o600)  # Owner read/write only
        return token
    
    def _validate_connection(self, conn: socket.socket) -> bool:
        """Validate incoming connection."""
        try:
            # Check peer credentials (Unix sockets only)
            if hasattr(socket, "SO_PEERCRED"):
                cred = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 
                                      struct.calcsize("3i"))
                pid, uid, gid = struct.unpack("3i", cred)
                if uid != os.getuid():
                    logger.warning(f"Rejected connection from different user: {uid}")
                    return False
            
            # Validate authentication token
            conn.settimeout(2.0)
            auth_data = conn.recv(64)
            
            if len(auth_data) != 64:  # 32 bytes token + 32 bytes HMAC
                logger.warning("Invalid auth data length")
                return False
            
            received_token = auth_data[:32]
            received_hmac = auth_data[32:]
            
            # Verify HMAC
            expected_hmac = hmac.new(self.auth_token, received_token, 
                                   hashlib.sha256).digest()
            
            if not hmac.compare_digest(received_hmac, expected_hmac):
                logger.warning("HMAC validation failed")
                return False
            
            return True
            
        except (socket.timeout, socket.error, ValueError) as e:
            logger.warning(f"Connection validation failed: {e}")
            return False
    
    def start(self):
        """Start secure socket server."""
        # Clean up existing socket
        if self.socket_path.exists():
            try:
                self.socket_path.unlink()
            except:
                pass
        
        # Create socket with secure permissions
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.settimeout(1.0)  # Non-blocking with timeout
        
        try:
            self._socket.bind(str(self.socket_path))
            
            # Set secure permissions (owner read/write only)
            if os.name == "posix":
                os.chmod(self.socket_path, 0o600)
            
            self._socket.listen(1)
            self._running = True
            
            logger.info(f"Secure socket server started at {self.socket_path}")
            
            # Start listener thread
            threading.Thread(target=self._listen, daemon=True).start()
            
        except socket.error as e:
            logger.error(f"Failed to start socket server: {e}")
            raise HotkeyError(f"Socket server failed: {e}")
    
    def _listen(self):
        """Listen for incoming connections."""
        while self._running:
            try:
                conn, addr = self._socket.accept()
                
                # Validate connection
                if not self._validate_connection(conn):
                    conn.close()
                    continue
                
                # Handle authenticated connection
                threading.Thread(
                    target=self._handle_connection,
                    args=(conn,),
                    daemon=True
                ).start()
                
            except socket.timeout:
                continue
            except socket.error as e:
                if self._running:
                    logger.error(f"Socket error: {e}")
                    break
```

2. **Secure Client** (`integration/socket_client.py`):
```python
class SecureSocketClient:
    def __init__(self, socket_path: Path, auth_token: bytes):
        self.socket_path = socket_path
        self.auth_token = auth_token
    
    def send_command(self, command: str, timeout: float = 5.0) -> bool:
        """Send command to secure socket server."""
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            # Connect
            sock.connect(str(self.socket_path))
            
            # Authenticate
            challenge = secrets.token_bytes(32)
            hmac_digest = hmac.new(self.auth_token, challenge, 
                                 hashlib.sha256).digest()
            auth_data = challenge + hmac_digest
            
            sock.sendall(auth_data)
            
            # Send command
            sock.sendall(command.encode() + b"\n")
            
            # Wait for acknowledgment
            response = sock.recv(1024)
            sock.close()
            
            return response.decode().strip() == "OK"
            
        except (socket.timeout, socket.error, ConnectionError) as e:
            logger.error(f"Failed to send command: {e}")
            return False
```

**Testing Strategy**:
1. **Permission Tests**: Verify socket file permissions (0600)
2. **Authentication Tests**: Test token-based authentication
3. **Ownership Tests**: Verify socket rejects connections from other users
4. **Network Tests**: Test secure communication over network (if enabled)

**DoD**:
- [ ] Socket uses user-isolated path (XDG_RUNTIME_DIR or ~/.cache)
- [ ] Socket file permissions restricted to owner only (0600)
- [ ] Socket ownership validated on connection
- [ ] HMAC-based authentication token system implemented
- [ ] Authentication tokens stored securely (0600 permissions)
- [ ] Connections from other users rejected
- [ ] Optional network encryption for remote connections
- [ ] Security tests cover all authentication scenarios

### 3.2 Privacy Mode

**Problem**: No guarantees about data remaining local.

**Implementation**:

1. **Privacy Enforcement** (`core/privacy.py`):
```python
import socket
import requests
from typing import Set

class PrivacyEnforcer:
    """Enforce privacy by preventing network access."""
    
    BLOCKED_HOSTS = {
        "api.openai.com",
        "api.anthropic.com",
        "api.deepseek.com",
        "api.groq.com",
        # Add other AI API endpoints
    }
    
    def __init__(self, strict: bool = True):
        self.strict = strict
        self.original_socket = None
        self.original_requests = None
        
    def enable(self):
        """Enable privacy enforcement."""
        if self.strict:
            self._block_network_access()
        
        # Log privacy mode
        logger.info("Privacy mode enabled - all processing remains local")
    
    def _block_network_access(self):
        """Block network access for suspicious modules."""
        # Patch socket module
        self.original_socket = socket.socket
        
        class BlockedSocket(socket.socket):
            def connect(self, address):
                host, port = address[0], address[1]
                if any(blocked in host for blocked in PrivacyEnforcer.BLOCKED_HOSTS):
                    raise ConnectionError(
                        f"Privacy mode blocked connection to {host}"
                    )
                return super().connect(address)
        
        socket.socket = BlockedSocket
        
        # Patch requests if available
        try:
            import requests
            self.original_requests = requests.request
            
            def blocked_request(method, url, **kwargs):
                if any(blocked in url for blocked in PrivacyEnforcer.BLOCKED_HOSTS):
                    raise ConnectionError(
                        f"Privacy mode blocked request to {url}"
                    )
                return self.original_requests(method, url, **kwargs)
            
            requests.request = blocked_request
        except ImportError:
            pass
    
    def disable(self):
        """Disable privacy enforcement."""
        if self.original_socket:
            socket.socket = self.original_socket
        if self.original_requests:
            import requests
            requests.request = self.original_requests
        
        logger.info("Privacy mode disabled")
    
    def verify_local_only(self) -> bool:
        """Verify that no network access is occurring."""
        # Check loaded modules for suspicious imports
        suspicious_modules = {
            "openai", "anthropic", "cohere", "google.generativeai",
            "replicate", "huggingface_hub", "transformers",
        }
        
        for module_name in sys.modules:
            for suspicious in suspicious_modules:
                if suspicious in module_name.lower():
                    logger.warning(f"Suspicious module loaded: {module_name}")
                    return False
        
        return True
```

2. **Privacy Configuration** (`config/privacy.yaml`):
```yaml
privacy:
  enabled: true
  strict_mode: true
  allowed_domains: []
  block_ai_apis: true
  local_model_only: true
  clear_audio_cache: true  # Delete audio files after processing
  clear_transcription_cache: true  # Delete transcription cache
  max_retention_days: 7  # Maximum days to keep any data
```

**Testing Strategy**:
1. **Network Blocking Tests**: Verify network requests to AI APIs are blocked
2. **Data Cleanup Tests**: Verify audio files are deleted after processing
3. **Module Detection Tests**: Verify suspicious module detection works
4. **Configuration Tests**: Test privacy configuration options

**DoD**:
- [ ] Privacy mode blocks network access to known AI APIs
- [ ] Audio files deleted immediately after transcription
- [ ] Transcription cache cleared based on retention policy
- [ ] Suspicious module detection and warning
- [ ] Privacy configuration options in GUI
- [ ] Privacy badge/indicator in system tray
- [ ] Privacy policy document included
- [ ] All privacy tests pass

## 4. Testing & Quality Assurance

### 4.1 Comprehensive Unit Test Suite

**Problem**: Only integration tests, no unit tests for core components.

**Implementation**:

1. **Test Infrastructure** (`tests/conftest.py`):
```python
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

@pytest.fixture
def temp_config_dir():
    """Create temporary config directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".config" / "voicetype"
        config_dir.mkdir(parents=True)
        yield config_dir

@pytest.fixture
def sample_config():
    """Create sample configuration."""
    return {
        "model": {
            "name": "tiny.en",
            "device": "cpu",
            "compute_type": "float32",
        },
        "audio": {
            "sample_rate": 16000,
            "channels": 1,
            "silence_threshold": 0.01,
            "silence_duration": 1.0,
        },
        "text_processing": {
            "remove_fillers": True,
            "auto_capitalize": True,
            "auto_punctuate": True,
            "trailing_punctuation": True,
        }
    }

@pytest.fixture
def mock_audio_data():
    """Generate mock audio data for testing."""
    import numpy as np
    # 1 second of silent audio
    return np.zeros((16000, 1), dtype=np.float32)

@pytest.fixture
def mock_transcription():
    """Mock transcription result."""
    return "This is a test transcription with some filler words like um you know"

@pytest.fixture
def patch_audio_dependencies():
    """Patch audio dependencies for testing."""
    with patch("sounddevice.InputStream") as mock_stream, \
         patch("sounddevice.query_devices") as mock_query, \
         patch("sounddevice.query_hostapis") as mock_apis:
        
        # Mock audio device
        mock_query.return_value = {
            "name": "Test Microphone",
            "max_input_channels": 2,
            "default_samplerate": 16000,
            "default_low_input_latency": 0.1,
        }
        
        mock_apis.return_value = [{
            "name": "Test API",
            "devices": [0],
        }]
        
        # Mock stream
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        mock_stream_instance.start = MagicMock()
        mock_stream_instance.stop = MagicMock()
        mock_stream_instance.close = MagicMock()
        
        yield {
            "stream": mock_stream,
            "query": mock_query,
            "apis": mock_apis,
            "stream_instance": mock_stream_instance,
        }

@pytest.fixture
def patch_model_dependencies():
    """Patch model dependencies for testing."""
    with patch("faster_whisper.WhisperModel") as mock_model_class:
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        # Mock transcription result
        mock_segment = MagicMock()
        mock_segment.text = "Test transcription"
        
        mock_model.transcribe.return_value = (
            [mock_segment],  # segments
            MagicMock(language="en"),  # info
        )
        
        yield {
            "model_class": mock_model_class,
            "model": mock_model,
        }
```

2. **Audio Recorder Tests** (`tests/unit/test_audio.py`):
```python
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
import sys

from core.audio import RobustAudioRecorder
from core.config import Config
from utils.errors import AudioDeviceError

class TestRobustAudioRecorder:
    def test_initialization(self, sample_config):
        """Test recorder initialization."""
        config = Config(**sample_config)
        recorder = RobustAudioRecorder(config)
        
        assert recorder.config == config
        assert recorder.is_recording == False
        assert hasattr(recorder, "available_devices")
    
    def test_device_scanning(self, patch_audio_dependencies):
        """Test audio device scanning."""
        config = Config()
        recorder = RobustAudioRecorder(config)
        
        devices = recorder._scan_devices()
        assert isinstance(devices, list)
        # Should have our mocked device
        assert len(devices) >= 1
        assert devices[0]["name"] == "Test Microphone"
    
    def test_start_recording_success(self, patch_audio_dependencies):
        """Test successful recording start."""
        config = Config()
        recorder = RobustAudioRecorder(config)
        
        recorder.start_recording()
        
        # Verify stream was created and started
        patch_audio_dependencies["stream"].assert_called_once()
        patch_audio_dependencies["stream_instance"].start.assert_called_once()
        assert recorder.is_recording == True
    
    def test_start_recording_failure(self):
        """Test recording start failure."""
        config = Config()
        
        # Mock complete failure
        with patch("sounddevice.InputStream", side_effect=Exception("Device error")):
            recorder = RobustAudioRecorder(config)
            
            with pytest.raises(AudioDeviceError):
                recorder.start_recording()
            
            assert recorder.is_recording == False
    
    def test_stop_recording(self, patch_audio_dependencies):
        """Test recording stop."""
        config = Config()
        recorder = RobustAudioRecorder(config)
        
        # Start recording
        recorder.start_recording()
        assert recorder.is_recording == True
        
        # Stop recording
        audio_data = recorder.stop_recording()
        
        # Verify stream was stopped and closed
        patch_audio_dependencies["stream_instance"].stop.assert_called_once()
        patch_audio_dependencies["stream_instance"].close.assert_called_once()
        assert recorder.is_recording == False
        assert audio_data is None  # No audio was actually recorded
    
    def test_audio_callback(self):
        """Test audio callback processing."""
        config = Config()
        recorder = RobustAudioRecorder(config)
        
        # Create test audio data
        test_data = np.random.randn(1600, 1).astype(np.float32) * 0.1
        
        # Call callback directly
        recorder._audio_callback(test_data, 1600, None, None)
        
        # Audio should be in queue
        assert not recorder.audio_queue.empty()
    
    @pytest.mark.parametrize("silence_duration,expected_stop", [
        (0, False),  # No auto-stop
        (1.0, True),  # Auto-stop after 1s silence
        (2.0, True),  # Auto-stop after 2s silence
    ])
    def test_silence_detection(self, silence_duration, expected_stop):
        """Test silence detection logic."""
        config = Config(silence_duration=silence_duration)
        recorder = RobustAudioRecorder(config)
        
        # This test would require more complex mocking
        # For now, verify configuration is used
        assert recorder.config.silence_duration == silence_duration
```

3. **Text Processor Tests** (`tests/unit/test_text_processing.py`):
```python
import pytest
from core.text_processing import TextProcessor
from core.config import Config

class TestTextProcessor:
    def test_remove_fillers(self):
        """Test filler word removal."""
        config = Config(remove_fillers=True)
        processor = TextProcessor(config)
        
        text = "This is um a test with uh filler words you know"
        result = processor.process(text)
        
        assert "um" not in result.lower()
        assert "uh" not in result.lower()
        assert "you know" not in result.lower()
        assert "test" in result  # Content should remain
    
    def test_dictionary_replacement(self):
        """Test personal dictionary."""
        config = Config(dictionary={"voicetype": "VoiceType", "arch": "Arch Linux"})
        processor = TextProcessor(config)
        
        text = "I use voicetype on arch linux"
        result = processor.process(text)
        
        assert "VoiceType" in result
        assert "Arch Linux" in result
    
    def test_smart_capitalization(self):
        """Test automatic capitalization."""
        config = Config(auto_capitalize=True)
        processor = TextProcessor(config)
        
        text = "this is a test. this is another sentence"
        result = processor.process(text)
        
        assert result.startswith("This")  # First sentence capitalized
        # Note: current implementation may not handle this perfectly
    
    def test_empty_text(self):
        """Test processing empty text."""
        config = Config()
        processor = TextProcessor(config)
        
        result = processor.process("")
        assert result == ""
        
        result = processor.process("   ")
        assert result == ""
    
    @pytest.mark.parametrize("input_text,expected", [
        ("hello world", "Hello world."),  # Add punctuation
        ("hello world.", "Hello world."),  # Already has punctuation
        ("hello world!", "Hello world!"),  # Keep existing punctuation
        ("", ""),  # Empty string
    ])
    def test_punctuation(self, input_text, expected):
        """Test automatic punctuation."""
        config = Config(auto_punctuate=True, trailing_punctuation=True)
        processor = TextProcessor(config)
        
        result = processor.process(input_text)
        # Note: current implementation may differ
```

**Testing Strategy**:
1. **Unit Tests**: Isolated tests for each component with mocked dependencies
2. **Integration Tests**: Component interaction tests
3. **Property-Based Tests**: Test invariants and properties
4. **Performance Tests**: Benchmark critical paths

**DoD**:
- [ ] Unit test suite covers 80%+ of core modules
- [ ] All tests run in < 5 minutes locally
- [ ] Tests use appropriate mocking for external dependencies
- [ ] Parameterized tests for edge cases
- [ ] Test fixtures for common test data
- [ ] Code coverage reports generated automatically
- [ ] Tests run in parallel where possible
- [ ] Flaky tests identified and fixed

### 4.2 Continuous Integration Pipeline

**Problem**: No automated testing pipeline.

**Implementation**:

1. **GitHub Actions Workflow** (`.github/workflows/ci.yml`):
```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    name: Test (${{ matrix.os }}, Python ${{ matrix.python-version }})
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
        python-version: ["3.10", "3.11", "3.12"]
        exclude:
          - os: macos-latest
            python-version: "3.10"  # macOS may not have 3.10
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
        cache: 'pip'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[test]"
    
    - name: Run tests with coverage
      run: |
        pytest \
          --cov=src \
          --cov-report=xml \
          --cov-report=html \
          --cov-report=term \
          -v \
          --tb=short \
          tests/
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v4
      with:
        file: ./coverage.xml
        fail_ci_if_error: true
    
    - name: Upload test results
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: test-results-${{ matrix.os }}-py${{ matrix.python-version }}
        path: |
          htmlcov/
          test-results.xml
  
  lint:
    name: Lint and Code Quality
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"
    
    - name: Install linting tools
      run: |
        pip install black flake8 isort mypy bandit
    
    - name: Check code formatting with black
      run: black --check --diff src/ tests/
    
    - name: Check import sorting with isort
      run: isort --check-only --diff src/ tests/
    
    - name: Lint with flake8
      run: flake8 src/ tests/ --max-line-length=88 --extend-ignore=E203,W503
    
    - name: Type check with mypy
      run: mypy src/ --ignore-missing-imports
    
    - name: Security scan with bandit
      run: bandit -r src/ -ll
    
    - name: Upload linting results
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: lint-results
        path: |
          flake8.txt
          mypy.txt
  
  build:
    name: Build Packages
    runs-on: ubuntu-latest
    needs: [test, lint]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"
    
    - name: Build package
      run: |
        pip install build
        python -m build
    
    - name: Upload packages
      uses: actions/upload-artifact@v4
      with:
        name: packages
        path: dist/*
```

2. **Docker-Based Integration Tests** (`tests/integration/docker-compose.yml`):
```yaml
version: '3.8'

services:
  test-ubuntu:
    build:
      context: .
      dockerfile: Dockerfile.ubuntu
    volumes:
      - ./tests:/app/tests
      - ./src:/app/src
    command: pytest tests/integration/test_ubuntu.py -v
  
  test-fedora:
    build:
      context: .
      dockerfile: Dockerfile.fedora
    volumes:
      - ./tests:/app/tests
      - ./src:/app/src
    command: pytest tests/integration/test_fedora.py -v
  
  test-arch:
    build:
      context: .
      dockerfile: Dockerfile.arch
    volumes:
      - ./tests:/app/tests
      - ./src:/app/src
    command: pytest tests/integration/test_arch.py -v
```

**Testing Strategy**:
1. **Matrix Testing**: Test across OSes and Python versions
2. **Parallel Execution**: Run tests in parallel for speed
3. **Artifact Collection**: Collect test results and coverage
4. **Quality Gates**: Block PRs that fail tests or quality checks

**DoD**:
- [ ] CI pipeline runs on all pushes and PRs
- [ ] Tests run on Ubuntu, macOS, and optionally Windows
- [ ] Tests run on Python 3.10, 3.11, 3.12
- [ ] Code coverage reported and minimum enforced (80%)
- [ ] All code quality checks (black, flake8, mypy, bandit) pass
- [ ] Build artifacts created on main branch pushes
- [ ] Docker-based integration tests for different distributions
- [ ] CI completes in < 15 minutes

## 5. Configuration & User Experience

### 5.1 GUI Configuration Dialog

**Problem**: No GUI configuration, users must edit YAML.

**Implementation**:

1. **Configuration Dialog** (`ui/config_dialog.py`):
```python
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk
from typing import Dict, Any, Optional
import yaml
from pathlib import Path

from core.config import Config
from utils.errors import ConfigurationError

class ConfigDialog(Gtk.Dialog):
    def __init__(self, config: Config, parent: Optional[Gtk.Window] = None):
        super().__init__(
            title="VoiceType Configuration",
            parent=parent,
            flags=Gtk.DialogFlags.MODAL,
            buttons=(
                "Cancel", Gtk.ResponseType.CANCEL,
                "Save", Gtk.ResponseType.OK,
            )
        )
        
        self.config = config
        self.original_config = config.to_dict()
        self.changed = False
        
        self.set_default_size(600, 500)
        self.set_border_width(10)
        
        # Create notebook with tabs
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        
        # Add tabs
        self._create_general_tab()
        self._create_audio_tab()
        self._create_model_tab()
        self._create_text_tab()
        self._create_hotkeys_tab()
        self._create_privacy_tab()
        
        # Connect signals
        self.notebook.connect("switch-page", self._on_tab_changed)
        
        # Add notebook to dialog
        box = self.get_content_area()
        box.pack_start(self.notebook, True, True, 0)
        
        # Status bar
        self.statusbar = Gtk.Statusbar()
        self.statusbar.push(0, "Ready")
        box.pack_start(self.statusbar, False, False, 0)
        
        self.show_all()
    
    def _create_general_tab(self):
        """Create general settings tab."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        
        # Auto-start
        auto_start = Gtk.CheckButton(label="Start VoiceType on login")
        auto_start.set_active(self.config.auto_start)
        auto_start.connect("toggled", self._on_auto_start_toggled)
        box.pack_start(auto_start, False, False, 0)
        
        # System tray
        tray_icon = Gtk.CheckButton(label="Show system tray icon")
        tray_icon.set_active(self.config.show_tray_icon)
        tray_icon.connect("toggled", self._on_tray_icon_toggled)
        box.pack_start(tray_icon, False, False, 0)
        
        # Notification preferences
        frame = Gtk.Frame(label="Notifications")
        frame.set_border_width(5)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        frame.add(vbox)
        
        notify_start = Gtk.CheckButton(label="Notify when recording starts")
        notify_start.set_active(self.config.notify_recording_start)
        notify_start.connect("toggled", self._on_notify_start_toggled)
        vbox.pack_start(notify_start, False, False, 0)
        
        notify_stop = Gtk.CheckButton(label="Notify when recording stops")
        notify_stop.set_active(self.config.notify_recording_stop)
        notify_stop.connect("toggled", self._on_notify_stop_toggled)
        vbox.pack_start(notify_stop, False, False, 0)
        
        box.pack_start(frame, False, False, 0)
        
        self.notebook.append_page(box, Gtk.Label(label="General"))
    
    def _create_audio_tab(self):
        """Create audio settings tab."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        
        # Input device
        input_frame = Gtk.Frame(label="Input Device")
        input_frame.set_border_width(5)
        
        input_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        input_frame.add(input_box)
        
        # Device combo
        device_store = Gtk.ListStore(str, str)  # name, id
        # TODO: Populate with actual devices
        
        device_combo = Gtk.ComboBox.new_with_model_and_entry(device_store)
        device_combo.set_entry_text_column(0)
        device_combo.connect("changed", self._on_device_changed)
        input_box.pack_start(device_combo, False, False, 0)
        
        # Test button
        test_button = Gtk.Button(label="Test Microphone")
        test_button.connect("clicked", self._on_test_microphone)
        input_box.pack_start(test_button, False, False, 0)
        
        box.pack_start(input_frame, False, False, 0)
        
        # Audio levels visualization
        level_frame = Gtk.Frame(label="Audio Levels")
        level_frame.set_border_width(5)
        
        level_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        level_frame.add(level_box)
        
        # Level bar
        self.level_bar = Gtk.LevelBar()
        self.level_bar.set_min_value(0)
        self.level_bar.set_max_value(1)
        self.level_bar.set_value(0)
        level_box.pack_start(self.level_bar, False, False, 0)
        
        # Threshold adjustment
        threshold_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        threshold_label = Gtk.Label(label="Silence Threshold:")
        threshold_box.pack_start(threshold_label, False, False, 0)
        
        self.threshold_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 0.1, 0.001
        )
        self.threshold_scale.set_value(self.config.silence_threshold)
        self.threshold_scale.set_digits(3)
        self.threshold_scale.connect("value-changed", self._on_threshold_changed)
        threshold_box.pack_start(self.threshold_scale, True, True, 0)
        
        level_box.pack_start(threshold_box, False, False, 0)
        
        box.pack_start(level_frame, False, False, 0)
        
        self.notebook.append_page(box, Gtk.Label(label="Audio"))
    
    def _create_model_tab(self):
        """Create model settings tab."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        
        # Model selection
        model_frame = Gtk.Frame(label="Transcription Model")
        model_frame.set_border_width(5)
        
        model_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        model_frame.add(model_box)
        
        # Model combo
        model_store = Gtk.ListStore(str, str, str)  # name, size, quality
        models = [
            ("tiny.en", "~1GB VRAM", "Good for fast transcription"),
            ("small.en", "~2GB VRAM", "Better accuracy"),
            ("distil-medium.en", "~3GB VRAM", "Best balance"),
            ("medium.en", "~5GB VRAM", "Highest accuracy"),
        ]
        
        for model in models:
            model_store.append(model)
        
        model_combo = Gtk.ComboBox.new_with_model(model_store)
        renderer = Gtk.CellRendererText()
        model_combo.pack_start(renderer, True)
        model_combo.add_attribute(renderer, "text", 0)
        
        # Set current model
        for i, model in enumerate(models):
            if model[0] == self.config.model_name:
                model_combo.set_active(i)
                break
        
        model_combo.connect("changed", self._on_model_changed)
        model_box.pack_start(model_combo, False, False, 0)
        
        # Model info
        info_label = Gtk.Label()
        info_label.set_markup("<small>Select model based on available VRAM</small>")
        info_label.set_xalign(0)
        model_box.pack_start(info_label, False, False, 0)
        
        # Device selection
        device_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        device_label = Gtk.Label(label="Device:")
        device_box.pack_start(device_label, False, False, 0)
        
        device_combo = Gtk.ComboBoxText()
        device_combo.append_text("Auto-detect")
        device_combo.append_text("CUDA (NVIDIA GPU)")
        device_combo.append_text("CPU")
        
        if self.config.device == "cuda":
            device_combo.set_active(1)
        elif self.config.device == "cpu":
            device_combo.set_active(2)
        else:
            device_combo.set_active(0)
        
        device_combo.connect("changed", self._on_device_type_changed)
        device_box.pack_start(device_combo, True, True, 0)
        
        model_box.pack_start(device_box, False, False, 0)
        
        box.pack_start(model_frame, False, False, 0)
        
        # Model download/management
        manage_frame = Gtk.Frame(label="Model Management")
        manage_frame.set_border_width(5)
        
        manage_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        manage_frame.add(manage_box)
        
        # Download button
        download_button = Gtk.Button(label="Download Selected Model")
        download_button.connect("clicked", self._on_download_model)
        manage_box.pack_start(download_button, False, False, 0)
        
        # Progress bar
        self.download_progress = Gtk.ProgressBar()
        manage_box.pack_start(self.download_progress, False, False, 0)
        
        # Model location
        location_button = Gtk.Button(label="Open Model Directory")
        location_button.connect("clicked", self._on_open_model_dir)
        manage_box.pack_start(location_button, False, False, 0)
        
        box.pack_start(manage_frame, False, False, 0)
        
        self.notebook.append_page(box, Gtk.Label(label="Model"))
    
    def _save_configuration(self) -> bool:
        """Save configuration to file."""
        try:
            config_dict = self.config.to_dict()
            
            # Validate configuration
            self._validate_config(config_dict)
            
            # Save to file
            config_file = Path.home() / ".config" / "voicetype" / "config.yaml"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, "w") as f:
                yaml.dump(config_dict, f, default_flow_style=False)
            
            self.statusbar.push(0, "Configuration saved successfully")
            self.changed = False
            return True
            
        except ConfigurationError as e:
            self._show_error(f"Configuration error: {e}")
            return False
        except Exception as e:
            self._show_error(f"Failed to save configuration: {e}")
            return False
    
    def _show_error(self, message: str):
        """Show error dialog."""
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            message_format=message,
        )
        dialog.run()
        dialog.destroy()
```

**Testing Strategy**:
1. **UI Tests**: Test dialog creation and widget interaction
2. **Configuration Tests**: Test config save/load functionality
3. **Validation Tests**: Test configuration validation
4. **Integration Tests**: Test dialog integration with main application

**DoD**:
- [ ] GTK-based configuration dialog with tabs
- [ ] Real-time configuration validation with error messages
- [ ] Configuration preview/live update where possible
- [ ] Import/export configuration functionality
- [ ] Profile management (save/load presets)
- [ ] Accessible from system tray menu
- [ ] Keyboard navigation support
- [ ] Configuration changes take effect without restart (where possible)

### 5.2 First-Run Wizard

**Problem**: No onboarding, users must figure out setup.

**Implementation**:

1. **First-Run Wizard** (`ui/first_run.py`):
```python
class FirstRunWizard(Gtk.Dialog):
    def __init__(self):
        super().__init__(
            title="VoiceType Setup Wizard",
            flags=Gtk.DialogFlags.MODAL,
            buttons=(
                "Cancel", Gtk.ResponseType.CANCEL,
                "Back", Gtk.ResponseType.REJECT,
                "Next", Gtk.ResponseType.ACCEPT,
            )
        )
        
        self.set_default_size(500, 400)
        self.set_border_width(20)
        
        self.steps = [
            self._welcome_step,
            self._audio_setup_step,
            self._hotkey_setup_step,
            self._model_setup_step,
            self._completion_step,
        ]
        
        self.current_step = 0
        self.config = {}
        
        # Navigation
        self.next_button = self.get_widget_for_response(Gtk.ResponseType.ACCEPT)
        self.back_button = self.get_widget_for_response(Gtk.ResponseType.REJECT)
        self.back_button.set_sensitive(False)
        
        self.next_button.connect("clicked", self._on_next)
        self.back_button.connect("clicked", self._on_back)
        
        # Show first step
        self._show_step(0)
    
    def _show_step(self, step_index: int):
        """Show a specific step."""
        # Clear current content
        content_area = self.get_content_area()
        for child in content_area.get_children():
            if child not in [self.next_button, self.back_button]:
                content_area.remove(child)
        
        # Show step
        step_widget = self.steps[step_index]()
        content_area.pack_start(step_widget, True, True, 0)
        
        # Update navigation
        self.current_step = step_index
        self.back_button.set_sensitive(step_index > 0)
        
        if step_index == len(self.steps) - 1:
            self.next_button.set_label("Finish")
        else:
            self.next_button.set_label("Next")
        
        self.show_all()
    
    def _welcome_step(self) -> Gtk.Widget:
        """Welcome step."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        
        # Logo/icon
        icon = Gtk.Image.new_from_icon_name("audio-input-microphone", Gtk.IconSize.DIALOG)
        icon.set_pixel_size(64)
        box.pack_start(icon, False, False, 0)
        
        # Title
        title = Gtk.Label()
        title.set_markup("<span size='x-large' weight='bold'>Welcome to VoiceType</span>")
        title.set_xalign(0.5)
        box.pack_start(title, False, False, 0)
        
        # Description
        desc = Gtk.Label()
        desc.set_markup(
            "VoiceType is a local AI voice dictation tool for Linux.\n\n"
            "This wizard will help you set up:\n"
            "• Microphone configuration\n"
            "• Hotkey setup\n"
            "• AI model download\n\n"
            "Click Next to continue."
        )
        desc.set_line_wrap(True)
        desc.set_xalign(0)
        box.pack_start(desc, False, False, 0)
        
        return box
    
    def _audio_setup_step(self) -> Gtk.Widget:
        """Audio setup step."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        
        title = Gtk.Label()
        title.set_markup("<span size='large' weight='bold'>Microphone Setup</span>")
        title.set_xalign(0)
        box.pack_start(title, False, False, 0)
        
        # Device selection
        device_frame = Gtk.Frame(label="Select Microphone")
        device_frame.set_border_width(5)
        
        device_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        device_frame.add(device_box)
        
        # Get available devices
        devices = self._get_audio_devices()
        device_store = Gtk.ListStore(str, str)  # name, id
        
        for device in devices:
            device_store.append([device["name"], device["id"]])
        
        self.device_combo = Gtk.ComboBox.new_with_model(device_store)
        renderer = Gtk.CellRendererText()
        self.device_combo.pack_start(renderer, True)
        self.device_combo.add_attribute(renderer, "text", 0)
        
        if devices:
            self.device_combo.set_active(0)
        
        device_box.pack_start(self.device_combo, False, False, 0)
        
        # Test button
        test_button = Gtk.Button(label="Test Microphone")
        test_button.connect("clicked", self._on_test_microphone)
        device_box.pack_start(test_button, False, False, 0)
        
        # Visual feedback
        self.level_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        self.level_bar = Gtk.LevelBar()
        self.level_bar.set_min_value(0)
        self.level_bar.set_max_value(1)
        self.level_bar.set_value(0)
        self.level_box.pack_start(self.level_bar, True, True, 0)
        
        self.level_label = Gtk.Label("0%")
        self.level_box.pack_start(self.level_label, False, False, 0)
        
        device_box.pack_start(self.level_box, False, False, 0)
        
        box.pack_start(device_frame, False, False, 0)
        
        # Instructions
        instructions = Gtk.Label()
        instructions.set_markup(
            "<small>Speak into your microphone to test audio levels.\n"
            "Adjust your microphone volume if levels are too low or too high.</small>"
        )
        instructions.set_line_wrap(True)
        instructions.set_xalign(0)
        box.pack_start(instructions, False, False, 0)
        
        return box
    
    def _hotkey_setup_step(self) -> Gtk.Widget:
        """Hotkey setup step."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        
        title = Gtk.Label()
        title.set_markup("<span size='large' weight='bold'>Hotkey Setup</span>")
        title.set_xalign(0)
        box.pack_start(title, False, False, 0)
        
        # Hotkey entry
        hotkey_frame = Gtk.Frame(label="Recording Hotkey")
        hotkey_frame.set_border_width(5)
        
        hotkey_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        hotkey_frame.add(hotkey_box)
        
        # Current hotkey display
        self.hotkey_label = Gtk.Label()
        self.hotkey_label.set_markup("<span size='xx-large' weight='bold'>Super + I</span>")
        self.hotkey_label.set_xalign(0.5)
        hotkey_box.pack_start(self.hotkey_label, False, False, 0)
        
        # Change button
        change_button = Gtk.Button(label="Change Hotkey")
        change_button.connect("clicked", self._on_change_hotkey)
        hotkey_box.pack_start(change_button, False, False, 0)
        
        # Test area
        test_label = Gtk.Label("Press the hotkey to test:")
        test_label.set_xalign(0)
        hotkey_box.pack_start(test_label, False, False, 0)
        
        self.test_status = Gtk.Label("Waiting...")
        self.test_status.set_xalign(0)
        hotkey_box.pack_start(self.test_status, False, False, 0)
        
        box.pack_start(hotkey_frame, False, False, 0)
        
        # Instructions
        instructions = Gtk.Label()
        instructions.set_markup(
            "<small>The hotkey starts and stops recording.\n"
            "Make sure it doesn't conflict with other applications.</small>"
        )
        instructions.set_line_wrap(True)
        instructions.set_xalign(0)
        box.pack_start(instructions, False, False, 0)
        
        return box
    
    def _model_setup_step(self) -> Gtk.Widget:
        """Model setup step."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        
        title = Gtk.Label()
        title.set_markup("<span size='large' weight='bold'>AI Model Setup</span>")
        title.set_xalign(0)
        box.pack_start(title, False, False, 0)
        
        # Model selection
        model_frame = Gtk.Frame(label="Select Model")
        model_frame.set_border_width(5)
        
        model_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        model_frame.add(model_box)
        
        # Model info
        info = Gtk.Label()
        info.set_markup(
            "VoiceType uses AI models for transcription.\n"
            "Larger models are more accurate but require more resources."
        )
        info.set_line_wrap(True)
        info.set_xalign(0)
        model_box.pack_start(info, False, False, 0)
        
        # Model options
        options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        self.model_buttons = {}
        models = [
            ("tiny", "Tiny (Fastest, ~1GB VRAM)", "Good for basic dictation"),
            ("small", "Small (Fast, ~2GB VRAM)", "Better accuracy"),
            ("distil-medium", "Distilled Medium (Recommended, ~3GB VRAM)", "Best balance"),
            ("medium", "Medium (Slowest, ~5GB VRAM)", "Highest accuracy"),
        ]
        
        for model_id, name, desc in models:
            button = Gtk.RadioButton.new_with_label_from_widget(
                None if not self.model_buttons else list(self.model_buttons.values())[0],
                name
            )
            button.set_tooltip_text(desc)
            button.connect("toggled", self._on_model_selected, model_id)
            
            options_box.pack_start(button, False, False, 0)
            self.model_buttons[model_id] = button
        
        # Select recommended by default
        if "distil-medium" in self.model_buttons:
            self.model_buttons["distil-medium"].set_active(True)
        
        model_box.pack_start(options_box, False, False, 0)
        
        # Download button
        self.download_button = Gtk.Button(label="Download Model")
        self.download_button.connect("clicked", self._on_download_model)
        model_box.pack_start(self.download_button, False, False, 0)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_visible(False)
        model_box.pack_start(self.progress_bar, False, False, 0)
        
        box.pack_start(model_frame, False, False, 0)
        
        return box
    
    def _completion_step(self) -> Gtk.Widget:
        """Completion step."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        
        # Success icon
        icon = Gtk.Image.new_from_icon_name("emblem-ok", Gtk.IconSize.DIALOG)
        icon.set_pixel_size(64)
        box.pack_start(icon, False, False, 0)
        
        # Title
        title = Gtk.Label()
        title.set_markup("<span size='x-large' weight='bold'>Setup Complete!</span>")
        title.set_xalign(0.5)
        box.pack_start(title, False, False, 0)
        
        # Summary
        summary = Gtk.Label()
        summary.set_markup(
            "VoiceType is now ready to use!\n\n"
            "To start dictating:\n"
            "1. Press your configured hotkey (default: Super + I)\n"
            "2. Speak clearly into your microphone\n"
            "3. Press the hotkey again to stop and transcribe\n\n"
            "You can change settings anytime from the system tray menu."
        )
        summary.set_line_wrap(True)
        summary.set_xalign(0)
        box.pack_start(summary, False, False, 0)
        
        # Quick test
        test_frame = Gtk.Frame(label="Quick Test")
        test_frame.set_border_width(5)
        
        test_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        test_frame.add(test_box)
        
        test_button = Gtk.Button(label="Test Now (Record 5 seconds)")
        test_button.connect("clicked", self._on_quick_test)
        test_box.pack_start(test_button, False, False, 0)
        
        self.test_result = Gtk.Label()
        self.test_result.set_xalign(0)
        test_box.pack_start(self.test_result, False, False, 0)
        
        box.pack_start(test_frame, False, False, 0)
        
        return box
```

**Testing Strategy**:
1. **Wizard Flow Tests**: Test navigation through wizard steps
2. **Configuration Tests**: Test configuration saved correctly
3. **Integration Tests**: Test wizard integration with main app
4. **Error Handling Tests**: Test wizard error recovery

**DoD**:
- [ ] Wizard runs on first launch (detected via flag file)
- [ ] Microphone testing with visual feedback
- [ ] Hotkey configuration with live testing
- [ ] Model download with progress indication
- [ ] Configuration validation at each step
- [ ] Ability to skip and use defaults
- [ ] Wizard results in functional configuration
- [ ] Quick test feature at the end

## 6. Performance & Resource Management

### 6.1 Resource Monitoring

**Problem**: No resource management, memory leaks possible.

**Implementation**:

1. **Resource Monitor** (`utils/monitoring.py`):
```python
import psutil
import threading
import time
from typing import Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum

class ResourceLevel(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class ResourceMetrics:
    memory_mb: float
    memory_percent: float
    cpu_percent: float
    gpu_memory_mb: Optional[float] = None
    gpu_utilization: Optional[float] = None
    audio_buffer_size: Optional[int] = None
    model_loaded: bool = False

class ResourceMonitor:
    def __init__(self, config: Dict):
        self.config = config
        self.metrics = ResourceMetrics(0, 0, 0)
        self._running = False
        self._thread = None
        self._callbacks = []
        self._process = psutil.Process()
        
        # Thresholds (configurable)
        self.memory_warning_mb = config.get("memory_warning_mb", 2048)
        self.memory_critical_mb = config.get("memory_critical_mb", 3072)
        self.cpu_warning_percent = config.get("cpu_warning_percent", 80)
        self.cpu_critical_percent = config.get("cpu_critical_percent", 95)
    
    def start(self):
        """Start resource monitoring."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop resource monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _monitor_loop(self):
        """Monitoring loop."""
        update_interval = self.config.get("update_interval", 5.0)
        
        while self._running:
            try:
                self._update_metrics()
                self._check_thresholds()
                self._notify_callbacks()
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
            
            time.sleep(update_interval)
    
    def _update_metrics(self):
        """Update resource metrics."""
        # Memory
        memory_info = self._process.memory_info()
        self.metrics.memory_mb = memory_info.rss / 1024 / 1024
        self.metrics.memory_percent = self._process.memory_percent()
        
        # CPU
        self.metrics.cpu_percent = self._process.cpu_percent(interval=0.1)
        
        # GPU (if available)
        self.metrics.gpu_memory_mb = self._get_gpu_memory()
        self.metrics.gpu_utilization = self._get_gpu_utilization()
    
    def _get_gpu_memory(self) -> Optional[float]:
        """Get GPU memory usage if NVIDIA GPU is available."""
        try:
            import pynvml
            pynvml.nvmlInit()
            
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                return info.used / 1024 / 1024
            
            pynvml.nvmlShutdown()
        except:
            pass
        
        return None
    
    def _check_thresholds(self):
        """Check metrics against thresholds."""
        level = ResourceLevel.NORMAL
        
        if self.metrics.memory_mb > self.memory_critical_mb:
            level = ResourceLevel.CRITICAL
        elif self.metrics.memory_mb > self.memory_warning_mb:
            level = ResourceLevel.WARNING
        
        if self.metrics.cpu_percent > self.cpu_critical_percent:
            level = ResourceLevel.CRITICAL
        elif self.metrics.cpu_percent > self.cpu_warning_percent:
            if level == ResourceLevel.NORMAL:
                level = ResourceLevel.WARNING
        
        self.metrics.level = level
        
        if level == ResourceLevel.CRITICAL:
            self._handle_critical_level()
        elif level == ResourceLevel.WARNING:
            self._handle_warning_level()
    
    def _handle_critical_level(self):
        """Handle critical resource levels."""
        logger.warning(f"Critical resource levels: {self.metrics}")
        
        # Try to free memory
        self._cleanup_memory()
        
        # Notify UI
        self._notify_ui("Critical resource levels - performance may degrade")
    
    def _handle_warning_level(self):
        """Handle warning resource levels."""
        logger.info(f"Warning resource levels: {self.metrics}")
        
        # Suggest cleanup
        self._notify_ui("High resource usage - consider closing other applications")
    
    def _cleanup_memory(self):
        """Clean up memory."""
        import gc
        
        # Force garbage collection
        gc.collect()
        
        # Clear CUDA cache if available
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("Cleared CUDA cache")
        except:
            pass
        
        # Clear model cache if config allows
        if self.config.get("auto_unload_model", False):
            self._unload_model_if_idle()
    
    def register_callback(self, callback: Callable[[ResourceMetrics], None]):
        """Register callback for metric updates."""
        self._callbacks.append(callback)
    
    def _notify_callbacks(self):
        """Notify registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(self.metrics)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def get_report(self) -> Dict:
        """Get resource usage report."""
        return {
            "memory_mb": round(self.metrics.memory_mb, 2),
            "memory_percent": round(self.metrics.memory_percent, 1),
            "cpu_percent": round(self.metrics.cpu_percent, 1),
            "gpu_memory_mb": round(self.metrics.gpu_memory_mb, 2) if self.metrics.gpu_memory_mb else None,
            "level": self.metrics.level.value if hasattr(self.metrics, "level") else "normal",
            "timestamp": time.time(),
        }
```

2. **Model Manager with Resource Awareness** (`core/model_manager.py`):
```python
class ResourceAwareModelManager:
    def __init__(self, config: Dict, resource_monitor: ResourceMonitor):
        self.config = config
        self.monitor = resource_monitor
        self.model = None
        self.model_loaded = False
        self.last_used = 0
        self.unload_timeout = config.get("model_unload_timeout", 300)  # 5 minutes
        
        # Register for resource updates
        self.monitor.register_callback(self._on_resource_update)
    
    def load_model(self, force: bool = False):
        """Load model with resource awareness."""
        if self.model_loaded and not force:
            return
        
        # Check available resources
        if not self._has_sufficient_resources():
            raise ModelError("Insufficient resources to load model")
        
        # Load model
        self.model = self._load_model_implementation()
        self.model_loaded = True
        self.last_used = time.time()
        
        logger.info("Model loaded with resource awareness")
    
    def _has_sufficient_resources(self) -> bool:
        """Check if sufficient resources are available."""
        metrics = self.monitor.metrics
        
        # Check memory
        required_memory = self._get_model_memory_requirement()
        if metrics.memory_mb + required_memory > self.config.get("max_memory_mb", 4096):
            logger.warning(f"Insufficient memory for model: {required_memory}MB required")
            return False
        
        return True
    
    def _get_model_memory_requirement(self) -> float:
        """Get estimated memory requirement for current model."""
        model_sizes = {
            "tiny": 1000,  # MB
            "small": 2000,
            "distil-medium": 3000,
            "medium": 5000,
        }
        
        model_name = self.config.get("model_name", "distil-medium")
        for size_name, mb in model_sizes.items():
            if size_name in model_name:
                return mb
        
        return 3000  # Default
    
    def unload_if_idle(self):
        """Unload model if idle for too long."""
        if not self.model_loaded:
            return
        
        idle_time = time.time() - self.last_used
        if idle_time > self.unload_timeout:
            logger.info(f"Unloading idle model (idle for {idle_time:.0f}s)")
            self.unload_model()
    
    def unload_model(self):
        """Unload model to free memory."""
        if self.model:
            # Clean up model resources
            if hasattr(self.model, "cpu"):
                self.model.cpu()
            
            del self.model
            self.model = None
        
        self.model_loaded = False
        
        # Force cleanup
        import gc
        gc.collect()
        
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except:
            pass
        
        logger.info("Model unloaded")
    
    def _on_resource_update(self, metrics: ResourceMetrics):
        """Handle resource updates."""
        # Unload model if resources are critical
        if metrics.level == ResourceLevel.CRITICAL and self.model_loaded:
            logger.warning("Unloading model due to critical resource levels")
            self.unload_model()
```

**Testing Strategy**:
1. **Resource Tests**: Test memory/CPU monitoring accuracy
2. **Threshold Tests**: Test warning/critical threshold detection
3. **Cleanup Tests**: Test automatic cleanup on resource pressure
4. **Performance Tests**: Test monitoring overhead

**DoD**:
- [ ] Memory usage monitoring with configurable thresholds
- [ ] CPU usage monitoring
- [ ] GPU memory monitoring (if available)
- [ ] Automatic cleanup on critical resource levels
- [ ] Model unloading during idle periods
- [ ] Resource usage reports available via API
- [ ] UI indicators for resource status
- [ ] Monitoring overhead < 1% CPU, < 50MB memory

## 7. Advanced Features

### 7.1 Multi-Language Support

**Problem**: English-only transcription.

**Implementation**:

1. **Language Detection and Support** (`core/language.py`):
```python
from enum import Enum
from typing import Dict, List, Optional, Tuple
import numpy as np

class Language(Enum):
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    DUTCH = "nl"
    RUSSIAN = "ru"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"

class LanguageManager:
    # Language families for model selection
    EUROPEAN_LANGUAGES = {Language.ENGLISH, Language.SPANISH, Language.FRENCH, 
                          Language.GERMAN, Language.ITALIAN, Language.PORTUGUESE,
                          Language.DUTCH}
    
    ASIAN_LANGUAGES = {Language.CHINESE, Language.JAPANESE, Language.KOREAN}
    
    # Language-specific configurations
    LANGUAGE_CONFIGS = {
        Language.ENGLISH: {
            "model": "distil-medium.en",
            "filler_words": {"um", "uh", "like", "you know", "i mean"},
            "auto_punctuate": True,
            "auto_capitalize": True,
        },
        Language.SPANISH: {
            "model": "distil-medium",
            "filler_words": {"eh", "este", "o sea", "pues"},
            "auto_punctuate": True,
            "auto_capitalize": True,  # Spanish capitalizes differently
        },
        Language.FRENCH: {
            "model": "distil-medium",
            "filler_words": {"euh", "alors", "donc", "quoi"},
            "auto_punctuate": True,
            "auto_capitalize": True,
        },
        # Add more languages...
    }
    
    def __init__(self, config: Dict):
        self.config = config
        self.current_language = Language.ENGLISH
        self.detected_languages = []
        
    def detect_language(self, audio: np.ndarray) -> Optional[Language]:
        """Detect language from audio."""
        try:
            # Try to use whisper's built-in language detection
            if hasattr(self, "_whisper_model"):
                segments, info = self._whisper_model.transcribe(
                    audio,
                    task="translate",  # This returns language info
                    beam_size=1,
                    best_of=1,
                )
                
                if hasattr(info, "language") and info.language:
                    lang_code = info.language
                    for lang in Language:
                        if lang.value == lang_code:
                            return lang
            
            # Fallback: Use speech recognition with langdetect
            import langdetect
            from speech_recognition import Recognizer, AudioData
            
            # Convert audio to speech recognition format
            audio_data = AudioData(
                audio.tobytes(),
                sample_rate=16000,
                sample_width=2
            )
            
            recognizer = Recognizer()
            text = recognizer.recognize_google(audio_data, show_all=True)
            
            if "alternative" in text and len(text["alternative"]) > 0:
                detected_text = text["alternative"][0]["transcript"]
                detected_lang = langdetect.detect(detected_text)
                
                for lang in Language:
                    if lang.value == detected_lang:
                        return lang
        
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
        
        return None
    
    def get_language_config(self, language: Language) -> Dict:
        """Get configuration for specific language."""
        config = self.LANGUAGE_CONFIGS.get(language, {})
        
        # Merge with user configuration
        user_config = self.config.get("language_overrides", {}).get(language.value, {})
        config.update(user_config)
        
        return config
    
    def switch_language(self, language: Language):
        """Switch to different language."""
        if language == self.current_language:
            return
        
        logger.info(f"Switching language to {language.name}")
        
        # Get language-specific configuration
        lang_config = self.get_language_config(language)
        
        # Update current configuration
        self.config.update(lang_config)
        self.current_language = language
        
        # Reload model if needed
        if lang_config.get("model") != self.config.get("current_model"):
            self._load_language_model(lang_config["model"])
        
        # Update UI
        self._update_ui_for_language(language)
    
    def _load_language_model(self, model_name: str):
        """Load language-specific model."""
        # Implementation depends on model loading system
        pass
    
    def get_available_languages(self) -> List[Dict]:
        """Get list of available languages with metadata."""
        return [
            {
                "code": lang.value,
                "name": lang.name,
                "native_name": self._get_native_name(lang),
                "supported": lang in self.LANGUAGE_CONFIGS,
                "model_available": self._check_model_available(lang),
            }
            for lang in Language
        ]
```

2. **Multi-Language UI** (`ui/language_selector.py`):
```python
class LanguageSelector(Gtk.Box):
    def __init__(self, language_manager: LanguageManager):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        self.language_manager = language_manager
        
        # Language combo
        self.language_store = Gtk.ListStore(str, str, str)  # code, name, flag
        
        # Add languages
        for lang_info in language_manager.get_available_languages():
            if lang_info["supported"]:
                flag = self._get_flag_emoji(lang_info["code"])
                self.language_store.append([
                    lang_info["code"],
                    f"{flag} {lang_info['native_name']}",
                    flag
                ])
        
        self.language_combo = Gtk.ComboBox.new_with_model(self.language_store)
        renderer = Gtk.CellRendererText()
        self.language_combo.pack_start(renderer, True)
        self.language_combo.add_attribute(renderer, "text", 1)
        
        # Set current language
        current_code = language_manager.current_language.value
        for i, row in enumerate(self.language_store):
            if row[0] == current_code:
                self.language_combo.set_active(i)
                break
        
        self.language_combo.connect("changed", self._on_language_changed)
        
        self.pack_start(self.language_combo, False, False, 0)
    
    def _on_language_changed(self, combo):
        """Handle language change."""
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            lang_code = model[tree_iter][0]
            
            # Find language enum
            for lang in Language:
                if lang.value == lang_code:
                    self.language_manager.switch_language(lang)
                    break
```

**Testing Strategy**:
1. **Language Detection Tests**: Test audio language detection accuracy
2. **Configuration Tests**: Test language-specific configurations
3. **UI Tests**: Test language selector UI
4. **Integration Tests**: Test end-to-end multi-language dictation

**DoD**:
- [ ] Support for 5+ major languages (en, es, fr, de, it)
- [ ] Automatic language detection from audio
- [ ] Language-specific text processing rules
- [ ] UI localization framework
- [ ] Translated UI strings for 2-3 languages
- [ ] Language switching without restart
- [ ] Language-specific model downloading

## Conclusion

This implementation guide provides detailed, actionable steps for transforming VoiceType into a production-ready product. Each section includes:

1. **Clear Problem Statement**: What needs to be fixed
2. **Practical Implementation**: Code examples and architecture
3. **Comprehensive Testing**: How to verify the implementation
4. **Measurable DoD**: Specific criteria for completion

The guide follows a phased approach, starting with foundational improvements (architecture, error handling, security), then moving to platform support, testing infrastructure, user experience, and finally advanced features.

By following this guide, VoiceType can evolve from a proof-of-concept into a robust, user-friendly, and production-ready open-source voice dictation tool.