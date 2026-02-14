#!/usr/bin/env python3
"""
Test VoiceType initialization and lazy loading.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.voicetype import VoiceType, Transcriber, Config

def test_transcriber_lazy_load():
    print("Testing Transcriber lazy loading...")
    config = Config()
    transcriber = Transcriber(config)
    assert transcriber.model is None
    assert transcriber.model_loaded == False
    transcriber.load_model()
    assert transcriber.model_loaded == True
    assert transcriber.model is not None
    print("✓ Transcriber lazy load works")

def test_voice_type_auto_record():
    print("Testing VoiceType auto-record initialization...")
    app = VoiceType(auto_record=True)
    assert app.auto_record == True
    assert app.model_loaded == False
    assert app.model_loading == False
    assert app.pending_toggle == False
    print("✓ VoiceType auto-record state correct")

def test_toggle_before_model():
    print("Testing toggle before model loaded...")
    app = VoiceType(auto_record=False)
    # Simulate toggle when model not loaded
    app.toggle_recording()
    assert app.model_loading == True or app.pending_toggle == True
    print("✓ Toggle before model sets pending state")

if __name__ == "__main__":
    try:
        test_transcriber_lazy_load()
        test_voice_type_auto_record()
        test_toggle_before_model()
        print("\nAll tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)