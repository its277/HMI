"""
splash_screen.py — Welcome / branding screen (Screen 0).

Shows logo, system name, version, and a pulsing "Start" button.
Auto-transitions after a brief delay or on tap.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QPropertyAnimation, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


class SplashScreen(QWidget):
    """
    Branded welcome screen with animated entry.

    Signals
    -------
    start_requested()
        Emitted when the user taps "Begin Analysis".
    """

    start_requested = pyqtSignal()

    def __init__(self, parent: Any | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SplashScreen")
        self._build_ui()
        self._setup_animations()

    # ── UI Construction ──────────────────────────────────────────────────
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # ── Logo placeholder (Unicode microscope) ────────────────────────
        logo = QLabel("🔬")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFont(QFont("Segoe UI Emoji", 72))
        logo.setStyleSheet("background: transparent;")
        layout.addWidget(logo)

        # ── Title ────────────────────────────────────────────────────────
        title = QLabel("YakSperm Analyzer")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setProperty("role", "heading")
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title.setStyleSheet(
            "color: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #58a6ff, stop:1 #39d2c0); background: transparent;"
        )
        layout.addWidget(title)

        # ── Subtitle ────────────────────────────────────────────────────
        subtitle = QLabel("High-Altitude Reproductive Analysis System v2.0")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setProperty("role", "subheading")
        layout.addWidget(subtitle)

        # ── Tagline ──────────────────────────────────────────────────────
        tagline = QLabel("AI-Powered • CASA-Grade • Field-Ready")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setStyleSheet("color: #6e7681; font-size: 13px; background: transparent;")
        layout.addWidget(tagline)

        layout.addSpacing(32)

        # ── Start Button ─────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self._start_btn = QPushButton("▶  Begin Analysis")
        self._start_btn.setProperty("role", "primary")
        self._start_btn.setMinimumSize(280, 70)
        self._start_btn.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.clicked.connect(self.start_requested.emit)
        btn_row.addWidget(self._start_btn)

        btn_row.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        layout.addLayout(btn_row)

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # ── Footer ───────────────────────────────────────────────────────
        footer = QLabel("© 2026 High-Altitude Reproductive Lab  •  HARL-001")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #6e7681; font-size: 11px; background: transparent;")
        layout.addWidget(footer)

    # ── Animations ───────────────────────────────────────────────────────
    def _setup_animations(self) -> None:
        # Pulse the start button opacity
        self._opacity_effect = QGraphicsOpacityEffect(self._start_btn)
        self._start_btn.setGraphicsEffect(self._opacity_effect)

        self._pulse = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._pulse.setDuration(1500)
        self._pulse.setStartValue(0.6)
        self._pulse.setEndValue(1.0)
        self._pulse.setLoopCount(-1)  # infinite

        # Start after a tiny delay so the widget is visible
        QTimer.singleShot(200, self._pulse.start)
