"""
styles.py — Dark, high-contrast stylesheet for field / glove use.

Designed for:
  • Outdoor / bright sunlight readability (high contrast)
  • Touch interaction with gloves (large tap targets)
  • NVIDIA Jetson Nano 7″ display (1024×600)
"""

# ═════════════════════════════════════════════════════════════════════════════
# Color Palette
# ═════════════════════════════════════════════════════════════════════════════
COLORS = {
    "bg_primary":       "#0d1117",
    "bg_secondary":     "#161b22",
    "bg_tertiary":      "#1c2333",
    "bg_card":          "#21262d",
    "bg_hover":         "#30363d",
    "border":           "#30363d",
    "border_active":    "#58a6ff",
    "text_primary":     "#e6edf3",
    "text_secondary":   "#8b949e",
    "text_muted":       "#6e7681",
    "accent_blue":      "#58a6ff",
    "accent_green":     "#3fb950",
    "accent_orange":    "#d29922",
    "accent_red":       "#f85149",
    "accent_purple":    "#bc8cff",
    "accent_teal":      "#39d2c0",
    "gradient_start":   "#1a73e8",
    "gradient_end":     "#6c63ff",
    "success":          "#238636",
    "warning":          "#9e6a03",
    "danger":           "#da3633",
}


def get_stylesheet(min_button_px: int = 60) -> str:
    """Return the full application QSS stylesheet."""
    c = COLORS
    return f"""
    /* ═══════════════ Global ═══════════════ */
    QMainWindow, QWidget {{
        background-color: {c['bg_primary']};
        color: {c['text_primary']};
        font-family: "Segoe UI", "Roboto", "Noto Sans", sans-serif;
        font-size: 14px;
    }}

    /* ═══════════════ Labels ═══════════════ */
    QLabel {{
        color: {c['text_primary']};
        background: transparent;
    }}
    QLabel[role="heading"] {{
        font-size: 22px;
        font-weight: 700;
        color: {c['accent_blue']};
    }}
    QLabel[role="subheading"] {{
        font-size: 16px;
        font-weight: 500;
        color: {c['text_secondary']};
    }}
    QLabel[role="metric-value"] {{
        font-size: 32px;
        font-weight: 800;
        color: {c['accent_teal']};
    }}
    QLabel[role="metric-label"] {{
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: {c['text_muted']};
    }}
    QLabel[role="status-ok"] {{
        color: {c['accent_green']};
        font-weight: 600;
    }}
    QLabel[role="status-warn"] {{
        color: {c['accent_orange']};
        font-weight: 600;
    }}
    QLabel[role="status-error"] {{
        color: {c['accent_red']};
        font-weight: 600;
    }}

    /* ═══════════════ Buttons ═══════════════ */
    QPushButton {{
        min-height: {min_button_px}px;
        min-width: 120px;
        padding: 12px 24px;
        border: 2px solid {c['border']};
        border-radius: 10px;
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        font-size: 15px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {c['bg_hover']};
        border-color: {c['accent_blue']};
    }}
    QPushButton:pressed {{
        background-color: {c['border']};
    }}
    QPushButton:disabled {{
        background-color: {c['bg_tertiary']};
        color: {c['text_muted']};
        border-color: {c['bg_tertiary']};
    }}
    QPushButton[role="primary"] {{
        background-color: {c['gradient_start']};
        border-color: {c['gradient_start']};
        color: white;
    }}
    QPushButton[role="primary"]:hover {{
        background-color: {c['accent_blue']};
        border-color: {c['accent_blue']};
    }}
    QPushButton[role="success"] {{
        background-color: {c['success']};
        border-color: {c['success']};
        color: white;
    }}
    QPushButton[role="success"]:hover {{
        background-color: {c['accent_green']};
    }}
    QPushButton[role="danger"] {{
        background-color: {c['danger']};
        border-color: {c['danger']};
        color: white;
    }}
    QPushButton[role="danger"]:hover {{
        background-color: {c['accent_red']};
    }}

    /* ═══════════════ Progress Bar ═══════════════ */
    QProgressBar {{
        min-height: 24px;
        border: 2px solid {c['border']};
        border-radius: 12px;
        background-color: {c['bg_tertiary']};
        text-align: center;
        color: {c['text_primary']};
        font-weight: 600;
        font-size: 12px;
    }}
    QProgressBar::chunk {{
        border-radius: 10px;
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {c['gradient_start']},
            stop:1 {c['accent_teal']}
        );
    }}

    /* ═══════════════ Group Box / Cards ═══════════════ */
    QGroupBox {{
        border: 2px solid {c['border']};
        border-radius: 12px;
        margin-top: 14px;
        padding: 16px 12px 12px 12px;
        background-color: {c['bg_card']};
        font-weight: 600;
        font-size: 14px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 2px 12px;
        color: {c['accent_blue']};
    }}

    /* ═══════════════ Scroll Area ═══════════════ */
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollBar:vertical {{
        width: 10px;
        background: {c['bg_secondary']};
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['border']};
        border-radius: 5px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['accent_blue']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* ═══════════════ Line Edit ═══════════════ */
    QLineEdit {{
        min-height: 44px;
        padding: 8px 16px;
        border: 2px solid {c['border']};
        border-radius: 8px;
        background-color: {c['bg_secondary']};
        color: {c['text_primary']};
        font-size: 14px;
    }}
    QLineEdit:focus {{
        border-color: {c['accent_blue']};
    }}

    /* ═══════════════ Combo Box ═══════════════ */
    QComboBox {{
        min-height: 44px;
        padding: 8px 16px;
        border: 2px solid {c['border']};
        border-radius: 8px;
        background-color: {c['bg_secondary']};
        color: {c['text_primary']};
        font-size: 14px;
    }}
    QComboBox:hover {{
        border-color: {c['accent_blue']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        selection-background-color: {c['accent_blue']};
        border: 1px solid {c['border']};
        border-radius: 6px;
    }}

    /* ═══════════════ Table ═══════════════ */
    QTableWidget {{
        background-color: {c['bg_secondary']};
        gridline-color: {c['border']};
        border: 2px solid {c['border']};
        border-radius: 8px;
        font-size: 13px;
    }}
    QTableWidget::item {{
        padding: 6px;
    }}
    QTableWidget::item:selected {{
        background-color: {c['accent_blue']};
        color: white;
    }}
    QHeaderView::section {{
        background-color: {c['bg_tertiary']};
        color: {c['text_secondary']};
        padding: 8px;
        border: 1px solid {c['border']};
        font-weight: 600;
    }}

    /* ═══════════════ Status Bar ═══════════════ */
    QStatusBar {{
        background-color: {c['bg_secondary']};
        color: {c['text_secondary']};
        border-top: 1px solid {c['border']};
        font-size: 12px;
        padding: 4px;
    }}

    /* ═══════════════ Frame / Separator ═══════════════ */
    QFrame[role="separator"] {{
        background-color: {c['border']};
        max-height: 2px;
        min-height: 2px;
    }}
    QFrame[role="camera-viewport"] {{
        border: 3px solid {c['border']};
        border-radius: 12px;
        background-color: #000000;
    }}

    /* ═══════════════ Tooltips ═══════════════ */
    QToolTip {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px;
        font-size: 13px;
    }}
    """
