"""
serial_handler.py — Thread-safe ESP32 JSON serial protocol handler.

Protocol:
  TX → ESP32:  {"cmd": "<action>", "value": <optional>}
  RX ← ESP32:  {"type": "ack"|"status"|"error", ...}

Runs in a dedicated QThread; emits signals for UI consumption.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


@dataclass
class SerialConfig:
    """Immutable serial configuration."""

    port: str = "/dev/ttyUSB0"
    baud: int = 115200
    timeout: float = 2.0
    reconnect_interval: float = 5.0


class SerialHandler(QThread):
    """
    Manages bidirectional JSON communication with the ESP32.

    Signals
    -------
    temperature_updated(float)
        Current thermal stage temperature in °C.
    status_received(dict)
        Full status payload from ESP32.
    ack_received(dict)
        Acknowledgement for a previously sent command.
    error_occurred(str)
        Human-readable error message.
    connection_changed(bool)
        True when connected, False on disconnect.
    """

    temperature_updated = pyqtSignal(float)
    status_received = pyqtSignal(dict)
    ack_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    connection_changed = pyqtSignal(bool)

    def __init__(
        self,
        config: SerialConfig,
        mock_port: Any | None = None,
        parent: Any | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._mock_port = mock_port
        self._port: Any | None = None
        self._running = False
        self._tx_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._lock = threading.Lock()

    # ── Public API (thread-safe) ─────────────────────────────────────────
    def send_command(self, cmd: str, **kwargs: Any) -> None:
        """Enqueue a command for transmission."""
        payload: dict[str, Any] = {"cmd": cmd}
        payload.update(kwargs)
        self._tx_queue.put(payload)
        logger.debug("TX enqueued: %s", payload)

    def set_temperature(self, target: float) -> None:
        self.send_command("set_temp", value=target)

    def heater_off(self) -> None:
        self.send_command("heater_off")

    def move_servo(self, position: int) -> None:
        self.send_command("servo_move", position=position)

    def ping(self) -> None:
        self.send_command("ping")

    def stop(self) -> None:
        self._running = False

    # ── QThread entry ────────────────────────────────────────────────────
    def run(self) -> None:  # noqa: C901
        self._running = True
        logger.info("SerialHandler thread started")

        while self._running:
            # Connect / reconnect loop
            if self._port is None or not getattr(self._port, "is_open", False):
                self._connect()
                if self._port is None:
                    time.sleep(self._config.reconnect_interval)
                    continue

            # ── Transmit queued commands ─────────────────────────────────
            while not self._tx_queue.empty():
                try:
                    payload = self._tx_queue.get_nowait()
                    raw = (json.dumps(payload) + "\n").encode("utf-8")
                    with self._lock:
                        self._port.write(raw)
                    logger.debug("TX sent: %s", payload)
                except Exception as exc:
                    logger.error("TX error: %s", exc)
                    self.error_occurred.emit(f"Serial TX error: {exc}")

            # ── Receive ──────────────────────────────────────────────────
            try:
                with self._lock:
                    line = self._port.readline()
                if line:
                    self._process_rx(line)
            except Exception as exc:
                logger.error("RX error: %s", exc)
                self.error_occurred.emit(f"Serial RX error: {exc}")
                self._disconnect()

            time.sleep(0.01)  # Yield

        self._disconnect()
        logger.info("SerialHandler thread stopped")

    # ── Private helpers ──────────────────────────────────────────────────
    def _connect(self) -> None:
        try:
            if self._mock_port is not None:
                self._port = self._mock_port
                self._port.open()
            else:
                import serial  # type: ignore[import-untyped]

                self._port = serial.Serial(
                    port=self._config.port,
                    baudrate=self._config.baud,
                    timeout=self._config.timeout,
                )
            self.connection_changed.emit(True)
            logger.info(
                "Connected to %s @ %d baud",
                self._config.port,
                self._config.baud,
            )
        except Exception as exc:
            logger.warning("Connection failed: %s", exc)
            self.error_occurred.emit(f"Cannot connect: {exc}")
            self._port = None
            self.connection_changed.emit(False)

    def _disconnect(self) -> None:
        if self._port and getattr(self._port, "is_open", False):
            try:
                self._port.close()
            except Exception:
                pass
        self._port = None
        self.connection_changed.emit(False)

    def _process_rx(self, raw: bytes) -> None:
        try:
            data = json.loads(raw.decode("utf-8").strip())
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("Unparseable RX: %r", raw)
            return

        msg_type = data.get("type", "")
        if msg_type == "status":
            temp = data.get("temp", 0.0)
            self.temperature_updated.emit(float(temp))
            self.status_received.emit(data)
        elif msg_type == "ack":
            self.ack_received.emit(data)
        elif msg_type == "pong":
            self.ack_received.emit(data)
        elif msg_type == "error":
            self.error_occurred.emit(data.get("msg", "ESP32 error"))
        else:
            logger.debug("Unknown RX type: %s", data)
