"""
splash_screen.py — Welcome / branding screen (Screen 0).

Professional entry screen with system name, version, and
required Animal ID / Sample Dilution inputs.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QPropertyAnimation, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


class SplashScreen(QWidget):
    """
    Professional welcome screen with required inputs.

    Signals
    -------
    start_requested()
        Emitted when the user taps "Begin Analysis" (only when inputs valid).
    """

    start_requested = pyqtSignal()

    def __init__(self, parent: Any | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SplashScreen")
        self._build_ui()
        self._setup_animations()

    # ── Properties ───────────────────────────────────────────────────────
    @property
    def animal_id(self) -> str:
        """Return current Animal ID text."""
        return self._animal_id_input.text().strip()

    @property
    def sample_dilution(self) -> str:
        """Return selected sample dilution."""
        return self._dilution_combo.currentText()

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
        tagline = QLabel("AI-Powered  •  Standard-Grade  •  Field-Ready")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setStyleSheet(
            "color: #9ca3af; font-size: 11px; background: transparent;"
        )
        layout.addWidget(tagline)

        layout.addSpacing(20)

        # ── Animal ID Input ──────────────────────────────────────────────
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)
        input_container.setMaximumWidth(360)

        # Animal ID
        aid_label = QLabel("Animal ID / No.")
        aid_label.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #1a1a1a; background: transparent;"
        )
        input_layout.addWidget(aid_label)

        self._animal_id_input = QLineEdit()
        self._animal_id_input.setPlaceholderText("Enter Animal ID (e.g. A102)")
        self._animal_id_input.setMinimumHeight(40)
        self._animal_id_input.setFont(QFont("Inter", 12))
        self._animal_id_input.setStyleSheet(
            "QLineEdit {"
            "  border: 1px solid #d0d5dd;"
            "  border-radius: 6px;"
            "  padding: 6px 12px;"
            "  font-size: 13px;"
            "  color: #1a1a1a;"
            "  background: #ffffff;"
            "}"
            "QLineEdit:focus {"
            "  border: 2px solid #2563eb;"
            "}"
        )
        self._animal_id_input.textChanged.connect(self._validate_inputs)
        input_layout.addWidget(self._animal_id_input)

        # Sample Dilution
        dil_label = QLabel("Sample Dilution")
        dil_label.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #1a1a1a; background: transparent;"
        )
        input_layout.addWidget(dil_label)

        self._dilution_combo = QComboBox()
        self._dilution_combo.addItem("")  # Blank placeholder
        self._dilution_combo.addItem("1:19")
        self._dilution_combo.setCurrentIndex(0)
        self._dilution_combo.setMinimumHeight(40)
        self._dilution_combo.setFont(QFont("Inter", 12))
        self._dilution_combo.setStyleSheet(
            "QComboBox {"
            "  border: 1px solid #d0d5dd;"
            "  border-radius: 6px;"
            "  padding: 6px 12px;"
            "  font-size: 13px;"
            "  color: #1a1a1a;"
            "  background: #ffffff;"
            "}"
            "QComboBox:focus {"
            "  border: 2px solid #2563eb;"
            "}"
            "QComboBox::drop-down {"
            "  border: none;"
            "  width: 30px;"
            "}"
            "QComboBox QAbstractItemView {"
            "  background: #ffffff;"
            "  border: 1px solid #d0d5dd;"
            "  selection-background-color: #2563eb;"
            "  selection-color: white;"
            "}"
        )
        # Set placeholder text appearance
        self._dilution_combo.setItemText(0, "Select Dilution")
        self._dilution_combo.currentIndexChanged.connect(self._validate_inputs)
        input_layout.addWidget(self._dilution_combo)

        # Center the input container
        input_row = QHBoxLayout()
        input_row.addStretch()
        input_row.addWidget(input_container)
        input_row.addStretch()
        layout.addLayout(input_row)

        layout.addSpacing(16)

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
        self._start_btn.setEnabled(False)  # Disabled until inputs are valid
        self._start_btn.clicked.connect(self._on_start_clicked)
        btn_row.addWidget(self._start_btn)

        btn_row.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )
        layout.addLayout(btn_row)

        # ── Validation hint ──────────────────────────────────────────────
        self._hint_label = QLabel("Please fill Animal ID and select Sample Dilution")
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_label.setStyleSheet(
            "color: #d97706; font-size: 11px; font-weight: 500; background: transparent;"
        )
        layout.addWidget(self._hint_label)

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

    # ── Validation ───────────────────────────────────────────────────────
    def _validate_inputs(self) -> None:
        """Enable/disable Start button based on input validity."""
        aid_ok = len(self._animal_id_input.text().strip()) > 0
        dil_ok = self._dilution_combo.currentIndex() > 0  # Not the placeholder

        self._start_btn.setEnabled(aid_ok and dil_ok)

        if aid_ok and dil_ok:
            self._hint_label.setText("")
        elif not aid_ok and not dil_ok:
            self._hint_label.setText("Please fill Animal ID and select Sample Dilution")
        elif not aid_ok:
            self._hint_label.setText("Please enter Animal ID")
        else:
            self._hint_label.setText("Please select Sample Dilution")

    def _on_start_clicked(self) -> None:
        """Emit start only if inputs are valid."""
        if self._start_btn.isEnabled():
            self.start_requested.emit()

    # ── Public reset ─────────────────────────────────────────────────────
    def reset_inputs(self) -> None:
        """Clear inputs for a new session."""
        self._animal_id_input.clear()
        self._dilution_combo.setCurrentIndex(0)

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
