"""
history_screen.py — Past Reports Browser (Screen 4).

Lists previously generated PDF reports with metadata.
Clicking a report shows a QR code popup for download.
"""

from __future__ import annotations

import io
import os
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QImage, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class _QRPopupDialog(QDialog):
    """
    Modal dialog showing a QR code with 'Scan to Connect & Download' text
    and a red X close button.
    """

    def __init__(
        self, qr_data: str, filename: str, parent: Any | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Download Report")
        self.setFixedSize(320, 380)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setStyleSheet(
            "QDialog {"
            "  background: #ffffff;"
            "  border: 2px solid #d0d5dd;"
            "  border-radius: 12px;"
            "}"
        )
        self._build_ui(qr_data, filename)

    def _build_ui(self, qr_data: str, filename: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)

        # ── Top bar with close button ────────────────────────────────────
        top_row = QHBoxLayout()
        top_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            "QPushButton {"
            "  background: #dc2626; color: white; border: none;"
            "  border-radius: 16px; font-weight: 700;"
            "}"
            "QPushButton:hover {"
            "  background: #b91c1c;"
            "}"
        )
        close_btn.clicked.connect(self.close)
        top_row.addWidget(close_btn)
        layout.addLayout(top_row)

        # ── Title ────────────────────────────────────────────────────────
        title = QLabel("Scan to Connect & Download")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Inter", 13, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #1a1a1a; background: transparent;")
        layout.addWidget(title)

        layout.addSpacing(4)

        # ── QR Code ──────────────────────────────────────────────────────
        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_label.setMinimumSize(180, 180)
        qr_label.setMaximumSize(200, 200)
        qr_label.setStyleSheet(
            "background: #ffffff; border: 1px solid #e5e7eb; "
            "border-radius: 8px; padding: 8px;"
        )

        try:
            import qrcode

            qr = qrcode.make(qr_data)
            buf = io.BytesIO()
            qr.save(buf, format="PNG")
            buf.seek(0)

            qimg = QImage()
            qimg.loadFromData(buf.getvalue())
            pixmap = QPixmap.fromImage(qimg)

            qr_label.setPixmap(
                pixmap.scaled(
                    180, 180,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        except ImportError:
            qr_label.setText("[Install 'qrcode' package]")
            qr_label.setStyleSheet(
                "color: #9ca3af; font-size: 11px; background: #f9fafb; "
                "border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px;"
            )

        qr_row = QHBoxLayout()
        qr_row.addStretch()
        qr_row.addWidget(qr_label)
        qr_row.addStretch()
        layout.addLayout(qr_row)

        layout.addSpacing(4)

        # ── Filename info ────────────────────────────────────────────────
        file_label = QLabel(filename)
        file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        file_label.setStyleSheet(
            "color: #4b5563; font-size: 11px; font-weight: 500; "
            "background: transparent;"
        )
        file_label.setWordWrap(True)
        layout.addWidget(file_label)

        layout.addStretch()


class HistoryScreen(QWidget):
    """
    Displays a table of past analysis reports.
    Clicking a row opens a QR code popup.

    Signals
    -------
    go_home()
        Return to splash screen.
    """

    go_home = pyqtSignal()

    def __init__(
        self, reports_dir: str = "reports/", parent: Any | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("HistoryScreen")
        self._reports_dir = reports_dir
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 14)
        root.setSpacing(10)

        # Header
        header_row = QHBoxLayout()
        title = QLabel("Report History")
        title.setProperty("role", "heading")
        title.setFont(QFont("Inter", 16, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #1a1a1a; background: transparent;")
        header_row.addWidget(title)
        header_row.addStretch()

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setMinimumHeight(36)
        btn_refresh.clicked.connect(self.refresh)
        header_row.addWidget(btn_refresh)
        root.addLayout(header_row)

        sep = QFrame()
        sep.setProperty("role", "separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # Instruction hint
        hint = QLabel("Click on a report to view its download QR code")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(
            "color: #6b7280; font-size: 11px; font-style: italic; "
            "background: transparent; padding: 2px;"
        )
        root.addWidget(hint)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(
            ["Filename", "Sample ID", "Date", "Size"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.cellClicked.connect(self._on_row_clicked)
        root.addWidget(self._table)

        # Empty state
        self._empty_label = QLabel(
            "No reports found. Run an analysis first."
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            "color: #9ca3af; font-size: 13px; background: transparent;"
        )
        root.addWidget(self._empty_label)

        root.addStretch()

        # Bottom
        btn_row = QHBoxLayout()
        btn_home = QPushButton("Home")
        btn_home.setMinimumHeight(40)
        btn_home.clicked.connect(self.go_home.emit)
        btn_row.addWidget(btn_home)
        btn_row.addStretch()
        root.addLayout(btn_row)

    def _on_row_clicked(self, row: int, _column: int) -> None:
        """Show QR code popup when a report row is clicked."""
        fname_item = self._table.item(row, 0)
        if fname_item is None:
            return

        filename = fname_item.text()
        filepath = os.path.join(self._reports_dir, filename)

        # Parse sample ID from filename for QR data
        parts = filename.replace(".pdf", "").replace(".txt", "").split("_")
        sample_id = parts[0] if parts else filename

        # QR data encodes sample metadata
        qr_data = (
            f"SampleID:{sample_id}"
            f"|File:{filename}"
            f"|Path:{os.path.abspath(filepath)}"
        )

        dialog = _QRPopupDialog(qr_data, filename, parent=self)
        dialog.exec()

    def refresh(self) -> None:
        """Scan reports directory and populate table."""
        self._table.setRowCount(0)

        if not os.path.isdir(self._reports_dir):
            self._empty_label.setVisible(True)
            self._table.setVisible(False)
            return

        files = sorted(
            [
                f
                for f in os.listdir(self._reports_dir)
                if f.endswith((".pdf", ".txt"))
            ],
            reverse=True,
        )

        if not files:
            self._empty_label.setVisible(True)
            self._table.setVisible(False)
            return

        self._empty_label.setVisible(False)
        self._table.setVisible(True)
        self._table.setRowCount(len(files))

        for i, fname in enumerate(files):
            fpath = os.path.join(self._reports_dir, fname)
            stat = os.stat(fpath)

            # Parse sample ID from filename
            parts = fname.replace(".pdf", "").replace(".txt", "").split("_")
            sample_id = parts[0] if parts else "—"
            date_str = "_".join(parts[1:]) if len(parts) > 1 else "—"

            size_kb = stat.st_size / 1024

            self._table.setItem(i, 0, QTableWidgetItem(fname))
            self._table.setItem(i, 1, QTableWidgetItem(sample_id))
            self._table.setItem(i, 2, QTableWidgetItem(date_str))
            self._table.setItem(i, 3, QTableWidgetItem(f"{size_kb:.1f} KB"))

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        self.refresh()
