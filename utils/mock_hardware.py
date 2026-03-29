"""
mock_hardware.py — Simulated ESP32 + camera for desktop testing.

Provides drop-in replacements so `python main.py --mock` runs
the full UI flow without any physical hardware.
"""

from __future__ import annotations

import json
import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Mock Serial Port
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class MockSerialPort:
    """Simulates the ESP32 serial port with realistic thermal ramp."""

    port: str = "/dev/mock"
    baudrate: int = 115200
    timeout: float = 2.0
    is_open: bool = False

    # Internal state
    _temperature: float = field(default=25.0, repr=False)
    _target_temp: float = field(default=37.0, repr=False)
    _heater_on: bool = field(default=False, repr=False)
    _servo_pos: int = field(default=0, repr=False)
    _start_time: float = field(default_factory=time.time, repr=False)
    _buffer: list[bytes] = field(default_factory=list, repr=False)

    def open(self) -> None:
        self.is_open = True
        self._start_time = time.time()
        logger.info("MockSerialPort opened on %s", self.port)

    def close(self) -> None:
        self.is_open = False
        logger.info("MockSerialPort closed")

    def write(self, data: bytes) -> int:
        """Parse incoming JSON command and queue a response."""
        try:
            cmd = json.loads(data.decode("utf-8").strip())
            response = self._handle_command(cmd)
            self._buffer.append(
                (json.dumps(response) + "\n").encode("utf-8")
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("MockSerial bad data: %s", exc)
        return len(data)

    def readline(self) -> bytes:
        """Return the next queued response, or a periodic status."""
        if self._buffer:
            return self._buffer.pop(0)
        # Auto-generate a status heartbeat
        self._simulate_thermal()
        status = {
            "type": "status",
            "temp": round(self._temperature, 2),
            "heater": self._heater_on,
            "servo": self._servo_pos,
            "uptime_s": round(time.time() - self._start_time, 1),
        }
        time.sleep(0.05)  # Simulate serial latency
        return (json.dumps(status) + "\n").encode("utf-8")

    @property
    def in_waiting(self) -> int:
        return len(self._buffer)

    # ── Internal helpers ─────────────────────────────────────────────────
    def _simulate_thermal(self) -> None:
        """Simple first-order thermal model with noise."""
        if self._heater_on:
            diff = self._target_temp - self._temperature
            self._temperature += diff * 0.08 + random.gauss(0, 0.05)
        else:
            # Cool toward ambient ~22 °C
            self._temperature += (22.0 - self._temperature) * 0.02

    def _handle_command(self, cmd: dict[str, Any]) -> dict[str, Any]:
        action = cmd.get("cmd", "")
        if action == "set_temp":
            self._target_temp = cmd.get("value", 37.0)
            self._heater_on = True
            return {"type": "ack", "cmd": "set_temp", "status": "ok"}
        if action == "heater_off":
            self._heater_on = False
            return {"type": "ack", "cmd": "heater_off", "status": "ok"}
        if action == "servo_move":
            self._servo_pos = cmd.get("position", 0)
            return {"type": "ack", "cmd": "servo_move", "status": "ok"}
        if action == "ping":
            return {"type": "pong", "firmware": "mock-v1.0.0"}
        return {"type": "error", "msg": f"unknown cmd '{action}'"}


# ─────────────────────────────────────────────────────────────────────────────
# Mock Camera (generates synthetic sperm-like moving dots)
# ─────────────────────────────────────────────────────────────────────────────
class MockCamera:
    """Generates synthetic microscopy frames with moving particles."""

    def __init__(self, width: int = 1280, height: int = 720, fps: int = 30):
        self.width = width
        self.height = height
        self.fps = fps
        self._is_opened = False
        self._frame_count = 0
        self._particles = self._init_particles(40)

    def isOpened(self) -> bool:  # noqa: N802 – match OpenCV API
        return self._is_opened

    def open(self, index: int) -> bool:  # noqa: ARG002
        self._is_opened = True
        logger.info("MockCamera opened (index=%d)", index)
        return True

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self._is_opened:
            return False, None
        frame = self._render_frame()
        self._frame_count += 1
        return True, frame

    def release(self) -> None:
        self._is_opened = False

    def set(self, prop: int, value: float) -> bool:  # noqa: ARG002
        return True

    def get(self, prop: int) -> float:  # noqa: ARG002
        return 0.0

    # ── Particle simulation ──────────────────────────────────────────────
    def _init_particles(self, n: int) -> list[dict[str, float]]:
        particles = []
        for _ in range(n):
            particles.append({
                "x": random.uniform(40, self.width - 40),
                "y": random.uniform(40, self.height - 40),
                "vx": random.gauss(0, 2.5),
                "vy": random.gauss(0, 2.5),
                "radius": random.uniform(4, 8),
                "brightness": random.randint(180, 255),
                "phase": random.uniform(0, 2 * math.pi),
                "motile": random.random() < 0.65,  # ~65 % motile
            })
        return particles

    def _render_frame(self) -> np.ndarray:
        # Dark-field microscopy background
        frame = np.full(
            (self.height, self.width, 3), (12, 12, 18), dtype=np.uint8
        )
        # Add subtle noise
        noise = np.random.randint(0, 8, frame.shape, dtype=np.uint8)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(
            np.uint8
        )

        t = self._frame_count / max(self.fps, 1)
        for p in self._particles:
            if p["motile"]:
                # Sinusoidal wobble + drift
                p["x"] += p["vx"] + 1.5 * math.sin(t * 3 + p["phase"])
                p["y"] += p["vy"] + 1.0 * math.cos(t * 2.5 + p["phase"])
                # Random direction changes
                if random.random() < 0.03:
                    p["vx"] = random.gauss(0, 2.5)
                    p["vy"] = random.gauss(0, 2.5)
            else:
                # Non-motile: Brownian jitter only
                p["x"] += random.gauss(0, 0.3)
                p["y"] += random.gauss(0, 0.3)

            # Wrap around
            p["x"] %= self.width
            p["y"] %= self.height

            # Draw ellipse (sperm head approximation)
            cx, cy = int(p["x"]), int(p["y"])
            r = int(p["radius"])
            brightness = p["brightness"]
            # Simple filled circle via numpy slicing
            y_lo = max(cy - r, 0)
            y_hi = min(cy + r, self.height)
            x_lo = max(cx - r, 0)
            x_hi = min(cx + r, self.width)
            for yy in range(y_lo, y_hi):
                for xx in range(x_lo, x_hi):
                    if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                        frame[yy, xx] = (brightness, brightness, brightness)

            # Draw tail for motile
            if p["motile"] and r > 3:
                tail_len = int(r * 2.5)
                angle = math.atan2(p["vy"], p["vx"]) + math.pi
                for ti in range(tail_len):
                    tx = int(cx + ti * math.cos(angle + 0.3 * math.sin(t * 5 + ti * 0.3)))
                    ty = int(cy + ti * math.sin(angle + 0.3 * math.sin(t * 5 + ti * 0.3)))
                    if 0 <= tx < self.width and 0 <= ty < self.height:
                        val = max(60, brightness - ti * 8)
                        frame[ty, tx] = (val, val, val)

        return frame
