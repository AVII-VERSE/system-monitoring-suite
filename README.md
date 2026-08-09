# Advanced Keylogger & Intelligence Suite 🚀

<p align="center">
  <img src="https://img.shields.io/badge/Author-Avi-blueviolet?style=for-the-badge&logo=github" alt="Author Avi">
  <img src="https://img.shields.io/badge/Python-3.8%2B-cyan?style=for-the-badge&logo=python" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/Dashboard-Flask%20%2F%20Glassmorphism-emerald?style=for-the-badge&logo=flask" alt="Flask Dashboard">
  <img src="https://img.shields.io/badge/License-MIT-orange?style=for-the-badge" alt="MIT License">
</p>

---

## 🌟 Overview

**Advanced Keylogger & Intelligence Suite** is a next-generation, multi-threaded security and monitoring tool authored by **Avi**. Unlike standard basic keyloggers, this suite features a **Modern Glassmorphism Web Dashboard**, **Active Window Title Tracking**, **Silent WebCamera Snaps**, **Screen Capture**, **Microphone Audio Logging**, and **AES-256 Log Encryption**.

---

## ✨ Features

- 🖥️ **Modern Web Dashboard**: Real-time visual control panel running on `http://127.0.0.1:5000` with live keystroke log streams, screenshot galleries, audio playback, and system diagnostics.
- 🔤 **Active Window Keystroke Logging**: Automatically captures application context headers (e.g. `[Google Chrome]`, `[VS Code]`, `[Notepad]`) along with precise keystrokes.
- 📸 **Silent WebCamera Snaps**: Background webcam snapshots without opening disruptive GUI windows or popups.
- 🖼️ **Automated Screenshots**: High-resolution screen captures saved at configurable intervals.
- 🎙️ **Microphone Audio Recording**: Background audio recording saved in `.wav` format.
- 📋 **Clipboard Tracking**: Monitors system clipboard changes without duplicating text.
- 🔒 **AES-256 Log Encryption**: Built-in Fernet cryptography engine to encrypt sensitive log files.
- ⚙️ **Centralized JSON Config**: Simple `config.json` management for capture intervals, ports, and storage locations.

---

## 📁 Project Architecture

```
KeyLogger/
│── config.json              # Central configuration file
│── main.py                  # Suite entry point (Engine + Web Dashboard)
│── logger_engine.py         # Multi-threaded KeyLogger & Monitoring Engine
│── dashboard.py             # Flask Web Dashboard backend API
│── requirements.txt         # Dependency manifest
│── README.md                # Project documentation
│── LICENSE                  # MIT License (Author: Avi)
│── static/                  # Glassmorphism UI (CSS & JS)
│   ├── css/style.css
│   └── js/dashboard.js
│── templates/               # HTML Dashboard Template
│   └── index.html
└── Cryptography/
    ├── DecryptFile.py       # AES-256 Decryption utility
    └── GenerateKey.py       # Encryption key generator
```

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
