"""
===================================================================
Project: DarkWatch Telemetry & Productivity Suite
Module:  Activity & Window Tracker (pywin32 + psutil)
Description: Background worker to monitor active foreground window,
             extract browser tab titles, compute time spent per
             application, and prepare data for Chart.js.
===================================================================
"""

import sys
import time
import re
import threading
from datetime import datetime

IS_WINDOWS = sys.platform.startswith("win")

if IS_WINDOWS:
    try:
        import win32gui
        import win32process
    except ImportError:
        win32gui = None
        win32process = None
else:
    win32gui = None
    win32process = None

try:
    import psutil
except ImportError:
    psutil = None


class WindowActivityTracker:
    """
    Tracks foreground window activity, calculates time per process/app,
    and logs tab/window timeline in a thread-safe manner.
    """

    KNOWN_BROWSERS = {
        "chrome.exe": "Google Chrome",
        "msedge.exe": "Microsoft Edge",
        "brave.exe": "Brave Browser",
        "firefox.exe": "Mozilla Firefox",
        "opera.exe": "Opera",
        "vivaldi.exe": "Vivaldi"
    }

    # Regex patterns to strip standard browser title suffixes
    BROWSER_SUFFIX_REGEX = re.compile(
        r'\s*[-—]\s*(?:(?:Google\s+)?Chrome|(?:Personal\s+[-—]\s*)?(?:Microsoft\s+)?Edge|Brave(?: Browser)?|Mozilla\s+Firefox|Opera|Vivaldi).*$',
        re.IGNORECASE
    )

    def __init__(self, poll_interval=1.0, max_timeline_entries=200):
        self.poll_interval = max(0.2, float(poll_interval))
        self.max_timeline_entries = max_timeline_entries

        self.lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None

        # Cumulative time spent per executable (in seconds)
        # Format: {'chrome.exe': 3600, 'code.exe': 7200}
        self.app_usage_seconds = {}

        # Activity timeline list
        # Format: [{'timestamp': '...', 'app': 'chrome.exe', 'title': '...', 'tab': '...', 'duration': 45.2}]
        self.timeline = []

        # Current active state
        self.current_app = "Idle / None"
        self.current_title = "Desktop"
        self.current_tab = ""

    def parse_browser_tab(self, exe_name: str, window_title: str) -> str:
        """
        Extract clean tab/page name from browser window titles.
        Example: 'GitHub: Let’s build from here - Google Chrome' -> 'GitHub: Let’s build from here'
        """
        if not window_title:
            return ""

        exe_lower = exe_name.lower()
        if exe_lower in self.KNOWN_BROWSERS:
            # Strip standard browser suffix
            cleaned = self.BROWSER_SUFFIX_REGEX.sub("", window_title).strip()
            # If nothing left, return the original title
            return cleaned if cleaned else window_title
        return window_title

    @staticmethod
    def attach_to_interactive_desktop():
        """
        Ensures thread has access to the interactive desktop (WinSta0\\Default).
        Critical for Windows background services, scheduled tasks, and subshells.
        """
        if not IS_WINDOWS:
            return False
        try:
            import ctypes
            user32 = ctypes.windll.user32
            h_winsta = user32.OpenWindowStationW("WinSta0", False, 0x037F)
            if h_winsta:
                user32.SetProcessWindowStation(h_winsta)
            h_desk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if h_desk:
                user32.SetThreadDesktop(h_desk)
            return True
        except Exception:
            return False

    def get_foreground_window_info(self):
        """
        Queries the OS for current foreground window title and executable name.
        Uses win32gui and win32process with psutil fallback.
        """
        if not IS_WINDOWS or not win32gui or not win32process:
            return "system.exe", "Desktop / Non-Windows Environment"

        try:
            hwnd = win32gui.GetForegroundWindow()
            # If handle is 0, attempt desktop attachment and retry
            if not hwnd or hwnd == 0:
                self.attach_to_interactive_desktop()
                hwnd = win32gui.GetForegroundWindow()

            if not hwnd or hwnd == 0:
                return "idle.exe", "Desktop / Screen Saver"

            # 1. Capture exact window title string
            title = win32gui.GetWindowText(hwnd)
            if not title or not title.strip():
                title = "Desktop / Background Task"
            else:
                title = title.strip()

            # 2. Get process PID via win32process
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid <= 0:
                return "system.exe", title

            # 3. Resolve PID to executable name
            exe_name = "unknown.exe"
            if psutil:
                try:
                    proc = psutil.Process(pid)
                    exe_name = proc.name().lower()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    exe_name = f"proc_{pid}.exe"

            return exe_name, title

        except Exception as e:
            return "unknown.exe", f"Error: {e}"

    def _worker(self):
        """
        Background telemetry thread loop.
        Monitors active window, accumulates duration, and records timeline.
        """
        self.attach_to_interactive_desktop()
        last_time = time.time()
        last_exe = None
        last_title = None
        current_segment_start = last_time

        while not self._stop_event.is_set():
            current_time = time.time()
            delta = current_time - last_time
            last_time = current_time

            # Query current active foreground application
            exe_name, title = self.get_foreground_window_info()
            parsed_tab = self.parse_browser_tab(exe_name, title)

            with self.lock:
                # Update current instantaneous state
                self.current_app = exe_name
                self.current_title = title
                self.current_tab = parsed_tab

                # Accumulate time for previous app
                if last_exe:
                    self.app_usage_seconds[last_exe] = round(
                        self.app_usage_seconds.get(last_exe, 0.0) + delta, 1
                    )

                # Check if user switched window or application
                if exe_name != last_exe or title != last_title:
                    # Log the segment that just finished if it had meaningful duration (>0.5s)
                    segment_duration = round(current_time - current_segment_start, 1)
                    if last_exe and segment_duration >= 0.5:
                        self.timeline.insert(0, {
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "app": last_exe,
                            "title": last_title or "Unknown",
                            "tab": self.parse_browser_tab(last_exe, last_title or ""),
                            "duration_seconds": segment_duration
                        })
                        # Trim timeline to limit memory
                        if len(self.timeline) > self.max_timeline_entries:
                            self.timeline.pop()

                    current_segment_start = current_time
                    last_exe = exe_name
                    last_title = title

            # Wait for next poll interval or stop event
            self._stop_event.wait(timeout=self.poll_interval)

    def start(self):
        """Launch tracking thread in background."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, name="WindowActivityTrackerThread", daemon=True)
        self._thread.start()
        print("[*] WindowActivityTracker background worker started.")

    def stop(self):
        """Signal background thread to stop cleanly."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        print("[*] WindowActivityTracker background worker stopped.")

    def get_app_usage(self) -> dict:
        """
        Thread-safe getter for raw time spent dictionary.
        Returns: {'chrome.exe': 3600, 'code.exe': 7200, ...}
        """
        with self.lock:
            return dict(self.app_usage_seconds)

    def get_timeline(self, limit=30) -> list:
        """Thread-safe getter for recent window activity timeline."""
        with self.lock:
            return list(self.timeline[:limit])

    def get_current_focus(self) -> dict:
        """Returns the current foreground window details."""
        with self.lock:
            return {
                "app": self.current_app,
                "title": self.current_title,
                "tab": self.current_tab
            }

    def get_chartjs_payload(self, top_n=8) -> dict:
        """
        Prepares a ready-to-render payload formatted specifically for Chart.js.
        Converts seconds to minutes/hours for clear visual representation.
        """
        with self.lock:
            sorted_apps = sorted(self.app_usage_seconds.items(), key=lambda item: item[1], reverse=True)

        top_apps = sorted_apps[:top_n]
        remaining = sorted_apps[top_n:]

        labels = [app for app, _ in top_apps]
        max_sec = max([s for _, s in top_apps], default=0)
        use_seconds = max_sec < 180

        if use_seconds:
            unit_label = "Time Spent (Seconds)"
            data = [round(seconds, 1) for _, seconds in top_apps]
        else:
            unit_label = "Time Spent (Minutes)"
            data = [round(seconds / 60.0, 1) for _, seconds in top_apps]

        if remaining:
            other_seconds = sum(s for _, s in remaining)
            labels.append("other")
            data.append(round(other_seconds if use_seconds else other_seconds / 60.0, 1))

        return {
            "labels": labels,
            "unit": "s" if use_seconds else "m",
            "datasets": [
                {
                    "label": unit_label,
                    "data": data,
                    "backgroundColor": [
                        "rgba(14, 165, 233, 0.75)",   # Sky Blue
                        "rgba(56, 189, 248, 0.75)",   # Light Sky
                        "rgba(2, 132, 199, 0.75)",    # Darker Sky
                        "rgba(99, 102, 241, 0.75)",   # Indigo
                        "rgba(168, 85, 247, 0.75)",   # Purple
                        "rgba(236, 72, 153, 0.75)",   # Pink
                        "rgba(20, 184, 166, 0.75)",   # Teal
                        "rgba(245, 158, 11, 0.75)",   # Amber
                        "rgba(148, 163, 184, 0.75)"   # Slate (other)
                    ],
                    "borderColor": "rgba(255, 255, 255, 0.15)",
                    "borderWidth": 1
                }
            ]
        }


# Singleton instance for modular application import
activity_tracker = WindowActivityTracker()


if __name__ == "__main__":
    # Self-test loop demonstration
    print("Testing WindowActivityTracker for 10 seconds...")
    activity_tracker.start()

    for i in range(10):
        time.sleep(1)
        focus = activity_tracker.get_current_focus()
        print(f"[{i+1}s] App: {focus['app']} | Tab/Title: {focus['tab'] or focus['title']}")

    activity_tracker.stop()
    print("\n--- Final App Usage (Seconds) ---")
    print(activity_tracker.get_app_usage())
    print("\n--- Chart.js Payload ---")
    print(activity_tracker.get_chartjs_payload())
