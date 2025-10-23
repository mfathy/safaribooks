#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sound Notification Module
Handles playing sound notifications when book downloads complete
"""

import os
import subprocess
import threading
from pathlib import Path
from typing import Optional


class SoundNotifier:
    """Handles sound notifications for download completion"""
    
    def __init__(self, enable_sound: bool = True, sound_file: Optional[str] = None):
        self.enable_sound = enable_sound
        self.sound_file = sound_file or self._get_default_sound_file()
        self._ensure_sound_file_exists()
    
    def _get_default_sound_file(self) -> str:
        """Get default sound file path"""
        # Try to use a system sound first
        system_sounds = [
            "/System/Library/Sounds/Glass.aiff",
            "/System/Library/Sounds/Ping.aiff", 
            "/System/Library/Sounds/Submarine.aiff",
            "/System/Library/Sounds/Blow.aiff"
        ]
        
        for sound in system_sounds:
            if os.path.exists(sound):
                return sound
        
        # If no system sound found, create a simple beep sound
        return self._create_beep_sound()
    
    def _create_beep_sound(self) -> str:
        """Create a simple beep sound file using sox (if available) or return None"""
        beep_file = "output/notification_beep.aiff"
        beep_path = Path(beep_file)
        beep_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not beep_path.exists():
            try:
                # Try to create a simple beep using sox
                subprocess.run([
                    "sox", "-n", str(beep_path), 
                    "synth", "0.5", "sine", "800", "vol", "0.3"
                ], check=True, capture_output=True)
                return str(beep_path)
            except (subprocess.CalledProcessError, FileNotFoundError):
                # sox not available, we'll use system beep instead
                return None
        
        return str(beep_path)
    
    def _ensure_sound_file_exists(self):
        """Ensure the sound file exists or disable sound if not"""
        if self.sound_file and not os.path.exists(self.sound_file):
            # Try to find an alternative
            self.sound_file = self._get_default_sound_file()
            if not self.sound_file or not os.path.exists(self.sound_file):
                self.enable_sound = False
    
    def play_notification(self):
        """Play sound notification (non-blocking)"""
        if not self.enable_sound:
            return
        
        # Play sound in a separate thread to avoid blocking
        def _play_sound():
            try:
                if self.sound_file and os.path.exists(self.sound_file):
                    # Use afplay (macOS native audio player)
                    subprocess.run([
                        "afplay", self.sound_file
                    ], check=False, capture_output=True)
                else:
                    # Fallback to system beep
                    print("\a", end="", flush=True)  # Terminal bell
            except Exception:
                # If all else fails, use terminal bell
                print("\a", end="", flush=True)
        
        # Run in background thread
        thread = threading.Thread(target=_play_sound, daemon=True)
        thread.start()
    
    def test_sound(self):
        """Test if sound notification works"""
        if not self.enable_sound:
            print("Sound notifications are disabled")
            return False
        
        print(f"Testing sound notification with: {self.sound_file}")
        self.play_notification()
        return True
