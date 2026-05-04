# YakSperm Analyzer HMI v2.0 by Debraj Roy 

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

---

## HMI v3 — Bug Fixes, Hardware Integration & ESP32 Module

### What's New
Version 3 addresses runtime stability bugs and documents the full hardware Bill of Materials for the thermal stage and slide mechanism.

### Bug Fixes

| # | Issue | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | **Cancel freezes UI** — Cancelling a video analysis leaves the viewport stuck on the last rendered frame | `_on_cancel()` stopped the pipeline but never cleared the viewport, progress bar, or metrics | Added `AnalysisScreen.reset_ui()` that clears the frozen frame and resets all widgets to defaults; `_on_cancel()` now also waits for the pipeline thread to exit and disconnects its signals |
| 2 | **Serial port defaults to COM1** — PC mode picks COM1 (legacy motherboard port) instead of COM3 (ESP32) | Generic fallback matched any port containing `"COM"`, and COM1 is enumerated before COM3 | Fallback now explicitly skips legacy COM1/COM2 ports |

### Hardware Components (Bill of Materials)

| Component | Specification | Key Parameters |
|-----------|--------------|----------------|
| **Heater** | Polyimide Film Heater | 20×20 mm, 10 Ω, 12 V, ~14.4 W, ~1.2 A |
| **MOSFET** | AO3414 N-Channel (SOT-23) | Vds: 20 V, Id: 2.3 A, Rds(on): 55 mΩ @ 4.5 V |
| **Gate Resistor** | 220 Ω, 0.25 W | Limits gate inrush current |
| **Gate Pull-down Resistor** | 10 kΩ, 0.25 W | Ensures MOSFET off at boot |
| **Temperature Sensor** | DS18B20 | 3.0–5.5 V, 9–12 bit (0.0625 °C), −55 °C to +125 °C |
| **Pull-up Resistor (DS18B20)** | 4.7 kΩ, 0.25 W | OneWire bus pull-up |
| **DC-DC Buck Converter** | LM2596 | Input: 6–24 V, Output: adjustable (set to 5 V), ≥ 3 A |
| **Power Supply** | 12 V DC adapter | ≥ 2 A (recommended 3 A) |
| **Microcontroller** | ESP32 Dev Module | 3.3 V logic, Wi-Fi + BLE |
| **Servo Motor** | SG90 / MG90S | 5 V, up to ~700 mA (peak) |
| **Wiring** | Jumper wires / connectors | Rated ≥ 2 A for heater path |

### ESP32 Development Module

The `esp32DevModule/` directory contains trial Arduino sketches for the ESP32:

```text
esp32DevModule/
└── sketch_apr2a.ino   — DS18B20 temperature sensor test sketch
                         Uses OneWire + DallasTemperature libraries
                         GPIO 4 data pin, 115200 baud serial output
```

### New & Modified Files

```text
Modified:
  ui/screens/analysis_screen.py  — Added reset_ui() method to clear frozen
                                    viewport, progress bar, and metrics on cancel
  ui/main_window.py              — _on_cancel() now waits for pipeline thread,
                                    disconnects signals, and calls reset_ui()
  utils/pc_serial.py             — Fallback port detection skips legacy COM1/COM2
                                    ports on Windows
```

---

## HMI v3.1 — Production ESP32 Firmware & Wi-Fi PDF Sharing

### What's New
Version 3.1 introduces the fully functional production firmware for the ESP32 Development Module, replacing the simple trial sketch. This firmware actively controls the thermal stage, servo slide mechanism, and creates a local Wi-Fi network for mobile PDF report sharing.

### Firmware Details
The firmware is located at `esp32DevModule/esp32_firmware/esp32_firmware.ino` and handles:

1. **JSON Serial Protocol**: Communicates with the Jetson/PC via USB-Serial (115200 baud), parsing commands (`set_temp`, `heater_off`, `servo_move`, `ping`) and emitting periodic temperature status and acknowledgments.
2. **Thermal Stage PID/Bang-Bang**: Uses a DS18B20 sensor to read the slide temperature and controls the Polyimide Film Heater via an AO3414 MOSFET using a fast hysteresis loop.
3. **Servo Control**: Controls the SG90/MG90S slide-loading servo motor via PWM.
4. **Wi-Fi SoftAP**: Broadcasts a local Wi-Fi Access Point (SSID: `YakSperm_Analyzer_AP`, Password: `yakpassword`).

### ESP32 Pinout Guide
Based on the provided hardware BOM, the firmware expects the following default connections (can be changed in the `.ino` file):
- **GPIO 4**: DS18B20 Data pin (with 4.7kΩ pull-up to 3.3V/5V)
- **GPIO 18**: AO3414 MOSFET Gate (with 220Ω series resistor and 10kΩ pull-down to GND)
- **GPIO 19**: SG90 Servo PWM signal line

### Wi-Fi PDF Sharing Workflow
To seamlessly share generated PDF reports to mobile devices without requiring internet access:
1. The ESP32 broadcasts the `YakSperm_Analyzer_AP` Wi-Fi network.
2. The Jetson/PC running the HMI connects to this Wi-Fi network (if it has Wi-Fi), placing it on the same local network as the ESP32.
3. When a report is generated, the HMI creates a local web server and displays a QR code containing the PC's local IP address.
4. The user connects their smartphone to the `YakSperm_Analyzer_AP` Wi-Fi.
5. The user scans the QR code on the HMI screen, which instantly downloads the PDF report directly from the Jetson/PC over the local network.
