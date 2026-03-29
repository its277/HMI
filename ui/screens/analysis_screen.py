"""
analysis_screen.py — Live capture & AI analysis view (Screen 2).

Shows:
  • Live camera viewport with detection overlay
  • Capture progress / frame counter
  • AI pipeline stage indicator
  • Real-time detection count
"""

from __future__ import annotations

from typing import Any

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QImage, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class AnalysisScreen(QWidget):
    """
    Real-time analysis view with camera feed + pipeline status.

    Signals
    -------
    capture_requested()
        User clicks "Capture Frames".
    cancel_requested()
        User cancels ongoing analysis.
    """

    capture_requested = pyqtSignal()
    cancel_requested = pyqtSignal()

    def __init__(self, parent: Any | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AnalysisScreen")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # ── Left: Camera viewport ────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(8)

        cam_title = QLabel("📷  Live Microscope Feed")
        cam_title.setProperty("role", "heading")
        cam_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        left.addWidget(cam_title)

        self._viewport = QLabel()
        self._viewport.setProperty("role", "camera-viewport")
        self._viewport.setMinimumSize(640, 400)
        self._viewport.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._viewport.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._viewport.setStyleSheet(
            "background: #000; border: 3px solid #30363d; border-radius: 12px;"
        )
        self._viewport.setText("Waiting for camera…")
        left.addWidget(self._viewport)

        # FPS overlay label
        self._fps_label = QLabel("FPS: —")
        self._fps_label.setStyleSheet(
            "color: #3fb950; font-size: 12px; font-weight: 600; background: transparent;"
        )
        left.addWidget(self._fps_label)

        root.addLayout(left, stretch=3)

        # ── Right: Status panel ──────────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(12)

        # Pipeline stage
        stage_box = QGroupBox("AI Pipeline")
        sl = QVBoxLayout(stage_box)

        self._stage_label = QLabel("Stage: Idle")
        self._stage_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._stage_label.setStyleSheet("color: #58a6ff; background: transparent;")
        sl.addWidget(self._stage_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setMinimumHeight(28)
        sl.addWidget(self._progress_bar)

        self._stage_detail = QLabel("—")
        self._stage_detail.setStyleSheet("color: #8b949e; font-size: 12px; background: transparent;")
        sl.addWidget(self._stage_detail)
        right.addWidget(stage_box)

        # Detection metrics
        metrics_box = QGroupBox("Real-Time Metrics")
        ml = QVBoxLayout(metrics_box)

        self._metric_cells = self._make_metric("Cells Detected", "0")
        ml.addLayout(self._metric_cells["layout"])

        self._metric_frames = self._make_metric("Frames Captured", "0 / 90")
        ml.addLayout(self._metric_frames["layout"])

        self._metric_conf = self._make_metric("Avg Confidence", "—")
        ml.addLayout(self._metric_conf["layout"])

        right.addWidget(metrics_box)

        # Temperature
        temp_box = QGroupBox("Thermal Stage")
        tl = QVBoxLayout(temp_box)
        self._temp_label = QLabel("37.0 °C")
        self._temp_label.setProperty("role", "metric-value")
        self._temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._temp_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        tl.addWidget(self._temp_label)
        right.addWidget(temp_box)

        right.addStretch()

        # Buttons
        self._btn_capture = QPushButton("⏺  Capture Frames")
        self._btn_capture.setProperty("role", "primary")
        self._btn_capture.setMinimumHeight(60)
        self._btn_capture.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._btn_capture.clicked.connect(self.capture_requested.emit)
        right.addWidget(self._btn_capture)

        self._btn_cancel = QPushButton("✕  Cancel")
        self._btn_cancel.setProperty("role", "danger")
        self._btn_cancel.setMinimumHeight(60)
        self._btn_cancel.setEnabled(False)
        self._btn_cancel.clicked.connect(self.cancel_requested.emit)
        right.addWidget(self._btn_cancel)

        root.addLayout(right, stretch=1)

    # ── Helper ───────────────────────────────────────────────────────────
    @staticmethod
    def _make_metric(label: str, default: str) -> dict[str, Any]:
        layout = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setProperty("role", "metric-label")
        lbl.setStyleSheet("font-size: 12px; color: #8b949e; background: transparent;")
        val = QLabel(default)
        val.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        val.setStyleSheet("color: #39d2c0; background: transparent;")
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(lbl)
        layout.addStretch()
        layout.addWidget(val)
        return {"layout": layout, "value": val}

    # ── Public update methods ────────────────────────────────────────────
    def update_frame(self, frame: np.ndarray) -> None:
        """Display a BGR numpy frame in the viewport."""
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        rgb = frame[..., ::-1].copy()  # BGR → RGB
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        self._viewport.setPixmap(
            pixmap.scaled(
                self._viewport.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def update_fps(self, fps: float) -> None:
        self._fps_label.setText(f"FPS: {fps:.1f}")

    def update_temperature(self, temp: float) -> None:
        self._temp_label.setText(f"{temp:.1f} °C")
        if 36.5 <= temp <= 37.5:
            self._temp_label.setStyleSheet(
                "color: #3fb950; font-size: 28px; font-weight: 800; background: transparent;"
            )
        else:
            self._temp_label.setStyleSheet(
                "color: #d29922; font-size: 28px; font-weight: 800; background: transparent;"
            )

    def update_pipeline_stage(self, stage: str) -> None:
        stage_map = {
            "detection":  "🔍  Stage 1 — YOLO Detection",
            "motility":   "📊  Stage 2 — UKF Motility",
            "morphology": "🧬  Stage 3 — Morphology",
            "done":       "✅  Analysis Complete",
        }
        self._stage_label.setText(stage_map.get(stage, f"Stage: {stage}"))

    def update_progress(self, pct: int) -> None:
        self._progress_bar.setValue(pct)

    def update_frame_count(self, current: int, total: int) -> None:
        self._metric_frames["value"].setText(f"{current} / {total}")

    def update_detection_count(self, count: int) -> None:
        self._metric_cells["value"].setText(str(count))

    def set_capturing(self, active: bool) -> None:
        """Toggle button states for capture mode."""
        self._btn_capture.setEnabled(not active)
        self._btn_cancel.setEnabled(active)

    def set_analysing(self, active: bool) -> None:
        self._btn_capture.setEnabled(not active)
        self._btn_cancel.setEnabled(active)
        if active:
            self._stage_detail.setText("Processing captured frames…")
        else:
            self._stage_detail.setText("—")
