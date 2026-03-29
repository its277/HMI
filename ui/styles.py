"""
styles.py — Clean, professional light stylesheet for scientific instrument UI.

Designed for:
  • Laboratory / clinical environment readability
  • Professional, medical-grade appearance
  • Touch interaction (generous tap targets)
  • NVIDIA Jetson Nano 7″ display (1024×600)
"""

# ═════════════════════════════════════════════════════════════════════════════
# Color Palette — Professional Light Theme
# ═════════════════════════════════════════════════════════════════════════════
COLORS = {
    "bg_primary":       "#f8f9fa",
    "bg_secondary":     "#ffffff",
    "bg_tertiary":      "#f0f2f5",
    "bg_card":          "#ffffff",
    "bg_hover":         "#e9ecef",
    "border":           "#d0d5dd",
    "border_light":     "#e4e7eb",
    "border_active":    "#3b82f6",
    "text_primary":     "#1a1a1a",
    "text_secondary":   "#4b5563",
    "text_muted":       "#9ca3af",
    "accent_blue":      "#2563eb",
    "accent_green":     "#16a34a",
    "accent_orange":    "#d97706",
    "accent_red":       "#dc2626",
    "accent_purple":    "#7c3aed",
    "accent_teal":      "#0891b2",
    "gradient_start":   "#2563eb",
    "gradient_end":     "#1d4ed8",
    "success":          "#16a34a",
    "success_bg":       "#f0fdf4",
    "warning":          "#d97706",
    "warning_bg":       "#fffbeb",
    "danger":           "#dc2626",
    "danger_bg":        "#fef2f2",
    "shadow":           "rgba(0, 0, 0, 0.06)",
}


def get_stylesheet(min_button_px: int = 48) -> str:
    """Return the full application QSS stylesheet."""
    c = COLORS
    return f"""
    /* ═══════════════ Global ═══════════════ */
    QMainWindow, QWidget {{
        background-color: {c['bg_primary']};
        color: {c['text_primary']};
        font-family: "Inter", "Segoe UI", "Roboto", "Noto Sans", sans-serif;
        font-size: 13px;
    }}

    /* ═══════════════ Labels ═══════════════ */
    QLabel {{
        color: {c['text_primary']};
        background: transparent;
    }}
    QLabel[role="heading"] {{
        font-size: 18px;
        font-weight: 600;
        color: {c['text_primary']};
    }}
    QLabel[role="subheading"] {{
        font-size: 13px;
        font-weight: 500;
        color: {c['text_secondary']};
    }}
    QLabel[role="metric-value"] {{
        font-size: 26px;
        font-weight: 700;
        color: {c['text_primary']};
    }}
    QLabel[role="metric-label"] {{
        font-size: 10px;
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
        min-width: 100px;
        padding: 8px 20px;
        border: 1px solid {c['border']};
        border-radius: 6px;
        background-color: {c['bg_secondary']};
        color: {c['text_primary']};
        font-size: 13px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {c['bg_hover']};
        border-color: {c['border_active']};
    }}
    QPushButton:pressed {{
        background-color: {c['bg_tertiary']};
    }}
    QPushButton:disabled {{
        background-color: {c['bg_tertiary']};
        color: {c['text_muted']};
        border-color: {c['border_light']};
    }}
    QPushButton[role="primary"] {{
        background-color: {c['accent_blue']};
        border-color: {c['accent_blue']};
        color: white;
    }}
    QPushButton[role="primary"]:hover {{
        background-color: {c['gradient_end']};
        border-color: {c['gradient_end']};
    }}
    QPushButton[role="success"] {{
        background-color: {c['success']};
        border-color: {c['success']};
        color: white;
    }}
    QPushButton[role="success"]:hover {{
        background-color: #15803d;
    }}
    QPushButton[role="danger"] {{
        background-color: {c['danger']};
        border-color: {c['danger']};
        color: white;
    }}
    QPushButton[role="danger"]:hover {{
        background-color: #b91c1c;
    }}

    /* ═══════════════ Progress Bar ═══════════════ */
    QProgressBar {{
        min-height: 20px;
        border: 1px solid {c['border']};
        border-radius: 10px;
        background-color: {c['bg_tertiary']};
        text-align: center;
        color: {c['text_primary']};
        font-weight: 500;
        font-size: 11px;
    }}
    QProgressBar::chunk {{
        border-radius: 9px;
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {c['accent_blue']},
            stop:1 {c['accent_teal']}
        );
    }}

    /* ═══════════════ Group Box / Cards ═══════════════ */
    QGroupBox {{
        border: 1px solid {c['border']};
        border-radius: 8px;
        margin-top: 12px;
        padding: 14px 10px 10px 10px;
        background-color: {c['bg_card']};
        font-weight: 600;
        font-size: 13px;
        color: {c['text_primary']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 2px 10px;
        color: {c['text_secondary']};
        font-weight: 600;
    }}

    /* ═══════════════ Scroll Area ═══════════════ */
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollBar:vertical {{
        width: 8px;
        background: {c['bg_tertiary']};
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['border']};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['text_muted']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* ═══════════════ Line Edit ═══════════════ */
    QLineEdit {{
        min-height: 36px;
        padding: 6px 12px;
        border: 1px solid {c['border']};
        border-radius: 6px;
        background-color: {c['bg_secondary']};
        color: {c['text_primary']};
        font-size: 13px;
    }}
    QLineEdit:focus {{
        border-color: {c['accent_blue']};
    }}

    /* ═══════════════ Combo Box ═══════════════ */
    QComboBox {{
        min-height: 36px;
        padding: 6px 12px;
        border: 1px solid {c['border']};
        border-radius: 6px;
        background-color: {c['bg_secondary']};
        color: {c['text_primary']};
        font-size: 13px;
    }}
    QComboBox:hover {{
        border-color: {c['accent_blue']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c['bg_secondary']};
        color: {c['text_primary']};
        selection-background-color: {c['accent_blue']};
        selection-color: white;
        border: 1px solid {c['border']};
        border-radius: 4px;
    }}

    /* ═══════════════ Table ═══════════════ */
    QTableWidget {{
        background-color: {c['bg_secondary']};
        gridline-color: {c['border_light']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        font-size: 12px;
        color: {c['text_primary']};
    }}
    QTableWidget::item {{
        padding: 6px;
        color: {c['text_primary']};
    }}
    QTableWidget::item:selected {{
        background-color: #dbeafe;
        color: {c['text_primary']};
    }}
    QHeaderView::section {{
        background-color: {c['bg_tertiary']};
        color: {c['text_secondary']};
        padding: 8px;
        border: 1px solid {c['border_light']};
        font-weight: 600;
        font-size: 11px;
        text-transform: uppercase;
    }}

    /* ═══════════════ Status Bar ═══════════════ */
    QStatusBar {{
        background-color: {c['bg_secondary']};
        color: {c['text_secondary']};
        border-top: 1px solid {c['border']};
        font-size: 11px;
        padding: 2px 8px;
    }}

    /* ═══════════════ Frame / Separator ═══════════════ */
    QFrame[role="separator"] {{
        background-color: {c['border']};
        max-height: 1px;
        min-height: 1px;
    }}
    QFrame[role="camera-viewport"] {{
        border: 1px solid {c['border']};
        border-radius: 8px;
        background-color: #1a1a1a;
    }}

    /* ═══════════════ Tooltips ═══════════════ */
    QToolTip {{
        background-color: {c['bg_secondary']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        padding: 6px;
        font-size: 12px;
    }}
    """
