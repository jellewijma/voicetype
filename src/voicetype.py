#!/usr/bin/env python3
"""
VoiceType - Local AI Voice Dictation for Linux
Inspired by Wispr Flow, uses faster-whisper for fast, accurate transcription.
Controlled via Hyprland keybind -> socket communication.
"""

import os
import sys
import time
import queue
import threading
import tempfile
import wave
import json
import subprocess
import re
import socket
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List

import yaml
import numpy as np
import sounddevice as sd
import pyperclip
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

CONFIG_DIR = Path.home() / ".config" / "voicetype"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
DEFAULT_CONFIG = Path(__file__).parent.parent / "config" / "config.yaml"
SOCKET_PATH = Path(tempfile.gettempdir()) / "voicetype.sock"


@dataclass
class Config:
    model_name: str = "distil-medium.en"
    device: str = "cuda"
    compute_type: str = "float16"
    sample_rate: int = 16000
    channels: int = 1
    silence_threshold: float = 0.01
    silence_duration: float = 1.5
    remove_fillers: bool = True
    auto_capitalize: bool = True
    auto_punctuate: bool = True
    trailing_punctuation: bool = True
    dictionary: Dict[str, str] = field(default_factory=dict)
    snippets: Dict[str, str] = field(default_factory=dict)
    app_overrides: Dict[str, dict] = field(default_factory=dict)


FILLER_WORDS = {
    "um", "uh", "umm", "uhh", "er", "err", "ah", "ahh",
    "like", "you know", "i mean", "sort of", "kind of",
    "basically", "literally", "actually", "honestly"
}


class AudioRecorder:
    def __init__(self, config: Config):
        self.config = config
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.audio_data = []
        self._stop_event = threading.Event()
        
    def start_recording(self):
        self.audio_data = []
        self._stop_event.clear()
        self.is_recording = True
        
        def callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")
            self.audio_queue.put(indata.copy())
        
        self.stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype=np.float32,
            callback=callback
        )
        self.stream.start()
        
        self._process_thread = threading.Thread(target=self._process_audio)
        self._process_thread.start()
        
    def _process_audio(self):
        silence_start = None
        
        while not self._stop_event.is_set():
            try:
                data = self.audio_queue.get(timeout=0.1)
                self.audio_data.append(data)
                
                if self.config.silence_duration > 0:
                    volume = np.abs(data).mean()
                    if volume < self.config.silence_threshold:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > self.config.silence_duration:
                            break
                    else:
                        silence_start = None
            except queue.Empty:
                continue
                
    def stop_recording(self) -> np.ndarray:
        self._stop_event.set()
        self.is_recording = False
        
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
            
        if self._process_thread.is_alive():
            self._process_thread.join(timeout=1.0)
            
        if not self.audio_data:
            return None
            
        return np.concatenate(self.audio_data, axis=0)


class Transcriber:
    def __init__(self, config: Config):
        self.config = config
        self.model = None  # type: ignore
        self._load_model()
        
    def _load_model(self):
        from faster_whisper import WhisperModel
        
        print(f"Loading model: {self.config.model_name}")
        self.model = WhisperModel(
            self.config.model_name,
            device=self.config.device,
            compute_type=self.config.compute_type
        )
        print("Model loaded successfully")
        
    def transcribe(self, audio: np.ndarray) -> str:
        if audio is None or len(audio) == 0:
            return ""
            
        if audio.ndim > 1:
            audio = audio.flatten()
            
        segments, info = self.model.transcribe(  # type: ignore
            audio,
            language="en",
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        text = " ".join(segment.text.strip() for segment in segments)
        return text.strip()


class TextProcessor:
    def __init__(self, config: Config):
        self.config = config
        
    def process(self, text: str) -> str:
        if not text:
            return ""
            
        text = self._remove_fillers(text)
        text = self._apply_dictionary(text)
        text = self._apply_snippets(text)
        text = self._smart_capitalize(text)
        text = self._smart_punctuate(text)
        
        return text
        
    def _remove_fillers(self, text: str) -> str:
        if not self.config.remove_fillers:
            return text
            
        words = text.lower().split()
        filtered = []
        i = 0
        
        while i < len(words):
            word = words[i]
            
            if word in FILLER_WORDS:
                i += 1
                continue
                
            if i + 1 < len(words):
                bigram = f"{word} {words[i+1]}"
                if bigram in FILLER_WORDS:
                    i += 2
                    continue
                    
            if i + 2 < len(words):
                trigram = f"{word} {words[i+1]} {words[i+2]}"
                if trigram in FILLER_WORDS:
                    i += 3
                    continue
                    
            filtered.append(words[i])
            i += 1
            
        result = " ".join(filtered)
        return result
        
    def _apply_dictionary(self, text: str) -> str:
        if not self.config.dictionary:
            return text
            
        for word, replacement in self.config.dictionary.items():
            pattern = r'\b' + re.escape(word) + r'\b'
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            
        return text
        
    def _apply_snippets(self, text: str) -> str:
        if not self.config.snippets:
            return text
            
        for trigger, expansion in self.config.snippets.items():
            if trigger.lower() in text.lower():
                pattern = re.escape(trigger)
                text = re.sub(pattern, expansion, text, flags=re.IGNORECASE)
                
        return text
        
    def _smart_capitalize(self, text: str) -> str:
        if not self.config.auto_capitalize:
            return text
            
        sentences = re.split(r'([.!?]+\s*)', text)
        result = []
        
        for i, part in enumerate(sentences):
            if i % 2 == 0 and part:
                part = part[0].upper() + part[1:] if part else part
            result.append(part)
            
        return "".join(result)
        
    def _smart_punctuate(self, text: str) -> str:
        if not self.config.auto_punctuate:
            return text
            
        if text and not text[-1] in ".!?":
            if self.config.trailing_punctuation:
                text = text + "."
                
        return text


class TextInserter:
    def __init__(self, config: Config):
        self.config = config
        self._use_wayland = os.environ.get('XDG_SESSION_TYPE', '') == 'wayland'
        self._saved_window = None
        
    def save_focus(self):
        if self._use_wayland:
            try:
                result = subprocess.run(
                    ["hyprctl", "activewindow", "-j"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    import json
                    data = json.loads(result.stdout)
                    self._saved_window = data.get("address")
            except:
                pass
                
    def insert(self, text: str):
        if not text:
            return
            
        if self._use_wayland:
            self._insert_wayland(text)
        else:
            self._insert_x11(text)
            
    def _insert_wayland(self, text: str):
        time.sleep(0.1)
        
        if self._saved_window:
            try:
                subprocess.run(
                    ["hyprctl", "dispatch", "focuswindow", f"address:{self._saved_window}"],
                    capture_output=True
                )
                time.sleep(0.05)
            except:
                pass
                
        try:
            result = subprocess.run(["wtype", text], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return
        except:
            pass
            
        try:
            subprocess.run(["wl-copy"], input=text.encode(), check=True)
            time.sleep(0.05)
            subprocess.run(["wtype", "-M", "ctrl", "v", "-m", "ctrl"], check=True)
            return
        except:
            pass
            
        subprocess.run(["wl-copy"], input=text.encode())
        print("Text copied to clipboard - press Ctrl+V to paste")
        
    def _insert_x11(self, text: str):
        try:
            subprocess.run(["xdotool", "type", "--clearmodifiers", text], check=True)
        except subprocess.CalledProcessError:
            pyperclip.copy(text)
            subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+shift+v"], check=True)
            
    def get_active_window(self) -> str:
        try:
            result = subprocess.run(
                ["xdotool", "getwindowfocus", "getwindowname"],
                capture_output=True,
                text=True
            )
            return result.stdout.strip().lower()
        except:
            return ""


class SocketListener:
    def __init__(self, callback):
        self.callback = callback
        self._running = True
        self.socket = None
        
    def start(self):
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
            
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(str(SOCKET_PATH))
        self.socket.listen(1)
        self.socket.settimeout(1.0)
        
        print(f"Socket listening at: {SOCKET_PATH}")
        print("Add to your Hyprland config (~/.config/hypr/hyprland.conf):")
        print('  bind = , F12, exec, echo "toggle" | nc -U /tmp/voicetype.sock')
        print("Then reload Hyprland config.")
        
        def listen():
            while self._running:
                try:
                    conn, _ = self.socket.accept()
                    data = conn.recv(1024).decode().strip()
                    conn.close()
                    
                    if data == "toggle":
                        print("[DEBUG] Toggle command received")
                        GLib.idle_add(self.callback)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self._running:
                        print(f"Socket error: {e}")
                        
        self._thread = threading.Thread(target=listen, daemon=True)
        self._thread.start()
        
    def stop(self):
        self._running = False
        if self.socket:
            self.socket.close()
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()


class RecordingPopup:
    def __init__(self):
        self.window = None
        self.label = None
        self._visible = False
        
    def show(self, text: str = "Listening..."):
        if self.window is None:
            self._create_window()
        
        GLib.idle_add(self._update_text, text)
        
        if not self._visible:
            self._visible = True
            GLib.idle_add(self._do_show)
            
    def _do_show(self):
        if self.window:
            self.window.show_all()
            self._position_window()
        return False
            
    def hide(self):
        if self.window and self._visible:
            self._visible = False
            GLib.idle_add(self.window.hide)
            
    def update_text(self, text: str):
        if self.label:
            GLib.idle_add(self._update_text, text)
            
    def _update_text(self, text: str):
        if self.label:
            self.label.set_text(text)
        return False
        
    def _create_window(self):
        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_decorated(False)
        self.window.set_keep_above(True)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.set_resizable(False)
        self.window.set_accept_focus(False)
        
        self.window.connect("realize", self._on_realize)
        
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b'''
            window {
                background-color: rgba(30, 30, 30, 0.95);
                border-radius: 24px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            .container {
                padding: 14px 20px;
                border-radius: 24px;
            }
            .mic-icon {
                color: #FF5252;
                font-size: 16px;
            }
            label {
                color: white;
                font-size: 14px;
                font-weight: 500;
            }
            .transcribing {
                color: #4CAF50;
            }
        ''')
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.get_style_context().add_class("container")
        
        mic_label = Gtk.Label()
        mic_label.set_markup('<span foreground="#FF5252">●</span>')
        mic_label.set_margin_end(4)
        hbox.pack_start(mic_label, False, False, 0)
        
        self.label = Gtk.Label(label="Listening...")
        hbox.pack_start(self.label, False, False, 0)
        
        self.window.add(hbox)
        
    def _on_realize(self, widget):
        window = widget.get_window()
        if window:
            window.set_override_redirect(True)
        
    def _position_window(self):
        if not self.window:
            return
            
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        if not monitor:
            monitor = display.get_monitor(0)
        if not monitor:
            return
            
        geometry = monitor.get_geometry()
        window_width, window_height = self.window.get_size()
        
        x = geometry.x + (geometry.width - window_width) // 2
        y = geometry.y + geometry.height - window_height - 80
        
        self.window.move(x, y)


class SystemTray:
    def __init__(self, app: 'VoiceType'):
        self.app = app
        self.icon = None  # type: ignore
        
    def start(self):
        try:
            import pystray
            from PIL import Image, ImageDraw
            
            if not self._check_system_tray():
                return False
                
            def create_icon():
                img = Image.new('RGB', (64, 64), color='black')
                draw = ImageDraw.Draw(img)
                draw.ellipse([8, 8, 56, 56], fill='red')
                return img
                
            menu = pystray.Menu(
                pystray.MenuItem("Record", self._toggle_record, checked=lambda _: self.app.is_recording),
                pystray.MenuItem("Settings", self._open_settings),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self._quit)
            )
            
            self.icon = pystray.Icon("voicetype", create_icon(), "VoiceType", menu)
            self.icon.run()
            return True
        except Exception:
            return False
            
    def _check_system_tray(self):
        try:
            import subprocess
            result = subprocess.run(
                ["xdotool", "search", "--class", "panel"],
                capture_output=True,
                text=True
            )
            if not result.stdout.strip():
                result = subprocess.run(
                    ["xdotool", "search", "--name", "tray"],
                    capture_output=True,
                    text=True
                )
            return bool(result.stdout.strip()) or os.environ.get('XDG_CURRENT_DESKTOP', '').lower() in ['kde', 'xfce', 'lxqt', 'mate']
        except:
            return False
            
    def _toggle_record(self):
        self.app.toggle_recording()
        
    def _open_settings(self):
        import subprocess
        editor = os.environ.get('EDITOR', 'nano')
        subprocess.Popen([editor, str(CONFIG_FILE)])
        
    def _quit(self):
        if self.icon:
            self.icon.stop()  # type: ignore
        self.app.quit()
        
    def update_icon(self, recording: bool):
        if self.icon:
            from PIL import Image, ImageDraw
            
            def create_icon():
                color = 'red' if recording else 'green'
                img = Image.new('RGB', (64, 64), color='black')
                draw = ImageDraw.Draw(img)
                draw.ellipse([8, 8, 56, 56], fill=color)
                return img
                
            self.icon.icon = create_icon()


class VoiceType:
    def __init__(self):
        self.config = self._load_config()
        self.recorder = AudioRecorder(self.config)
        self.transcriber = Transcriber(self.config)
        self.processor = TextProcessor(self.config)
        self.inserter = TextInserter(self.config)
        self.tray = SystemTray(self)
        self.popup = RecordingPopup()
        self.is_recording = False
        self._running = True
        
    def _load_config(self) -> Config:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        config = Config()
        
        if not CONFIG_FILE.exists() and DEFAULT_CONFIG.exists():
            import shutil
            shutil.copy(DEFAULT_CONFIG, CONFIG_FILE)
            
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                data = yaml.safe_load(f) or {}
                
            if 'model' in data:
                m = data['model']
                config.model_name = m.get('name', config.model_name)
                config.device = m.get('device', config.device)
                config.compute_type = m.get('compute_type', config.compute_type)
                
            if 'audio' in data:
                a = data['audio']
                config.sample_rate = a.get('sample_rate', config.sample_rate)
                config.channels = a.get('channels', config.channels)
                config.silence_threshold = a.get('silence_threshold', config.silence_threshold)
                config.silence_duration = a.get('silence_duration', config.silence_duration)
                
            if 'text_processing' in data:
                t = data['text_processing']
                config.remove_fillers = t.get('remove_fillers', config.remove_fillers)
                config.auto_capitalize = t.get('auto_capitalize', config.auto_capitalize)
                config.auto_punctuate = t.get('auto_punctuate', config.auto_punctuate)
                config.trailing_punctuation = t.get('trailing_punctuation', config.trailing_punctuation)
                
            config.dictionary = data.get('dictionary', {})
            config.snippets = data.get('snippets', {})
            config.app_overrides = data.get('app_overrides', {})
            
        return config
        
    def toggle_recording(self):
        if self.is_recording:
            self._stop_and_transcribe()
        else:
            self._start_recording()
            
    def _start_recording(self):
        self.inserter.save_focus()
        self.is_recording = True
        self.recorder.start_recording()
        self.tray.update_icon(True)
        self.popup.show("Listening...")
        print("Recording started...")
        
    def _stop_and_transcribe(self):
        self.is_recording = False
        self.tray.update_icon(False)
        self.popup.update_text("Transcribing...")
        print("Recording stopped. Transcribing...")
        
        audio = self.recorder.stop_recording()
        if audio is not None:
            text = self.transcriber.transcribe(audio)
            processed = self.processor.process(text)
            
            self.popup.hide()
            
            if processed:
                self.inserter.insert(processed)
                print(f"Inserted: {processed}")
            else:
                print("No speech detected")
        else:
            self.popup.hide()
                
    def run(self):
        print("VoiceType started.")
        print("Press Ctrl+C to quit.")
        
        self.socket = SocketListener(self.toggle_recording)
        self.socket.start()
        
        GLib.timeout_add(100, self._check_quit)
        
        if self.tray.start():
            Gtk.main()
        else:
            print("System tray not available. Running in console mode.")
            try:
                Gtk.main()
            except KeyboardInterrupt:
                self.quit()
                
    def _check_quit(self):
        if not self._running:
            Gtk.main_quit()
            return False
        return True
        
    def quit(self):
        self._running = False
        if self.is_recording:
            self.recorder.stop_recording()
        sys.exit(0)


def main():
    app = VoiceType()
    app.run()


if __name__ == "__main__":
    main()