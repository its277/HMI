"""
setup_screen.py — Hardware Setup & Calibration (Screen 1).

Shows:
  • Serial connection status & controls
  • Thermal stage temperature gauge
  • Camera preview toggle
  • Slide loading servo control
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class _StatusIndicator(QWidget):
    """Small coloured dot + label for status items."""

    def __init__(self, label: str, parent: Any | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._dot = QLabel("●")
        self._dot.setFixedWidth(16)
        self._dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dot.setStyleSheet(
            "color: #9ca3af; font-size: 14px; background: transparent;"
        )
        layout.addWidget(self._dot)

        self._label = QLabel(label)
        self._label.setStyleSheet(
            "font-size: 12px; color: #1a1a1a; background: transparent;"
        )
        layout.addWidget(self._label)
        layout.addStretch()

    def set_status(self, ok: bool) -> None:
        color = "#16a34a" if ok else "#dc2626"
        self._dot.setStyleSheet(
            f"color: {color}; font-size: 14px; background: transparent;"
        )


class SetupScreen(QWidget):
    """
    Hardware configuration and pre-analysis checks.

    Signals
    -------
    connect_serial()
        Request serial connection.
    start_heating()
        Start PID heating to 37 °C.
    load_slide()
        Actuate slide servo.
    proceed_to_analysis()
        All checks passed, move to capture screen.
    """

    connect_serial = pyqtSignal()
    start_heating = pyqtSignal()
    load_slide = pyqtSignal()
    proceed_to_analysis = pyqtSignal()

    def __init__(self, parent: Any | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SetupScreen")
        self._build_ui()

    # ── UI ───────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 14)
        root.setSpacing(10)

        # Header
        header = QLabel("System Setup")
        header.setProperty("role", "heading")
        header.setFont(QFont("Inter", 18, QFont.Weight.DemiBold))
        header.setStyleSheet("color: #1a1a1a; background: transparent;")
        root.addWidget(header)

        sep = QFrame()
        sep.setProperty("role", "separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # Main grid
        grid = QGridLayout()
        grid.setSpacing(12)

        # ── Card 1: Serial Connection ────────────────────────────────────
        serial_card = QGroupBox("Serial Connection")
        sl = QVBoxLayout(serial_card)
        sl.setSpacing(6)
        self._serial_status = _StatusIndicator("ESP32 Connection")
        sl.addWidget(self._serial_status)
        self._serial_info = QLabel("Port: —  |  Firmware: —")
        self._serial_info.setStyleSheet(
            "font-size: 11px; color: #4b5563; background: transparent;"
        )
        sl.addWidget(self._serial_info)
        self._btn_connect = QPushButton("Connect")
        self._btn_connect.setProperty("role", "primary")
        self._btn_connect.clicked.connect(self.connect_serial.emit)
        sl.addWidget(self._btn_connect)
        grid.addWidget(serial_card, 0, 0)

        # ── Card 2: Thermal Stage ────────────────────────────────────────
        thermal_card = QGroupBox("Thermal Stage")
        tl = QVBoxLayout(thermal_card)
        tl.setSpacing(6)
        self._temp_value = QLabel("—.— °C")
        self._temp_value.setProperty("role", "metric-value")
        self._temp_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._temp_value.setStyleSheet(
            "color: #1a1a1a; font-size: 26px; font-weight: 700; background: transparent;"
        )
        tl.addWidget(self._temp_value)
        self._temp_label = QLabel("TARGET: 37.0 ± 0.5 °C")
        self._temp_label.setProperty("role", "metric-label")
        self._temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._temp_label.setStyleSheet(
            "font-size: 10px; color: #9ca3af; background: transparent;"
        )
        tl.addWidget(self._temp_label)
        self._temp_bar = QProgressBar()
        self._temp_bar.setRange(200, 400)  # 20.0 to 40.0 °C × 10
        self._temp_bar.setValue(200)
        self._temp_bar.setFormat("%v/10 °C")
        self._temp_bar.setTextVisible(False)
        tl.addWidget(self._temp_bar)
        self._thermal_status = _StatusIndicator("Temperature Stable")
        tl.addWidget(self._thermal_status)
        self._btn_heat = QPushButton("Start Heating")
        self._btn_heat.setProperty("role", "primary")
        self._btn_heat.clicked.connect(self.start_heating.emit)
        tl.addWidget(self._btn_heat)
        grid.addWidget(thermal_card, 0, 1)

        # ── Card 3: Camera ───────────────────────────────────────────────
        cam_card = QGroupBox("Microscope Camera")
        cl = QVBoxLayout(cam_card)
        cl.setSpacing(6)
        self._cam_status = _StatusIndicator("Camera Feed")
        cl.addWidget(self._cam_status)
        self._cam_fps = QLabel("FPS: —")
        self._cam_fps.setStyleSheet(
            "font-size: 11px; color: #4b5563; background: transparent;"
        )
        cl.addWidget(self._cam_fps)
        self._cam_preview = QLabel()
        self._cam_preview.setMinimumHeight(100)
        self._cam_preview.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._cam_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cam_preview.setStyleSheet(
            "background: #f0f2f5; border: 1px solid #d0d5dd; border-radius: 6px;"
        )
        self._cam_preview.setText("No preview")
        cl.addWidget(self._cam_preview)
        grid.addWidget(cam_card, 1, 0)

        # ── Card 4: Slide Loader ─────────────────────────────────────────
        slide_card = QGroupBox("Slide Loader")
        sll = QVBoxLayout(slide_card)
        sll.setSpacing(6)
        self._slide_status = _StatusIndicator("Slide Loaded")
        sll.addWidget(self._slide_status)
        self._slide_info = QLabel("Servo position: 0°")
        self._slide_info.setStyleSheet(
            "font-size: 11px; color: #4b5563; background: transparent;"
        )
        sll.addWidget(self._slide_info)
        self._btn_slide = QPushButton("Load Slide")
        self._btn_slide.setProperty("role", "primary")
        self._btn_slide.clicked.connect(self.load_slide.emit)
        sll.addWidget(self._btn_slide)
        grid.addWidget(slide_card, 1, 1)

        root.addLayout(grid)
        root.addStretch()

        # ── Proceed button ───────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_proceed = QPushButton("Start Capture")
        self._btn_proceed.setProperty("role", "success")
        self._btn_proceed.setMinimumSize(200, 44)
        self._btn_proceed.setFont(QFont("Inter", 13, QFont.Weight.DemiBold))
        self._btn_proceed.setEnabled(False)
        self._btn_proceed.clicked.connect(self.proceed_to_analysis.emit)
        btn_row.addWidget(self._btn_proceed)
        btn_row.addStretch()
        root.addLayout(btn_row)

    # ── Public update slots ──────────────────────────────────────────────
    def update_serial_status(self, connected: bool, info: str = "") -> None:
        self._serial_status.set_status(connected)
        self._serial_info.setText(
            info if info else ("Connected" if connected else "Disconnected")
        )
        self._btn_connect.setText("Connected" if connected else "Connect")
        self._btn_connect.setEnabled(not connected)
        self._check_ready()

    def update_temperature(self, temp: float, stable: bool = False) -> None:
        self._temp_value.setText(f"{temp:.1f} °C")
        self._temp_bar.setValue(int(temp * 10))
        self._thermal_status.set_status(stable)
        if stable:
            self._temp_value.setStyleSheet(
                "color: #16a34a; font-size: 26px; font-weight: 700; background: transparent;"
            )
        elif temp > 35:
            self._temp_value.setStyleSheet(
                "color: #d97706; font-size: 26px; font-weight: 700; background: transparent;"
            )
        else:
            self._temp_value.setStyleSheet(
                "color: #1a1a1a; font-size: 26px; font-weight: 700; background: transparent;"
            )
        self._check_ready()

    def update_camera_status(self, active: bool, fps: float = 0.0) -> None:
        self._cam_status.set_status(active)
        self._cam_fps.setText(f"FPS: {fps:.1f}" if active else "FPS: —")
        self._check_ready()

    def update_camera_preview(self, pixmap: Any) -> None:
        """Set a QPixmap preview thumbnail."""
        if pixmap:
            self._cam_preview.setPixmap(
                pixmap.scaled(
                    self._cam_preview.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def update_slide_status(self, loaded: bool) -> None:
        self._slide_status.set_status(loaded)
        self._slide_info.setText(
            "Servo position: 90°" if loaded else "Servo position: 0°"
        )
        self._check_ready()

    def _check_ready(self) -> None:
        """Enable Proceed when all subsystems are green."""
        serial_ok = self._serial_status._dot.styleSheet().find("#16a34a") != -1
        thermal_ok = self._thermal_status._dot.styleSheet().find("#16a34a") != -1
        cam_ok = self._cam_status._dot.styleSheet().find("#16a34a") != -1
        self._btn_proceed.setEnabled(serial_ok and thermal_ok and cam_ok)
