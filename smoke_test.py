#!/usr/bin/env python3
"""
Smoke test for VoiceType installation and auto-start functionality.
"""
import sys
import os
import subprocess
import tempfile
from pathlib import Path

def check_python_version():
    """Check Python version."""
    print("✓ Python version: " + sys.version.split()[0])
    return sys.version_info >= (3, 10)

def check_imports():
    """Check that required imports work."""
    imports = [
        'numpy',
        'sounddevice',
        'pyperclip',
        'yaml',
        'gi',
    ]
    
    print("Checking imports...")
    for import_name in imports:
        try:
            __import__(import_name)
            print(f"  ✓ {import_name}")
        except ImportError as e:
            print(f"  ✗ {import_name}: {e}")
            return False
    
    # Check gi versions
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        gi.require_version('Gdk', '3.0')
        gi.require_version('GLib', '2.0')
        from gi.repository import Gtk, GLib, Gdk
        print("  ✓ GTK 3.0 available")
    except Exception as e:
        print(f"  ✗ GTK: {e}")
        return False
    
    return True

def check_config():
    """Check configuration files."""
    print("Checking configuration...")
    
    config_dir = Path.home() / ".config" / "voicetype"
    config_file = config_dir / "config.yaml"
    
    if config_dir.exists():
        print(f"  ✓ Config directory: {config_dir}")
    else:
        print(f"  ⚠ Config directory missing: {config_dir}")
    
    if config_file.exists():
        print(f"  ✓ Config file: {config_file}")
        # Try to read it
        try:
            import yaml
            with open(config_file) as f:
                data = yaml.safe_load(f)
            print(f"  ✓ Config file is valid YAML")
        except Exception as e:
            print(f"  ✗ Config file error: {e}")
            return False
    else:
        print(f"  ⚠ Config file missing: {config_file}")
    
    return True

def check_wrapper_script():
    """Check wrapper script."""
    print("Checking wrapper script...")
    
    script_path = Path(__file__).parent / "voicetype-toggle.sh"
    
    if not script_path.exists():
        print(f"  ✗ Wrapper script not found: {script_path}")
        return False
    
    print(f"  ✓ Wrapper script exists: {script_path}")
    
    # Check if executable
    if os.access(script_path, os.X_OK):
        print(f"  ✓ Wrapper script is executable")
    else:
        print(f"  ⚠ Wrapper script is not executable (run: chmod +x {script_path})")
    
    # Check script content
    try:
        with open(script_path) as f:
            content = f.read()
        if "--auto-record" in content:
            print(f"  ✓ Wrapper script uses --auto-record flag")
        else:
            print(f"  ⚠ Wrapper script doesn't use --auto-record flag")
        
        if "voicetype.sock" in content:
            print(f"  ✓ Wrapper script uses correct socket path")
        else:
            print(f"  ⚠ Wrapper script doesn't reference voicetype.sock")
    except Exception as e:
        print(f"  ⚠ Could not read wrapper script: {e}")
    
    return True

def check_socket_path():
    """Check socket path configuration."""
    print("Checking socket configuration...")
    
    sock_path = Path(tempfile.gettempdir()) / "voicetype.sock"
    print(f"  ✓ Socket path: {sock_path}")
    
    # Check if socket file exists (might be from a running instance)
    if sock_path.exists():
        print(f"  ⚠ Socket file exists (VoiceType might be running)")
    
    return True

def check_command_line():
    """Check command line interface."""
    print("Checking command line interface...")
    
    script_path = Path(__file__).parent / "src" / "voicetype.py"
    
    if not script_path.exists():
        print(f"  ✗ Main script not found: {script_path}")
        return False
    
    print(f"  ✓ Main script exists: {script_path}")
    
    # Test --help flag
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"  ✓ --help flag works")
            if "--auto-record" in result.stdout:
                print(f"  ✓ --auto-record flag documented")
            else:
                print(f"  ⚠ --auto-record flag not in help")
        else:
            print(f"  ✗ --help failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ⚠ Could not run --help: {e}")
    
    return True

def check_hyprland_binding():
    """Check Hyprland binding configuration."""
    print("Checking Hyprland binding...")
    
    hypr_config = Path.home() / ".config" / "hypr" / "hyprland.conf"
    
    if not hypr_config.exists():
        print(f"  ⚠ Hyprland config not found: {hypr_config}")
        return True  # Not critical if user doesn't use Hyprland
    
    try:
        with open(hypr_config) as f:
            content = f.read()
        
        wrapper_path = Path(__file__).parent / "voicetype-toggle.sh"
        wrapper_str = str(wrapper_path)
        
        if "voicetype-toggle.sh" in content:
            print(f"  ✓ Hyprland config references voicetype-toggle.sh")
            
            # Check if path is correct
            if wrapper_str in content:
                print(f"  ✓ Hyprland binding has correct path")
            else:
                print(f"  ⚠ Hyprland binding path might need updating")
                print(f"    Current path in config should be: {wrapper_str}")
        elif "voicetype.sock" in content:
            print(f"  ⚠ Hyprland config uses old socket binding (update to wrapper script)")
        else:
            print(f"  ⚠ Hyprland config doesn't have VoiceType binding")
    except Exception as e:
        print(f"  ⚠ Could not check Hyprland config: {e}")
    
    return True

def main():
    """Run all checks."""
    print("=" * 60)
    print("VoiceType Installation and Auto-Start Test")
    print("=" * 60)
    
    tests = [
        ("Python version", check_python_version),
        ("Imports", check_imports),
        ("Configuration", check_config),
        ("Wrapper script", check_wrapper_script),
        ("Socket path", check_socket_path),
        ("Command line", check_command_line),
        ("Hyprland binding", check_hyprland_binding),
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
            print(f"  ✗ Test failed with exception: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("SUCCESS: All checks passed!")
        print("\nAuto-start functionality should work correctly.")
        print("Press your hotkey (default: SUPER + I) to test.")
        return 0
    else:
        print("ISSUES: Some checks failed.")
        print("\nPlease fix the issues above before testing auto-start.")
        return 1

if __name__ == "__main__":
    sys.exit(main())