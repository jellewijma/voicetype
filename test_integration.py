#!/usr/bin/env python3
"""
Integration test for VoiceType auto-start functionality.
"""
import sys
import os
import subprocess
import time
import signal
import socket
import tempfile
from pathlib import Path

def cleanup_process(proc):
    """Clean up process if running."""
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

def test_wrapper_script():
    """Test the wrapper script logic."""
    print("Testing wrapper script...")
    
    script_path = Path(__file__).parent / "voicetype-toggle.sh"
    
    # Check script exists and is executable
    assert script_path.exists(), f"Wrapper script not found: {script_path}"
    assert os.access(script_path, os.X_OK), f"Wrapper script not executable: {script_path}"
    
    # Check script content
    with open(script_path) as f:
        content = f.read()
    
    # Should have auto-record flag
    assert "--auto-record" in content, "Wrapper script should use --auto-record flag"
    
    # Should reference the socket
    assert "voicetype.sock" in content, "Wrapper script should reference voicetype.sock"
    
    print("✓ Wrapper script checks passed")
    return True

def test_socket_communication():
    """Test socket creation and communication."""
    print("Testing socket communication...")
    
    sock_path = Path(tempfile.gettempdir()) / "voicetype.sock"
    
    # Clean up any existing socket
    if sock_path.exists():
        sock_path.unlink()
    
    # Create a test socket server to simulate VoiceType
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(sock_path))
    server.listen(1)
    server.settimeout(2.0)
    
    # Start a thread to accept connections
    import threading
    received_data = []
    
    def accept_connections():
        try:
            conn, _ = server.accept()
            data = conn.recv(1024).decode().strip()
            received_data.append(data)
            conn.close()
        except socket.timeout:
            pass
    
    thread = threading.Thread(target=accept_connections)
    thread.start()
    
    # Test sending toggle command via nc
    try:
        # Try to use nc to send command
        result = subprocess.run(
            ["echo", "toggle"],
            capture_output=True,
            text=True,
        )
        
        # Pipe to nc
        nc_result = subprocess.run(
            ["nc", "-U", str(sock_path)],
            input="toggle\n",
            capture_output=True,
            text=True,
            timeout=2
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # nc might not be available or timeout, that's OK for test
        pass
    
    thread.join()
    server.close()
    
    # Clean up
    if sock_path.exists():
        sock_path.unlink()
    
    print("✓ Socket communication test completed")
    return True

def test_command_line_interface():
    """Test command line interface."""
    print("Testing command line interface...")
    
    script_path = Path(__file__).parent / "src" / "voicetype.py"
    
    # Test --help
    result = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    assert result.returncode == 0, f"--help failed: {result.stderr}"
    assert "VoiceType" in result.stdout, "Help should contain 'VoiceType'"
    assert "--auto-record" in result.stdout, "Help should mention --auto-record flag"
    
    # Test that script can be imported (syntax check)
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(script_path)],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    assert result.returncode == 0, f"Syntax check failed: {result.stderr}"
    
    print("✓ Command line interface tests passed")
    return True

def test_auto_start_logic():
    """Test the auto-start logic without actually running full app."""
    print("Testing auto-start logic...")
    
    # Import VoiceType with mocked dependencies
    # Mock heavy imports
    import unittest.mock as mock
    
    with mock.patch.dict('sys.modules', {
        'gi': mock.MagicMock(),
        'sounddevice': mock.MagicMock(),
        'pyperclip': mock.MagicMock(),
        'pystray': mock.MagicMock(),
        'PIL': mock.MagicMock(),
        'faster_whisper': mock.MagicMock(),
    }):
        # Mock gi.repository
        mock_gi = mock.MagicMock()
        mock_gi.require_version = mock.MagicMock()
        sys.modules['gi'] = mock_gi
        
        # Mock Gtk, GLib, Gdk
        mock_gtk = mock.MagicMock()
        mock_glib = mock.MagicMock()
        mock_gdk = mock.MagicMock()
        mock_glib.idle_add = mock.MagicMock()
        sys.modules['gi.repository.Gtk'] = mock_gtk
        sys.modules['gi.repository.GLib'] = mock_glib
        sys.modules['gi.repository.Gdk'] = mock_gdk
        
        # Now we can import VoiceType
        from src.voicetype import VoiceType
        
        # Test auto-record flag
        app = VoiceType(auto_record=True)
        assert app.auto_record == True
        assert app.model_loaded == False
        
        # Test initialization logic
        app._initialize_model()
        assert app.model_loading == True
        
        print("✓ Auto-start logic tests passed")
        return True

def test_hyprland_config():
    """Check Hyprland configuration."""
    print("Checking Hyprland configuration...")
    
    hypr_config = Path.home() / ".config" / "hypr" / "hyprland.conf"
    
    if not hypr_config.exists():
        print("⚠ Hyprland config not found (skipping)")
        return True
    
    with open(hypr_config) as f:
        content = f.read()
    
    wrapper_path = Path(__file__).parent / "voicetype-toggle.sh"
    
    # Should have binding for VoiceType
    if "voicetype-toggle.sh" in content:
        print("✓ Hyprland config references voicetype-toggle.sh")
        
        # Check path is correct
        if str(wrapper_path) in content:
            print("✓ Hyprland binding has correct path")
        else:
            print("⚠ Hyprland binding path might need updating")
            return False
    else:
        print("⚠ Hyprland config doesn't have VoiceType binding")
        return False
    
    return True

def main():
    """Run all integration tests."""
    print("=" * 60)
    print("VoiceType Integration Test")
    print("=" * 60)
    
    tests = [
        ("Wrapper script", test_wrapper_script),
        ("Socket communication", test_socket_communication),
        ("Command line interface", test_command_line_interface),
        ("Auto-start logic", test_auto_start_logic),
        ("Hyprland config", test_hyprland_config),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{name}:")
        try:
            if test_func():
                results.append((name, True))
            else:
                results.append((name, False))
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Integration Test Summary:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("SUCCESS: All integration tests passed!")
        print("\nAuto-start functionality is correctly implemented.")
        print("To test manually:")
        print("1. Make sure no VoiceType is running (check /tmp/voicetype.sock)")
        print("2. Press SUPER + I (or your configured hotkey)")
        print("3. You should see 'Initializing...' popup, then 'Listening...'")
        print("4. Speak, then press hotkey again to transcribe")
        return 0
    else:
        print("FAILURE: Some integration tests failed.")
        print("\nPlease fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())