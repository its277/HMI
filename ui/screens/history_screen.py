"""
history_screen.py — Past Reports Browser (Screen 4).

Lists previously generated PDF reports with metadata.
"""

from __future__ import annotations

import os
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
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


class HistoryScreen(QWidget):
    """
    Displays a table of past analysis reports.

    Signals
    -------
    go_home()
        Return to splash screen.
    """

    go_home = pyqtSignal()

    def __init__(self, reports_dir: str = "reports/", parent: Any | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("HistoryScreen")
        self._reports_dir = reports_dir
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Header
        header_row = QHBoxLayout()
        title = QLabel("📁  Report History")
        title.setProperty("role", "heading")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header_row.addWidget(title)
        header_row.addStretch()

        btn_refresh = QPushButton("🔄  Refresh")
        btn_refresh.setMinimumHeight(48)
        btn_refresh.clicked.connect(self.refresh)
        header_row.addWidget(btn_refresh)
        root.addLayout(header_row)

        sep = QFrame()
        sep.setProperty("role", "separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Filename", "Sample ID", "Date", "Size"])
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
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setMinimumHeight(300)
        root.addWidget(self._table)

        # Empty state
        self._empty_label = QLabel("No reports found. Run an analysis first.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("color: #6e7681; font-size: 16px; background: transparent;")
        root.addWidget(self._empty_label)

        root.addStretch()

        # Bottom
        btn_row = QHBoxLayout()
        btn_home = QPushButton("🏠  Home")
        btn_home.setMinimumHeight(60)
        btn_home.clicked.connect(self.go_home.emit)
        btn_row.addWidget(btn_home)
        btn_row.addStretch()
        root.addLayout(btn_row)

    def refresh(self) -> None:
        """Scan reports directory and populate table."""
        self._table.setRowCount(0)

        if not os.path.isdir(self._reports_dir):
            self._empty_label.setVisible(True)
            self._table.setVisible(False)
            return

        files = sorted(
            [f for f in os.listdir(self._reports_dir) if f.endswith((".pdf", ".txt"))],
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
