#!/usr/bin/env python3
"""
main.py — Entry point for the YakSperm Analyzer HMI.

Usage:
    python main.py              # Normal mode (requires ESP32 + camera)
    python main.py --mock       # Mock mode (simulated hardware)
    python main.py --fullscreen # Fullscreen (Jetson kiosk mode)

Author: High-Altitude Reproductive Lab
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.styles import get_stylesheet


def setup_logging(verbose: bool = False) -> None:
    """Configure root logger."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)-7s] %(name)-25s — %(message)s",
        datefmt="%H:%M:%S",
    )


def load_config(config_path: str = "utils/config.yaml") -> dict:
    """Load YAML configuration file."""
    path = Path(config_path)
    if not path.exists():
        logging.warning("Config not found at %s — using defaults", config_path)
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="YakSperm Analyzer — High-Altitude Semen Analysis HMI",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run with simulated hardware (no ESP32 / camera required)",
    )
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="Launch in fullscreen kiosk mode",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="utils/config.yaml",
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def main() -> int:
    """Application entry point."""
    args = parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger("main")

    # Change to project root so relative paths work
    os.chdir(Path(__file__).parent)

    logger.info("═" * 60)
    logger.info("  YakSperm Analyzer HMI v2.0")
    logger.info("  Mock mode: %s", args.mock)
    logger.info("═" * 60)

    # Load configuration
    config = load_config(args.config)
    if args.fullscreen:
        config.setdefault("ui", {})["fullscreen"] = True

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("YakSperm Analyzer")
    app.setOrganizationName("HARL")

    # Apply dark stylesheet
    min_btn = config.get("ui", {}).get("touch_button_min_px", 60)
    app.setStyleSheet(get_stylesheet(min_btn))

    # Create and show main window
    window = MainWindow(config=config, mock=args.mock)
    window.show()

    logger.info("HMI ready — entering event loop")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
