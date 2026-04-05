# YakSperm Analyzer HMI v2.0

## Overview
The **YakSperm Analyzer HMI** is a production-ready, touch-optimized Human-Machine Interface (HMI) built for a high-altitude yak semen analysis scientific instrument. Designed to seamlessly run on an NVIDIA Jetson Nano board in kiosk mode, this application offers a comprehensive diagnostic workflow integrating real-time deep learning computer vision, high-speed camera interfacing, and external hardware stage manipulation via ESP32.

With a clinical, light-toned professional aesthetic built on **PyQt6**, the interface guides the operator from temperature and slide setup all the way through a 3-stage morphological and motility diagnostic pipeline resulting in shareable reports.

## Key Technical Features
* **NVIDIA Jetson Native**: Built for embedded edge devices prioritizing lightweight rendering engines and headless hardware integrations.
* **3-Stage AI Diagnosis Pipeline** in `core/ai_pipeline.py`:
  1. **YOLOv11 Detection**: Robust cell tracking out of the box using high-efficiency nano/small YOLO weights.
  2. **UKF-SORT Tracker** in `core/tracker.py`: Unscented Kalman Filter object tracker optimized for biological cells, operating tightly with the YOLO inferences to track overlapping motility paths.
  3. **EfficientNet-V2 Morphology Validation**: Secondary classifier to analyze individual bounding box crops for morphological abnormalities.
* **Asynchronous Multi-threading**: The hardware interactions, UI, and video processing loops are deeply decoupled via PyQt Queues and distinct generic Python `ThreadPoolExecutors`/Threads (`core/camera_thread.py`).
* **Kiosk & Mock Mode Configs**: A heavily configurable environment testing methodology (via `utils/config.yaml` and `utils/mock_hardware.py`) ensuring you can run and iterate on standard development machines without physical microscopes or Jetson developer kits (`launch.sh --mock`).
* **PDF Report Generation**: Clinical grade automated reporting capability built directly into the UI workflow (`core/report_generator.py`).

## Directory Structure

```text
Project/
├── core/                  # Core Business Logic & AI Engines
│   ├── ai_pipeline.py     # Central YOLO + EfficientNet inference coordinator
│   ├── camera_thread.py   # High FPS async capture loop & downsampling algorithms
│   ├── report_generator.py# ReportLab based PDF document generation
│   ├── serial_handler.py  # Thread-safe UART communication wrapper
│   ├── state_machine.py   # Core logic tying AI states to HMI UI states
│   ├── tracker.py         # UKF-SORT object tracker
│   └── video_pipeline.py  # End-to-end stream parsing
├── models/                # Trained Neural Network weights
│   ├── best.pt            # YOLOv11 tracking weights
│   └── efficientnetv2_l_sperm_morphology2.pth # Morphology classification weights
├── reports/               # Auto-generated destination folder for clinical outputs (PDFs, metrics)
├── ui/                    # PyQt6 presentation layer
│   ├── main_window.py     # Main application frame
│   ├── styles.py          # Central stylesheet (Light-toned, clinical aesthetic)
│   └── screens/           # Individual HMI tabs and steps
│       ├── analysis_screen.py # Live feed bounding boxes & real-time metrics
│       ├── history_screen.py  # Past results & loadable reports
│       ├── results_screen.py  # End-of-run static summary viewer
│       ├── setup_screen.py    # ESP32 Temperature & stage preparation
│       └── splash_screen.py   # Boot loading screen
├── utils/                 # Configuration and utilities
│   ├── config.yaml        # Main application config map 
│   └── mock_hardware.py   # Dummy class interfaces for dev iteration
├── venv/                  # Python virtual environment (ignored in git)
├── .gitignore             # Standard python ignores
├── esp.py                 # Debug script to test Jetson to ESP32 UART communication natively
├── launch.sh              # Quick deployment bash launcher enforcing XCB QT plugins and virtual envs
├── main.py                # Main application entry point handling CLI arguments
└── requirements.txt       # Project python package bounds
```

## Running the Application

A convenience wrapper is provided via `launch.sh`, or you can invoke Python directly.

### 1. Mock Mode (Development)
For iterating on the UI, AI logic, and threading without connecting to a physical camera or an ESP32 micro-controller board, run mock-mode.
```bash
./launch.sh --mock
# OR
python main.py --mock
```

### 2. Normal Mode (Production)
Requires actual Jetson UART hardware pins to be configured. The software expects `/dev/ttyTHS1`.
```bash
./launch.sh
```

### 3. Kiosk Mode
Will force `PyQt6` into borderless fullscreen optimized for high-res touch screens.
```bash
./launch.sh --fullscreen
```

## System Requirements & Setup
See `requirements.txt` for exact Python version bounds. Primary pillars include:
* `PyQt6` (User Interface)
* `opencv-python-headless` (OpenCV optimized for headless compute / non-GUI conflicts)
* `torch` / `torchvision` (Neural network inference)
* `ultralytics` (YOLO pipelines)
* `pyserial` (Jetson/ESP32 UART serial lines)
* `reportlab` (Report Generation)

Before running, make sure to isolate dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## HMI v2.2 — PC Mode (`--pc`)

### What's New
Version 2.2 introduces **PC Mode**, a new launch mode that runs the full hardware + AI analysis pipeline on a standard **PC or laptop** (Windows / Linux) instead of the NVIDIA Jetson Nano.

| Mode | Flag | Serial Port | Camera | AI Pipeline | Use Case |
|------|------|-------------|--------|-------------|----------|
| Normal | *(none)* | `/dev/ttyTHS1` (Jetson UART) | Real | Real | Production on Jetson Nano |
| Mock | `--mock` | Simulated (`MockSerialPort`) | Simulated (`MockCamera`) | Simulated | UI/logic development — no hardware |
| **PC** | **`--pc`** | **Auto-detected** (USB-serial) | **Real** | **Real** | **Lab PC with USB-connected ESP32** |
| Kiosk | `--fullscreen` | *(per mode)* | *(per mode)* | *(per mode)* | Borderless fullscreen overlay |

### Running in PC Mode
```bash
# Auto-detect ESP32 serial port and use real camera + AI
./launch.sh --pc

# With verbose logging
./launch.sh --pc -v

# Combined with fullscreen
./launch.sh --pc --fullscreen

# Direct Python invocation
python main.py --pc
```

> **Note:** `--mock` and `--pc` are mutually exclusive. You cannot combine them.

### Serial Port Auto-Detection
In normal (Jetson) mode the ESP32 is accessed via the fixed hardware UART at `/dev/ttyTHS1`. On a PC or laptop the ESP32 is instead connected through a USB-to-serial adapter, which appears as a different device depending on the platform and chipset:

| Platform | Typical Port | Chipset Examples |
|----------|-------------|------------------|
| Linux | `/dev/ttyUSB0`, `/dev/ttyACM0` | CP2102, CH340, FTDI |
| Windows | `COM3`, `COM4`, … | CP2102, CH340, FTDI |

The new `utils/pc_serial.py` module performs automatic detection:
1. **pyserial enumeration** — scans all available COM/tty ports and matches against known ESP32 chipset keywords (CP210x, CH340, FTDI, Espressif, etc.).
2. **Glob fallback** (Linux) — if pyserial enumeration is unavailable, globs `/dev/ttyUSB*` and `/dev/ttyACM*`.
3. **Platform default** — falls back to `/dev/ttyUSB0` (Linux) or `COM3` (Windows).

The detected port is logged at startup and automatically injected into the runtime configuration, overriding the `serial.port` value from `config.yaml`.

### New & Modified Files

```text
utils/
└── pc_serial.py   [NEW]  — Serial port auto-detection utility for PC/laptop

Modified:
  main.py            — Added --pc CLI flag, mutually exclusive with --mock;
                       auto-detects serial port and injects into config
  ui/main_window.py  — Accepts pc_mode flag; shows blue "PC MODE" badge in
                       nav bar; displays detected port in setup screen
  launch.sh          — Updated usage docs and version banner
```

### How It Works (Architecture)

```text
┌─────────────────────────────────────────────┐
│                  main.py                    │
│  --pc flag → detect_serial_port()           │
│  config["serial"]["port"] = detected_port   │
│  MainWindow(mock=False, pc_mode=True)       │
└──────────────────┬──────────────────────────┘
                   │
     ┌─────────────┼─────────────┐
     ▼             ▼             ▼
 SerialHandler  CameraThread  AIPipeline
 (real serial)  (real OpenCV) (real YOLO +
  auto-detect    /dev/video0   UKF-SORT +
  USB port       via cv2       EfficientNet)
```

Everything downstream of `main.py` runs identically to normal (Jetson) mode — the **only** difference is which serial port path is used for ESP32 communication.
