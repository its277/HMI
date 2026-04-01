"""
camera_thread.py — OpenCV camera capture in a QThread.

Emits each frame as a numpy array via a Qt signal so the UI and
AI pipeline can consume frames without blocking the event loop.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class CameraThread(QThread):
    """
    Captures frames from a camera (or MockCamera) and emits them.

    Signals
    -------
    frame_ready(np.ndarray)
        BGR frame as a NumPy array.
    fps_updated(float)
        Measured frames-per-second.
    error_occurred(str)
        Human-readable error string.
    """

    frame_ready = pyqtSignal(np.ndarray)
    fps_updated = pyqtSignal(float)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        camera_index: int = 0,
        width: int = 1280,
        height: int = 720,
        target_fps: int = 30,
        mock_camera: Any | None = None,
        parent: Any | None = None,
    ) -> None:
        super().__init__(parent)
        self._camera_index = camera_index
        self._width = width
        self._height = height
        self._target_fps = target_fps
        self._mock_camera = mock_camera
        self._running = False
        self._cap: Any | None = None

    # ── Public API ───────────────────────────────────────────────────────
    def stop(self) -> None:
        self._running = False

    # ── QThread entry ────────────────────────────────────────────────────
    def run(self) -> None:
        self._running = True
        self._open_camera()
        if self._cap is None or not self._cap.isOpened():
            self.error_occurred.emit("Failed to open camera")
            return

        interval = 1.0 / max(self._target_fps, 1)
        frame_count = 0
        fps_timer = time.perf_counter()

        logger.info("CameraThread started (index=%d)", self._camera_index)

        while self._running:
            t0 = time.perf_counter()
            ret, frame = self._cap.read()
            if not ret or frame is None:
                self.error_occurred.emit("Camera read failed")
                time.sleep(0.1)
                continue

            self.frame_ready.emit(frame)
            frame_count += 1

            # Calculate FPS every second
            elapsed = time.perf_counter() - fps_timer
            if elapsed >= 1.0:
                self.fps_updated.emit(frame_count / elapsed)
                frame_count = 0
                fps_timer = time.perf_counter()

            # Throttle to target FPS
            dt = time.perf_counter() - t0
            if dt < interval:
                time.sleep(interval - dt)

        self._release_camera()
        logger.info("CameraThread stopped")

    # ── Private helpers ──────────────────────────────────────────────────
    def _open_camera(self) -> None:
        if self._mock_camera is not None:
            self._cap = self._mock_camera
            self._cap.open(self._camera_index)
            logger.info("Using MockCamera")
        else:
            import cv2

            self._cap = cv2.VideoCapture(self._camera_index)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
            self._cap.set(cv2.CAP_PROP_FPS, 60)  # Capture at 60fps for frame decimation
            logger.info("OpenCV camera opened (index=%d, target=60fps)", self._camera_index)

    def _release_camera(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
