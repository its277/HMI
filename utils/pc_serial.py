"""
pc_serial.py — PC/Laptop serial port auto-detection for ESP32.

Automatically discovers the correct serial port for ESP32 communication
on desktop platforms (Linux / Windows) as opposed to the fixed Jetson
Nano hardware UART pin (/dev/ttyTHS1).

Used by the ``--pc`` launch mode.
"""

from __future__ import annotations

import glob
import logging
import platform
from typing import Any

logger = logging.getLogger(__name__)

# Known USB-to-serial chipset keywords found in ESP32 dev-board descriptors
_ESP32_KEYWORDS: list[str] = [
    "cp210",        # Silicon Labs CP2102 / CP2104
    "ch340",        # WCH CH340
    "ch341",        # WCH CH341
    "ftdi",         # FTDI FT232
    "usb serial",   # Generic USB-serial
    "usb-serial",
    "esp32",
    "espressif",
    "uart",
]


def get_platform_default() -> str:
    """Return the platform-appropriate fallback serial port."""
    system = platform.system()
    if system == "Windows":
        return "COM3"
    elif system == "Darwin":
        return "/dev/tty.usbserial-0001"
    else:  # Linux
        return "/dev/ttyUSB0"


def list_available_ports() -> list[dict[str, str]]:
    """List all available serial ports with metadata (requires pyserial)."""
    try:
        from serial.tools import list_ports

        return [
            {
                "device": p.device or "",
                "description": p.description or "",
                "manufacturer": p.manufacturer or "",
                "hwid": p.hwid or "",
            }
            for p in list_ports.comports()
        ]
    except ImportError:
        return []


def detect_serial_port(fallback: str | None = None) -> str:
    """
    Auto-detect the ESP32 serial port on a PC / laptop.

    Strategy
    --------
    1. Use ``serial.tools.list_ports`` to enumerate COM / tty devices.
    2. Match against known ESP32 USB-serial chipset keywords.
    3. If no keyword match, pick the first USB-serial port found.
    4. If ``list_ports`` is unavailable, glob /dev/ttyUSB* and /dev/ttyACM*.
    5. Fall back to the platform default (``/dev/ttyUSB0`` or ``COM3``).

    Parameters
    ----------
    fallback : str or None
        Explicit fallback port.  If *None*, a platform default is used.

    Returns
    -------
    str
        Detected (or fallback) serial port path.
    """
    if fallback is None:
        fallback = get_platform_default()

    # ── 1. Try pyserial port enumeration ─────────────────────────────────
    try:
        from serial.tools import list_ports

        ports = list(list_ports.comports())
    except ImportError:
        logger.warning("pyserial list_ports unavailable; falling back to glob")
        ports = []

    if ports:
        # Keyword-based match
        for port in ports:
            combined = " ".join(
                filter(None, [port.description, port.manufacturer, port.hwid])
            ).lower()
            for kw in _ESP32_KEYWORDS:
                if kw in combined:
                    logger.info(
                        "Auto-detected ESP32 port: %s (%s)",
                        port.device,
                        port.description,
                    )
                    return port.device  # type: ignore[return-value]

        # No keyword hit — pick the first USB-serial / COM port
        for port in ports:
            dev: str = port.device or ""
            if any(
                pat in dev
                for pat in ("/dev/ttyUSB", "/dev/ttyACM", "COM")
            ):
                logger.info(
                    "Using first USB-serial port: %s (%s)",
                    port.device,
                    port.description,
                )
                return dev

        # Absolute last resort among enumerated ports
        logger.info("Using first enumerated port: %s", ports[0].device)
        return ports[0].device  # type: ignore[return-value]

    # ── 2. Glob-based fallback (Linux only) ──────────────────────────────
    if platform.system() == "Linux":
        candidates = sorted(
            glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
        )
        if candidates:
            logger.info("Glob-detected serial port: %s", candidates[0])
            return candidates[0]

    logger.warning("No serial ports detected — using fallback: %s", fallback)
    return fallback
