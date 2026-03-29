"""
splash_screen.py — Welcome / branding screen (Screen 0).

Professional entry screen with system name and version.
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
    Professional welcome screen.

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
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(10)

        layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        # ── Logo placeholder ─────────────────────────────────────────────
        logo = QLabel("🔬")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFont(QFont("Segoe UI Emoji", 48))
        logo.setStyleSheet("background: transparent;")
        layout.addWidget(logo)

        layout.addSpacing(8)

        # ── Title ────────────────────────────────────────────────────────
        title = QLabel("YakSperm Analyzer")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Inter", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #1a1a1a; background: transparent;")
        layout.addWidget(title)

        # ── Subtitle ────────────────────────────────────────────────────
        subtitle = QLabel("High-Altitude Reproductive Analysis System v2.0")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(
            "color: #4b5563; font-size: 13px; font-weight: 500; background: transparent;"
        )
        layout.addWidget(subtitle)

        # ── Tagline ──────────────────────────────────────────────────────
        tagline = QLabel("AI-Powered  •  CASA-Grade  •  Field-Ready")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setStyleSheet(
            "color: #9ca3af; font-size: 11px; background: transparent;"
        )
        layout.addWidget(tagline)

        layout.addSpacing(24)

        # ── Start Button ─────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )

        self._start_btn = QPushButton("Begin Analysis")
        self._start_btn.setProperty("role", "primary")
        self._start_btn.setMinimumSize(220, 48)
        self._start_btn.setFont(QFont("Inter", 14, QFont.Weight.DemiBold))
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.clicked.connect(self.start_requested.emit)
        btn_row.addWidget(self._start_btn)

        btn_row.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )
        layout.addLayout(btn_row)

        layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        # ── Footer ───────────────────────────────────────────────────────
        footer = QLabel("© 2026 High-Altitude Reproductive Lab  •  HARL-001")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(
            "color: #9ca3af; font-size: 10px; background: transparent;"
        )
        layout.addWidget(footer)

    # ── Animations ───────────────────────────────────────────────────────
    def _setup_animations(self) -> None:
        # Subtle pulse on the start button
        self._opacity_effect = QGraphicsOpacityEffect(self._start_btn)
        self._start_btn.setGraphicsEffect(self._opacity_effect)

        self._pulse = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._pulse.setDuration(2000)
        self._pulse.setStartValue(0.75)
        self._pulse.setEndValue(1.0)
        self._pulse.setLoopCount(-1)  # infinite

        QTimer.singleShot(200, self._pulse.start)
