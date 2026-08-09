# 🛡️ System Monitoring Suite

<p align="center">
  <b>Multi-Threaded System Monitoring & Security Telemetry Platform</b>
  <br/>
  Python • Flask • Windows API • REST • Cryptography
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python">
  <img src="https://img.shields.io/badge/Flask-Web%20Dashboard-black?style=for-the-badge&logo=flask">
  <img src="https://img.shields.io/badge/Platform-Windows-informational?style=for-the-badge&logo=windows">
  <img src="https://img.shields.io/badge/Security-Fernet%20Encryption-success?style=for-the-badge">
</p>

---

## ✦ About

**System Monitoring Suite** is a modular Python application that combines a **multi-threaded monitoring engine** with a **Flask-powered web dashboard** for centralized activity visualization, system telemetry, logging, and secure local data handling.

## ⚡ Features

| Feature | Description |
|---|---|
| 🖥️ Dashboard | Real-time monitoring through a modern Flask web interface |
| ⚙️ Multi-Threading | Independent background monitoring workers |
| 🪟 Windows Tracking | Active application and system context monitoring |
| ⌨️ Event Logging | Keyboard and clipboard event processing |
| 📸 Media Capture | Screen and camera capture support |
| 🎙️ Audio | Configurable audio recording |
| 🔐 Encryption | Fernet-based secure local log storage |
| 🔌 REST API | Backend APIs for dashboard communication |
| 🛠️ Configuration | Centralized `config.json` settings |

## 🏗️ Architecture

```text
                 ┌─────────────────────┐
                 │       main.py       │
                 └──────────┬──────────┘
                            │
             ┌──────────────┴──────────────┐
             ▼                             ▼
   ┌──────────────────┐          ┌──────────────────┐
   │ Monitoring Engine│          │ Flask Dashboard  │
   │ logger_engine.py │          │  dashboard.py    │
   └────────┬─────────┘          └────────┬─────────┘
            │                             │
            ▼                             ▼
     System Telemetry                REST API
            │                             │
            └──────────┬──────────────────┘
                       ▼
                Centralized Logs
                       │
                       ▼
                🔐 Encryption
---

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Suite
```bash
python main.py
```

### 3. Open Web Dashboard
Navigate to `http://127.0.0.1:5000` in your web browser to view live keystroke logs, screenshot galleries, and trigger instant snapshots.

---

## 🔐 Cryptography Utilities

To encrypt generated logs manually or via script:
```bash
python Cryptography/GenerateKey.py
```

To decrypt stored logs:
```bash
python Cryptography/DecryptFile.py
```

---

## ⚠️ Disclaimer

*This software is created by **Avi** for educational, security research, and authorized administrative monitoring purposes only. Using this tool to monitor devices without prior explicit consent is strictly prohibited.*

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.  
**Copyright (c) 2026 Avi**
