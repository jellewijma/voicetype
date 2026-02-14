#!/usr/bin/env python3
"""
Run all VoiceType tests.
"""
import sys
import os
import subprocess
import argparse

def run_test(test_file, description):
    """Run a test file and return success."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"{'='*60}")
    
    try:
        # Run the test
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print(f"✓ {description} passed")
            return True
        else:
            print(f"✗ {description} failed (exit code: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"✗ {description} timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"✗ {description} failed with exception: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run VoiceType tests")
    parser.add_argument("--skip-smoke", action="store_true", help="Skip smoke test")
    parser.add_argument("--skip-init", action="store_true", help="Skip initialization test")
    parser.add_argument("--skip-all", action="store_true", help="Skip all tests and show summary only")
    args = parser.parse_args()
    
    tests = []
    
    if not args.skip_all:
        if not args.skip_init:
            tests.append(("test_initialization.py", "Initialization tests"))
        
        if not args.skip_smoke:
            tests.append(("smoke_test.py", "Smoke test (installation check)"))
    
    if not tests:
        print("No tests to run (all skipped)")
        return 0
    
    print("VoiceType Test Suite")
    print("=" * 60)
    
    results = []
    for test_file, description in tests:
        success = run_test(test_file, description)
        results.append((description, success))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    
    all_passed = True
    for description, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {description}")
        if not success:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("SUCCESS: All tests passed!")
        print("\nAuto-start functionality should work correctly.")
        print("To test manually:")
        print("1. Make sure VoiceType is not running (no socket at /tmp/voicetype.sock)")
        print("2. Press your hotkey (default: SUPER + I)")
        print("3. You should see 'Initializing...' popup, then 'Listening...'")
        print("4. Speak, then press hotkey again to transcribe")
        return 0
    else:
        print("FAILURE: Some tests failed.")
        print("\nPlease fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())