import re
import time
import queue
import threading
from dataclasses import dataclass, field
from typing import List, Set, Optional, Callable, Dict, Any

@dataclass
class DLPInspectionResult:
    id: int
    alert_triggered: bool
    matched_keywords: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: time.strftime('%H:%M:%S - %d %b'))
    source: str = 'Unknown'
    snippet: str = ''
    read: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class DLPScannerService:
    def __init__(
        self,
        keywords: Optional[Set[str]] = None,
        on_alert_callback: Optional[Callable[[DLPInspectionResult], None]] = None,
        worker_threads: int = 1
    ):
        self._keywords = set(keywords) if keywords else {'confidential', 'admin', 'password', 'secret', 'restricted'}
        self._pattern = self._compile_regex(self._keywords)
        self._on_alert_callback = on_alert_callback

        self._scan_queue: queue.Queue = queue.Queue(maxsize=10000)
        self._stop_event = threading.Event()
        self._workers: List[threading.Thread] = []

        self._lock = threading.Lock()
        self._counter = 0
        self._last_alert_time = 0
        self._last_alert_text = ''
        self.incident_history: List[DLPInspectionResult] = []

        self._start_workers(worker_threads)

    def _compile_regex(self, words: Set[str]) -> re.Pattern:
        if not words:
            return re.compile(r'(?!x)x')
        escaped_words = [re.escape(w.strip()) for w in words if w.strip()]
        # Substring/prefix matching so password123, admin_pass, etc. are all caught
        regex_pattern = r'(' + '|'.join(escaped_words) + r')'
        return re.compile(regex_pattern, re.IGNORECASE)

    def update_keywords(self, new_keywords: Set[str]):
        with self._lock:
            self._keywords = set(new_keywords)
            self._pattern = self._compile_regex(self._keywords)

    def get_keywords(self) -> List[str]:
        with self._lock:
            return sorted(list(self._keywords))

    def submit_text(self, text_buffer: str, source: str = 'Telemetry', metadata: Optional[dict] = None) -> bool:
        if not text_buffer or len(text_buffer.strip()) < 3:
            return False
        try:
            self._scan_queue.put_nowait((text_buffer, source, metadata or {}))
            return True
        except queue.Full:
            return False

    def _start_workers(self, num_workers: int):
        for i in range(num_workers):
            t = threading.Thread(target=self._worker_loop, name=f'DLP-Worker-{i+1}', daemon=True)
            t.start()
            self._workers.append(t)

    def _worker_loop(self):
        while not self._stop_event.is_set():
            try:
                text_buffer, source, metadata = self._scan_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                self._inspect_buffer(text_buffer, source, metadata)
            except Exception as e:
                print(f'[!] Error during DLP buffer inspection: {e}')
            finally:
                self._scan_queue.task_done()

    def _inspect_buffer(self, text: str, source: str, metadata: dict):
        with self._lock:
            pattern = self._pattern

        matches = pattern.findall(text)
        if matches:
            unique_matches = sorted(list({m.lower() for m in matches}))
            
            # Clean up keylogger markup for clean human-readable display in drawer
            clean_text = re.sub(r'\[[A-Z0-9_]+\]', ' ', text)
            clean_text = ' '.join(clean_text.split())
            if not clean_text:
                clean_text = text.strip()

            snippet = clean_text[:280].strip()
            if len(clean_text) > 280:
                snippet += '...'

            with self._lock:
                now_ts = time.time()
                # Debounce continuous keystrokes within 2.5s for same source
                if (now_ts - self._last_alert_time < 2.5) and self.incident_history:
                    last_inc = self.incident_history[-1]
                    if last_inc.source == source and set(last_inc.matched_keywords) == set(unique_matches):
                        # Update latest incident with fuller text
                        last_inc.snippet = snippet
                        self._last_alert_time = now_ts
                        self._last_alert_text = text
                        return

                self._counter += 1
                self._last_alert_time = now_ts
                self._last_alert_text = text

                result = DLPInspectionResult(
                    id=self._counter,
                    alert_triggered=True,
                    matched_keywords=unique_matches,
                    source=source,
                    snippet=snippet,
                    read=False,
                    metadata=metadata
                )

                self.incident_history.append(result)
                if len(self.incident_history) > 100:
                    self.incident_history.pop(0)

            print(f'[*] [DLP ALERT #{result.id}] Keywords: {result.matched_keywords} | Source: {result.source} | Context: "{result.snippet}"')
            self.capture_system_state(result)
            if self._on_alert_callback:
                try:
                    self._on_alert_callback(result)
                except Exception as cb_err:
                    print(f'[!] DLP alert callback error: {cb_err}')

    def capture_system_state(self, incident: DLPInspectionResult):
        pass

    def get_dashboard_alert_status(self) -> dict:
        with self._lock:
            unread_count = sum(1 for inc in self.incident_history if not inc.read)
            alerts = []
            for inc in reversed(self.incident_history[-35:]):
                alerts.append({
                    'id': inc.id,
                    'matched_keywords': inc.matched_keywords,
                    'timestamp': inc.timestamp,
                    'source': inc.source,
                    'snippet': inc.snippet,
                    'read': inc.read
                })
            return {
                'unread_count': unread_count,
                'total_alerts': len(self.incident_history),
                'alert_triggered': unread_count > 0,
                'alerts': alerts,
                'latest': alerts[0] if alerts else None
            }

    def mark_all_read(self):
        with self._lock:
            for inc in self.incident_history:
                inc.read = True

    def clear_alerts(self):
        with self._lock:
            self.incident_history.clear()

    def shutdown(self):
        self._stop_event.set()
        for t in self._workers:
            t.join(timeout=1.0)
