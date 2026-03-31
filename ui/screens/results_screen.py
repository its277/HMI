"""
results_screen.py — Analysis Results Dashboard (Screen 3).

Displays:
  • Animal ID and Sample Dilution
  • Motility parameters (VCL, VSL, VAP, LIN, ALH, BCF)
  • Motility classification
  • Morphology breakdown
  • Pass/Fail assessment
  • Report generation button
  • QR code at the bottom
"""

from __future__ import annotations

import io
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QImage, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class _MetricCard(QFrame):
    """Single metric display card."""

    def __init__(
        self, label: str, value: str = "—", unit: str = "",
        parent: Any | None = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "background: #ffffff; border: 1px solid #d0d5dd; "
            "border-radius: 6px; padding: 6px;"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        self._label = QLabel(label.upper())
        self._label.setStyleSheet(
            "font-size: 9px; font-weight: 600; color: #9ca3af; "
            "letter-spacing: 1px; background: transparent; border: none;"
        )
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label)

        self._value = QLabel(f"{value}")
        self._value.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        self._value.setStyleSheet(
            "color: #1a1a1a; background: transparent; border: none;"
        )
        self._value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._value)

        if unit:
            self._unit = QLabel(unit)
            self._unit.setStyleSheet(
                "font-size: 10px; color: #4b5563; background: transparent; border: none;"
            )
            self._unit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self._unit)

    def set_value(self, value: str, color: str = "#1a1a1a") -> None:
        self._value.setText(value)
        self._value.setStyleSheet(
            f"color: {color}; background: transparent; border: none; "
            f"font-size: 20px; font-weight: 700;"
        )


class _BarIndicator(QWidget):
    """Horizontal bar showing a percentage against a threshold."""

    def __init__(
        self, label: str, threshold: float = 0.0,
        parent: Any | None = None,
    ) -> None:
        super().__init__(parent)
        self._threshold = threshold
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        top = QHBoxLayout()
        self._label = QLabel(label)
        self._label.setStyleSheet(
            "font-size: 12px; font-weight: 500; color: #1a1a1a; background: transparent;"
        )
        top.addWidget(self._label)
        self._pct = QLabel("—%")
        self._pct.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #1a1a1a; background: transparent;"
        )
        self._pct.setAlignment(Qt.AlignmentFlag.AlignRight)
        top.addWidget(self._pct)
        layout.addLayout(top)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setMinimumHeight(14)
        self._bar.setTextVisible(False)
        layout.addWidget(self._bar)

    def set_value(self, pct: float) -> None:
        self._pct.setText(f"{pct:.1f}%")
        self._bar.setValue(int(min(pct, 100)))
        if pct >= self._threshold:
            self._pct.setStyleSheet(
                "font-size: 12px; font-weight: 600; color: #16a34a; background: transparent;"
            )
        else:
            self._pct.setStyleSheet(
                "font-size: 12px; font-weight: 600; color: #dc2626; background: transparent;"
            )


class ResultsScreen(QWidget):
    """
    Analysis results dashboard.

    Signals
    -------
    generate_report()
        User requests PDF report.
    new_sample()
        Start a new analysis cycle.
    go_home()
        Return to splash screen.
    """

    generate_report = pyqtSignal()
    new_sample = pyqtSignal()
    go_home = pyqtSignal()

    def __init__(self, parent: Any | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ResultsScreen")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        # Header
        header_row = QHBoxLayout()
        title = QLabel("Analysis Results")
        title.setProperty("role", "heading")
        title.setFont(QFont("Inter", 16, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #1a1a1a; background: transparent;")
        header_row.addWidget(title)
        header_row.addStretch()

        self._verdict_label = QLabel("—")
        self._verdict_label.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        self._verdict_label.setStyleSheet(
            "color: #1a1a1a; background: transparent;"
        )
        header_row.addWidget(self._verdict_label)
        root.addLayout(header_row)

        sep = QFrame()
        sep.setProperty("role", "separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # ── Sample Info Row (Animal ID + Dilution) ───────────────────────
        info_row = QHBoxLayout()
        info_row.setSpacing(20)

        self._lbl_animal_id = QLabel("Animal ID: —")
        self._lbl_animal_id.setFont(QFont("Inter", 12, QFont.Weight.DemiBold))
        self._lbl_animal_id.setStyleSheet(
            "color: #2563eb; background: #eff6ff; padding: 4px 12px; "
            "border-radius: 4px; border: 1px solid #bfdbfe;"
        )
        info_row.addWidget(self._lbl_animal_id)

        self._lbl_dilution = QLabel("Dilution: —")
        self._lbl_dilution.setFont(QFont("Inter", 12, QFont.Weight.DemiBold))
        self._lbl_dilution.setStyleSheet(
            "color: #7c3aed; background: #f5f3ff; padding: 4px 12px; "
            "border-radius: 4px; border: 1px solid #ddd6fe;"
        )
        info_row.addWidget(self._lbl_dilution)

        info_row.addStretch()
        root.addLayout(info_row)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setSpacing(12)

        # ── Metric cards row ─────────────────────────────────────────────
        cards_grid = QGridLayout()
        cards_grid.setSpacing(8)

        self._card_cells = _MetricCard("Total Cells", "—")
        cards_grid.addWidget(self._card_cells, 0, 0)

        self._card_vcl = _MetricCard("Avg VCL", "—", "µm/s")
        cards_grid.addWidget(self._card_vcl, 0, 1)

        self._card_vsl = _MetricCard("Avg VSL", "—", "µm/s")
        cards_grid.addWidget(self._card_vsl, 0, 2)

        self._card_vap = _MetricCard("Avg VAP", "—", "µm/s")
        cards_grid.addWidget(self._card_vap, 0, 3)

        self._card_lin = _MetricCard("Linearity", "—")
        cards_grid.addWidget(self._card_lin, 1, 0)

        self._card_conc = _MetricCard("Concentration", "—", "M/mL")
        cards_grid.addWidget(self._card_conc, 1, 1)

        self._card_duration = _MetricCard("Duration", "—", "sec")
        cards_grid.addWidget(self._card_duration, 1, 2)

        self._card_motile = _MetricCard("Motile Cells", "—")
        cards_grid.addWidget(self._card_motile, 1, 3)

        cl.addLayout(cards_grid)

        # ── Bar indicators ──────────────────────────────────────────────
        bars_box = QGroupBox("Quality Assessment")
        bl = QVBoxLayout(bars_box)
        bl.setSpacing(8)

        self._bar_total_motility = _BarIndicator(
            "Total Motility", threshold=40.0
        )
        bl.addWidget(self._bar_total_motility)

        self._bar_progressive = _BarIndicator(
            "Progressive Motility", threshold=32.0
        )
        bl.addWidget(self._bar_progressive)

        self._bar_morphology = _BarIndicator(
            "Normal Morphology", threshold=70.0
        )
        bl.addWidget(self._bar_morphology)

        cl.addWidget(bars_box)

        # ── Morphology breakdown ─────────────────────────────────────────
        morph_box = QGroupBox("Morphology Breakdown")
        morph_layout = QGridLayout(morph_box)
        morph_layout.setSpacing(6)

        self._morph_normal = QLabel("Normal: —%")
        self._morph_normal.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #16a34a; background: transparent;"
        )
        morph_layout.addWidget(self._morph_normal, 0, 0)

        self._morph_head = QLabel("Head Defect: —%")
        self._morph_head.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #dc2626; background: transparent;"
        )
        morph_layout.addWidget(self._morph_head, 0, 1)

        self._morph_mid = QLabel("Midpiece Defect: —%")
        self._morph_mid.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #d97706; background: transparent;"
        )
        morph_layout.addWidget(self._morph_mid, 1, 0)

        self._morph_tail = QLabel("Tail Defect: —%")
        self._morph_tail.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #7c3aed; background: transparent;"
        )
        morph_layout.addWidget(self._morph_tail, 1, 1)

        cl.addWidget(morph_box)

        # ── QR Code Section ──────────────────────────────────────────────
        self._qr_box = QGroupBox("Sample QR Code")
        qr_layout = QVBoxLayout(self._qr_box)
        qr_layout.setSpacing(6)

        self._qr_label = QLabel()
        self._qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_label.setMinimumSize(120, 120)
        self._qr_label.setMaximumSize(160, 160)
        self._qr_label.setStyleSheet(
            "background: #ffffff; border: 1px solid #d0d5dd; "
            "border-radius: 6px; padding: 4px;"
        )
        self._qr_label.setText("QR will appear after report generation")
        self._qr_label.setStyleSheet(
            "background: #f9fafb; border: 1px solid #d0d5dd; "
            "border-radius: 6px; padding: 8px; color: #9ca3af; font-size: 11px;"
        )

        qr_center = QHBoxLayout()
        qr_center.addStretch()
        qr_center.addWidget(self._qr_label)
        qr_center.addStretch()
        qr_layout.addLayout(qr_center)

        self._qr_info = QLabel("Scan to view sample data")
        self._qr_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_info.setStyleSheet(
            "color: #4b5563; font-size: 11px; font-weight: 500; background: transparent;"
        )
        qr_layout.addWidget(self._qr_info)

        self._qr_box.setVisible(False)  # Hidden until QR is generated
        cl.addWidget(self._qr_box)

        scroll.setWidget(content)
        root.addWidget(scroll)

        # ── Bottom buttons ───────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_home = QPushButton("Home")
        btn_home.setMinimumHeight(40)
        btn_home.clicked.connect(self.go_home.emit)
        btn_row.addWidget(btn_home)

        btn_row.addStretch()

        self._btn_report = QPushButton("Generate Report")
        self._btn_report.setProperty("role", "primary")
        self._btn_report.setMinimumSize(180, 40)
        self._btn_report.setFont(QFont("Inter", 12, QFont.Weight.DemiBold))
        self._btn_report.clicked.connect(self.generate_report.emit)
        btn_row.addWidget(self._btn_report)

        btn_new = QPushButton("New Sample")
        btn_new.setProperty("role", "success")
        btn_new.setMinimumSize(160, 40)
        btn_new.setFont(QFont("Inter", 12, QFont.Weight.DemiBold))
        btn_new.clicked.connect(self.new_sample.emit)
        btn_row.addWidget(btn_new)

        root.addLayout(btn_row)

    # ── Public: populate results ─────────────────────────────────────────
    def display_results(
        self, result: Any,
        animal_id: str = "",
        sample_dilution: str = "",
    ) -> None:
        """Populate all widgets from an AnalysisResult dataclass."""
        r = result

        # Sample info
        self._lbl_animal_id.setText(f"Animal ID: {animal_id}" if animal_id else "Animal ID: —")
        self._lbl_dilution.setText(f"Dilution: {sample_dilution}" if sample_dilution else "Dilution: —")

        self._card_cells.set_value(str(r.total_cells))
        self._card_vcl.set_value(f"{r.avg_vcl}")
        self._card_vsl.set_value(f"{r.avg_vsl}")
        self._card_vap.set_value(f"{r.avg_vap}")
        self._card_lin.set_value(f"{r.avg_lin:.3f}")
        self._card_conc.set_value(f"{r.concentration}")
        self._card_duration.set_value(f"{r.analysis_duration_s}")
        self._card_motile.set_value(str(r.motile_cells))

        self._bar_total_motility.set_value(r.total_motility_pct)
        self._bar_progressive.set_value(r.progressive_motility_pct)
        self._bar_morphology.set_value(r.normal_morphology_pct)

        # Morphology breakdown
        total_morph = max(len(r.morphologies), 1)
        from core.ai_pipeline import MorphologyClass

        counts = {cls: 0 for cls in MorphologyClass}
        for m in r.morphologies:
            counts[m.classification] += 1

        self._morph_normal.setText(
            f"Normal: {100 * counts[MorphologyClass.NORMAL] / total_morph:.1f}%"
        )
        self._morph_head.setText(
            f"Head Defect: {100 * counts[MorphologyClass.HEAD_DEFECT] / total_morph:.1f}%"
        )
        self._morph_mid.setText(
            f"Midpiece Defect: {100 * counts[MorphologyClass.MIDPIECE_DEFECT] / total_morph:.1f}%"
        )
        self._morph_tail.setText(
            f"Tail Defect: {100 * counts[MorphologyClass.TAIL_DEFECT] / total_morph:.1f}%"
        )

        # Verdict
        passed = (
            r.total_motility_pct >= 40
            and r.progressive_motility_pct >= 32
            and r.normal_morphology_pct >= 70
        )
        if passed:
            self._verdict_label.setText("PASS")
            self._verdict_label.setStyleSheet(
                "color: #16a34a; font-size: 14px; font-weight: 700; "
                "background: #f0fdf4; padding: 4px 12px; border-radius: 4px; "
                "border: 1px solid #bbf7d0;"
            )
        else:
            self._verdict_label.setText("REVIEW REQUIRED")
            self._verdict_label.setStyleSheet(
                "color: #d97706; font-size: 14px; font-weight: 700; "
                "background: #fffbeb; padding: 4px 12px; border-radius: 4px; "
                "border: 1px solid #fde68a;"
            )

    # ── QR Code display ──────────────────────────────────────────────────
    def show_qr_code(self, data: str) -> None:
        """Generate and display a QR code at the bottom of results."""
        try:
            import qrcode

            qr = qrcode.make(data)
            buf = io.BytesIO()
            qr.save(buf, format="PNG")
            buf.seek(0)

            qimg = QImage()
            qimg.loadFromData(buf.getvalue())
            pixmap = QPixmap.fromImage(qimg)

            self._qr_label.setPixmap(
                pixmap.scaled(
                    140, 140,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self._qr_label.setStyleSheet(
                "background: #ffffff; border: 1px solid #d0d5dd; "
                "border-radius: 6px; padding: 4px;"
            )
            self._qr_box.setVisible(True)
        except ImportError:
            self._qr_label.setText("[QR: install 'qrcode' package]")
            self._qr_box.setVisible(True)

    def set_report_generating(self, active: bool) -> None:
        self._btn_report.setEnabled(not active)
        self._btn_report.setText(
            "Generating…" if active else "Generate Report"
        )

    def set_report_done(self, filepath: str) -> None:
        self._btn_report.setEnabled(True)
        self._btn_report.setText("Report Saved")
