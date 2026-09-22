# System Monitoring & Endpoint Telemetry Framework 🛰️

<p align="center">
  <img src="https://img.shields.io/badge/Author-Avi-blueviolet?style=for-the-badge&logo=github" alt="Author Avi">
  <img src="https://img.shields.io/badge/Python-3.10%2B-cyan?style=for-the-badge&logo=python" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Architecture-Client--Server%20Telemetry-emerald?style=for-the-badge&logo=flask" alt="Architecture">
  <img src="https://img.shields.io/badge/License-MIT-orange?style=for-the-badge" alt="MIT License">
  <img src="https://img.shields.io/badge/Focus-Educational%20%26%20Research-blue?style=for-the-badge" alt="Educational Focus">
</p>

---

## 📚 Academic & Educational Statement

> **NOTICE:**  
> This repository contains an **educational research framework** designed to demonstrate the fundamentals of **operating system event handling**, **endpoint telemetry collection**, **defensive Data Loss Prevention (DLP)**, and **secure client-server web architecture**.
>
> It is developed strictly for **academic study**, **systems administration training**, and **authorized research in controlled laboratory environments**.

---

## 🎯 Research & Learning Objectives

This project explores key engineering and security concepts:

1. **OS-Level Event Observation:** Demonstrates how low-level Windows APIs (`SetWindowsHookEx`, `win32gui`, clipboard APIs) interact with user-space applications to track active window contexts and user input.
2. **Endpoint Telemetry & Diagnostics:** Illustrates continuous gathering of system health metrics (CPU utilization, virtual memory allocation, disk capacity, process trees, and network sockets).
3. **Data Loss Prevention (DLP) Pattern Matching:** Implements an asynchronous queue-based regular expression engine to detect sensitive data patterns in active text streams.
4. **Productivity & Time Accounting:** Uses time-tracking heuristics and browser tab context analysis to generate visual analytics with Chart.js.
5. **Secure Telemetry Pipeline:** Implements secure communication paradigms including cryptographic token validation (`X-Agent-Token`), Scrypt password hashing, sliding-window IP rate limiting, and AES-256 encryption at rest.

---

## 🌟 Architecture Overview

```
                        ┌─────────────────────────────────┐
                        │    Remote Endpoint Node(s)      │
                        │                                 │
                        │  - OS Input & Window Tracker    │
                        │  - System Resource Monitor      │
                        │  - Screen/Media Diagnostic Grab │
                        │  - Client Ingestion Daemon      │
                        └────────────────┬────────────────┘
                                         │
                                         │  HTTP / Token Auth
                                         ▼
                        ┌─────────────────────────────────┐
                        │      Central Telemetry Hub      │
                        │                                 │
                        │  - REST Ingestion API           │
                        │  - Automated Health Analyzer    │
                        │  - DLP Text Scanning Engine     │
                        │  - Web Analytics Dashboard      │
                        └─────────────────────────────────┘
```

---

## 📁 Repository Structure

```
.
├── main.py                  # Telemetry server & engine entry point
├── logger_engine.py         # Multi-threaded OS event capture engine
├── activity_tracker.py      # Window resolution and time tracking module
├── dlp_scanner.py           # Async DLP regex inspection engine
├── dashboard.py             # Flask telemetry API & security middleware
├── config.json              # Server configuration and thresholds
├── requirements.txt         # Python dependency definitions
├── README.md                # Project documentation
├── LICENSE                  # MIT License (Author: Avi)
│
├── agent/                   # Standalone Endpoint Client
│   ├── telemetry_agent.py   # Multi-threaded client collector daemon
│   ├── agent_config.json    # Endpoint target settings
│   ├── run_agent.bat        # Windows launcher script
│   └── README.md            # Client deployment guide
│
├── Cryptography/            # Cryptographic Utilities
│   ├── GenerateKey.py       # AES key generation utility
│   └── DecryptFile.py       # Log decryption utility
│
├── static/                  # Web Interface Assets (CSS, JS)
│   ├── css/style.css
│   └── js/dashboard.js
│
└── templates/               # Web Interface Templates
    ├── index.html           # Main Telemetry Dashboard
    └── login.html           # Authentication Portal
```

---

## 🚀 Getting Started (Lab Setup)

### 1. Prerequisites
* Python 3.10 or higher installed on your system.

### 2. Installation
```bash
git clone https://github.com/AVII-VERSE/system-monitoring-suite.git
cd system-monitoring-suite
pip install -r requirements.txt
```

### 3. Running the Telemetry Hub
```bash
python main.py
```
Open your browser and navigate to `http://127.0.0.1:5000`:
* **Default Username:** `admin`
* **Default Password:** `admin123`

### 4. Running a Client Node
On a test endpoint within your lab network:
1. Copy the `agent/` folder.
2. Edit `agent/agent_config.json` to point to your hub's IP address.
3. Run `python telemetry_agent.py` or double-click `run_agent.bat`.

---

## ⚖️ Legal & Ethical Usage

This software is provided for educational and administrative research only. Users are responsible for ensuring compliance with all applicable local, state, national, and international cybersecurity laws (such as CFAA, IT Act, and GDPR). Unauthorized monitoring without explicit consent is strictly prohibited.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.  
**Copyright (c) 2026 Avi**
