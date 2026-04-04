"""
main_window.py — QMainWindow with QStackedWidget hosting all 5 screens.

Orchestrates the state machine, serial handler, camera thread,
AI pipeline, video pipeline, and report generator.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QImage, QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from core.ai_pipeline import AIPipeline, AnalysisResult
from core.camera_thread import CameraThread
from core.report_generator import ReportGenerator
from core.serial_handler import SerialHandler
from core.state_machine import Event, State, StateMachine
from ui.screens import (
    AnalysisScreen,
    HistoryScreen,
    ResultsScreen,
    SetupScreen,
    SplashScreen,
)

logger = logging.getLogger(__name__)

# Screen indices
_SPLASH = 0
_SETUP = 1
_ANALYSIS = 2
_RESULTS = 3
_HISTORY = 4


class MainWindow(QMainWindow):
    """Top-level HMI window."""

    def __init__(
        self,
        config: dict[str, Any],
        mock: bool = False,
        pc_mode: bool = False,
        parent: Any | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._mock = mock
        self._pc_mode = pc_mode

        # Workers (initialized lazily)
        self._serial: SerialHandler | None = None
        self._camera: CameraThread | None = None
        self._pipeline: AIPipeline | None = None
        self._video_pipeline = None  # VideoPipeline (lazy import)
        self._report_gen: ReportGenerator | None = None

        # State
        self._fsm = StateMachine(self)
        self._captured_frames: list[np.ndarray] = []
        self._current_temp: float = 25.0
        self._temp_stable = False
        self._serial_connected = False
        self._last_result: AnalysisResult | None = None

        # Sample info (from splash screen)
        self._animal_id: str = ""
        self._sample_dilution: str = ""

        self._setup_window()
        self._build_screens()
        self._build_nav_bar()
        self._build_status_bar()
        self._connect_fsm()

    # ── Window setup ─────────────────────────────────────────────────────
    def _setup_window(self) -> None:
        title = "YakSperm Analyzer — HMI v3.0"
        if self._pc_mode:
            title += " [PC]"
        elif self._mock:
            title += " [MOCK]"
        self.setWindowTitle(title)
        ui_cfg = self._config.get("ui", {})
        w = ui_cfg.get("width", 1024)
        h = ui_cfg.get("height", 600)
        self.resize(w, h)
        if ui_cfg.get("fullscreen", False):
            self.showFullScreen()

    # ── Screens ──────────────────────────────────────────────────────────
    def _build_screens(self) -> None:
        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Nav placeholder (filled later)
        self._nav_widget = QWidget()
        root_layout.addWidget(self._nav_widget)

        self._stack = QStackedWidget()

        self._splash = SplashScreen()
        self._setup = SetupScreen()
        self._analysis = AnalysisScreen()
        self._results = ResultsScreen()
        self._history = HistoryScreen(
            reports_dir=self._config.get("report", {}).get("output_dir", "reports/")
        )

        # Set mock mode on analysis screen
        self._analysis.set_mock_mode(self._mock)

        self._stack.addWidget(self._splash)    # 0
        self._stack.addWidget(self._setup)     # 1
        self._stack.addWidget(self._analysis)  # 2
        self._stack.addWidget(self._results)   # 3
        self._stack.addWidget(self._history)   # 4

        root_layout.addWidget(self._stack)
        self.setCentralWidget(central)

        # Connect screen signals
        self._splash.start_requested.connect(self._on_start)
        self._setup.connect_serial.connect(self._on_connect_serial)
        self._setup.start_heating.connect(self._on_start_heating)
        self._setup.load_slide.connect(self._on_load_slide)
        self._setup.proceed_to_analysis.connect(self._on_proceed_to_analysis)
        self._analysis.capture_requested.connect(self._on_capture)
        self._analysis.cancel_requested.connect(self._on_cancel)
        self._analysis.upload_video_requested.connect(self._on_upload_video)
        self._results.generate_report.connect(self._on_generate_report)
        self._results.new_sample.connect(self._on_new_sample)
        self._results.go_home.connect(self._go_splash)
        self._history.go_home.connect(self._go_splash)

    # ── Navigation Bar ───────────────────────────────────────────────────
    def _build_nav_bar(self) -> None:
        layout = QHBoxLayout(self._nav_widget)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(4)
        self._nav_widget.setStyleSheet(
            "background: #ffffff; border-bottom: 1px solid #d0d5dd;"
        )

        nav_items = [
            ("Home", _SPLASH),
            ("Setup", _SETUP),
            ("Analysis", _ANALYSIS),
            ("Results", _RESULTS),
            ("History", _HISTORY),
        ]
        self._nav_buttons: list[QPushButton] = []
        for label, idx in nav_items:
            btn = QPushButton(label)
            btn.setMinimumHeight(32)
            btn.setMinimumWidth(80)
            btn.setFont(QFont("Inter", 11))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton { border: none; border-radius: 4px; padding: 4px 12px; "
                "background: transparent; color: #4b5563; font-weight: 500; }"
                "QPushButton:hover { background: #f0f2f5; color: #1a1a1a; }"
            )
            btn.clicked.connect(lambda checked, i=idx: self._navigate(i))
            layout.addWidget(btn)
            self._nav_buttons.append(btn)

        layout.addStretch()

        # Mode badge
        if self._mock:
            badge = QLabel("MOCK")
            badge.setStyleSheet(
                "color: #d97706; font-size: 10px; font-weight: 600; "
                "background: #fffbeb; padding: 2px 8px; border-radius: 4px; "
                "border: 1px solid #fde68a;"
            )
            layout.addWidget(badge)
        elif self._pc_mode:
            badge = QLabel("PC MODE")
            badge.setStyleSheet(
                "color: #2563eb; font-size: 10px; font-weight: 600; "
                "background: #eff6ff; padding: 2px 8px; border-radius: 4px; "
                "border: 1px solid #bfdbfe;"
            )
            layout.addWidget(badge)

    def _navigate(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)
        # Highlight active nav button
        for i, btn in enumerate(self._nav_buttons):
            if i == idx:
                btn.setStyleSheet(
                    "QPushButton { border: none; border-radius: 4px; padding: 4px 12px; "
                    "background: #2563eb; color: white; font-weight: 600; }"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { border: none; border-radius: 4px; padding: 4px 12px; "
                    "background: transparent; color: #4b5563; font-weight: 500; }"
                    "QPushButton:hover { background: #f0f2f5; color: #1a1a1a; }"
                )

    # ── Status Bar ───────────────────────────────────────────────────────
    def _build_status_bar(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)

        self._status_state = QLabel("State: IDLE")
        self._status_state.setStyleSheet("font-weight: 600; color: #1a1a1a; background: transparent;")
        sb.addWidget(self._status_state)

        self._status_temp = QLabel("Temp: —°C")
        self._status_temp.setStyleSheet("color: #4b5563; background: transparent;")
        sb.addWidget(self._status_temp)

        self._status_serial = QLabel("Serial: ●")
        self._status_serial.setStyleSheet("color: #dc2626; background: transparent;")
        sb.addPermanentWidget(self._status_serial)

    # ── FSM wiring ───────────────────────────────────────────────────────
    def _connect_fsm(self) -> None:
        self._fsm.state_changed.connect(self._on_state_changed)

    def _on_state_changed(self, old: State, new: State) -> None:
        self._status_state.setText(f"State: {new.name}")
        logger.info("State: %s → %s", old.name, new.name)

        # Auto-navigate on certain states
        if new == State.CONNECTING:
            self._navigate(_SETUP)
        elif new == State.CAPTURING:
            self._navigate(_ANALYSIS)
        elif new == State.RESULTS:
            self._navigate(_RESULTS)

    # ══════════════════════════════════════════════════════════════════════
    # ACTION HANDLERS
    # ══════════════════════════════════════════════════════════════════════

    def _on_start(self) -> None:
        """Splash → Setup. Read Animal ID and Dilution first."""
        # Capture sample info from splash screen
        self._animal_id = self._splash.animal_id
        self._sample_dilution = self._splash.sample_dilution
        logger.info(
            "Starting analysis — Animal ID: %s, Dilution: %s",
            self._animal_id, self._sample_dilution,
        )

        self._fsm.handle_event(Event.START)
        self._start_serial()
        self._start_camera()

    def _go_splash(self) -> None:
        self._navigate(_SPLASH)

    # ── Serial ───────────────────────────────────────────────────────────
    def _start_serial(self) -> None:
        if self._serial and self._serial.isRunning():
            return

        serial_cfg = self._config.get("serial", {})
        from core.serial_handler import SerialConfig

        cfg = SerialConfig(
            port=serial_cfg.get("port", "/dev/ttyUSB0"),
            baud=serial_cfg.get("baud", 115200),
            timeout=serial_cfg.get("timeout", 2.0),
            reconnect_interval=serial_cfg.get("reconnect_interval", 5.0),
        )

        mock_port = None
        if self._mock:
            from utils.mock_hardware import MockSerialPort
            mock_port = MockSerialPort(port=cfg.port, baudrate=cfg.baud)

        self._serial = SerialHandler(cfg, mock_port=mock_port, parent=self)
        self._serial.connection_changed.connect(self._on_serial_connection)
        self._serial.temperature_updated.connect(self._on_temperature)
        self._serial.ack_received.connect(self._on_serial_ack)
        self._serial.error_occurred.connect(self._on_serial_error)
        self._serial.start()

    def _on_connect_serial(self) -> None:
        self._start_serial()

    def _on_serial_connection(self, connected: bool) -> None:
        self._serial_connected = connected
        if self._mock:
            port_label = "Mock ESP32"
        elif self._pc_mode:
            port_label = f"PC — {self._config.get('serial', {}).get('port', '')}"
        else:
            port_label = ""
        self._setup.update_serial_status(connected, port_label)
        color = "#16a34a" if connected else "#dc2626"
        self._status_serial.setStyleSheet(f"color: {color}; background: transparent;")
        self._status_serial.setText(f"Serial: {'●' if connected else '○'}")
        if connected:
            self._fsm.handle_event(Event.CONNECTED)

    def _on_serial_ack(self, data: dict) -> None:
        cmd = data.get("cmd", "")
        if cmd == "servo_move":
            self._setup.update_slide_status(True)
            self._fsm.handle_event(Event.SLIDE_LOADED)
        elif cmd == "set_temp":
            logger.info("Heating started (ack)")

    def _on_serial_error(self, msg: str) -> None:
        logger.error("Serial error: %s", msg)
        self.statusBar().showMessage(f"⚠ {msg}", 5000)

    # ── Temperature ──────────────────────────────────────────────────────
    def _on_temperature(self, temp: float) -> None:
        self._current_temp = temp
        self._status_temp.setText(f"Temp: {temp:.1f}°C")
        target = self._config.get("thermal", {}).get("target_temp", 37.0)
        tolerance = self._config.get("thermal", {}).get("tolerance", 0.5)
        stable = abs(temp - target) <= tolerance
        self._temp_stable = stable
        self._setup.update_temperature(temp, stable)
        self._analysis.update_temperature(temp)
        if stable and self._fsm.state == State.THERMAL_WAIT:
            self._fsm.handle_event(Event.TEMP_STABLE)

    def _on_start_heating(self) -> None:
        if self._serial:
            target = self._config.get("thermal", {}).get("target_temp", 37.0)
            self._serial.set_temperature(target)
        # Move FSM forward
        if self._fsm.state == State.CONNECTING:
            self._fsm.handle_event(Event.CONNECTED)
        if self._fsm.state == State.CALIBRATING:
            self._fsm.handle_event(Event.CALIBRATED)

    def _on_load_slide(self) -> None:
        if self._serial:
            self._serial.move_servo(90)

    # ── Camera ───────────────────────────────────────────────────────────
    def _start_camera(self) -> None:
        if self._camera and self._camera.isRunning():
            return

        cam_cfg = self._config.get("camera", {})
        mock_cam = None
        if self._mock:
            from utils.mock_hardware import MockCamera
            mock_cam = MockCamera(
                width=cam_cfg.get("width", 1280),
                height=cam_cfg.get("height", 720),
                fps=cam_cfg.get("fps", 30),
            )

        self._camera = CameraThread(
            camera_index=cam_cfg.get("index", 0),
            width=cam_cfg.get("width", 1280),
            height=cam_cfg.get("height", 720),
            target_fps=cam_cfg.get("fps", 30),
            mock_camera=mock_cam,
            parent=self,
        )
        self._camera.frame_ready.connect(self._on_frame)
        self._camera.fps_updated.connect(self._on_fps)
        self._camera.error_occurred.connect(self._on_camera_error)
        self._camera.start()
        self._setup.update_camera_status(True, 0.0)

    def _on_frame(self, frame: np.ndarray) -> None:
        # Feed live view to analysis screen
        self._analysis.update_frame(frame)

        # Also update setup preview (downsampled)
        if self._stack.currentIndex() == _SETUP:
            h, w = frame.shape[:2]
            small = frame[::4, ::4]  # Quick downsample
            sh, sw, ch = small.shape
            rgb = small[..., ::-1].copy()
            qimg = QImage(rgb.data, sw, sh, ch * sw, QImage.Format.Format_RGB888)
            self._setup.update_camera_preview(QPixmap.fromImage(qimg))

        # Capture frames if in capture mode
        # Protocol: Record @60fps for 1s = 60 frames, then discard
        # odd frames (1,3,5...) keeping 30 even frames (0,2,4...)
        if self._fsm.state == State.CAPTURING:
            self._captured_frames.append(frame.copy())
            n_raw_target = 60  # 60 frames @60fps = 1 second
            n_final = 30       # Keep every other frame
            self._analysis.update_frame_count(
                len(self._captured_frames), n_raw_target
            )
            if len(self._captured_frames) >= n_raw_target:
                # Discard odd-indexed frames: keep 0,2,4,...,58
                self._captured_frames = [
                    f for i, f in enumerate(self._captured_frames[:n_raw_target])
                    if i % 2 == 0
                ]
                logger.info(
                    "Capture done: %d raw → %d even frames",
                    n_raw_target, len(self._captured_frames),
                )
                self._fsm.handle_event(Event.CAPTURE_DONE)
                self._run_pipeline()

    def _on_fps(self, fps: float) -> None:
        self._analysis.update_fps(fps)
        self._setup.update_camera_status(True, fps)

    def _on_camera_error(self, msg: str) -> None:
        logger.error("Camera error: %s", msg)
        self._setup.update_camera_status(False)

    # ── Capture / Analysis ───────────────────────────────────────────────
    def _on_proceed_to_analysis(self) -> None:
        # Allow proceeding to analysis view
        self._navigate(_ANALYSIS)
        if self._fsm.state == State.SLIDE_LOADING:
            self._fsm.handle_event(Event.SLIDE_LOADED)

    def _on_capture(self) -> None:
        self._captured_frames.clear()
        self._analysis.set_capturing(True)
        if self._fsm.state != State.CAPTURING:
            # Force into capturing state
            if self._fsm.state in (State.SLIDE_LOADING, State.THERMAL_WAIT):
                self._fsm.handle_event(Event.TEMP_STABLE)
                self._fsm.handle_event(Event.SLIDE_LOADED)
            # Try direct
            old = self._fsm._state
            self._fsm._state = State.CAPTURING
            self._fsm.state_changed.emit(old, State.CAPTURING)

    def _on_cancel(self) -> None:
        self._analysis.set_capturing(False)
        self._analysis.set_analysing(False)
        if self._pipeline:
            self._pipeline.stop()
        if self._video_pipeline:
            self._video_pipeline.stop()
        self._captured_frames.clear()
        self._fsm.reset()
        self._navigate(_SETUP)

    def _run_pipeline(self) -> None:
        self._analysis.set_capturing(False)
        self._analysis.set_analysing(True)

        models_cfg = self._config.get("models", {})
        ukf_cfg = self._config.get("ukf", {})
        pipeline_config = {**models_cfg, **ukf_cfg}

        self._pipeline = AIPipeline(
            frames=self._captured_frames.copy(),
            config=pipeline_config,
            mock=self._mock,
            parent=self,
        )
        self._pipeline.stage_changed.connect(self._analysis.update_pipeline_stage)
        self._pipeline.progress_updated.connect(self._analysis.update_progress)
        self._pipeline.detection_frame.connect(self._on_detection_frame)
        self._pipeline.analysis_complete.connect(self._on_analysis_complete)
        self._pipeline.error_occurred.connect(self._on_pipeline_error)
        self._pipeline.start()

    def _on_detection_frame(self, frame: np.ndarray, detections: list) -> None:
        self._analysis.update_detection_count(len(detections))
        self._analysis.update_frame(frame)

    def _on_analysis_complete(self, result: AnalysisResult) -> None:
        self._last_result = result
        self._analysis.set_analysing(False)
        self._fsm.handle_event(Event.ANALYSIS_DONE)
        self._results.display_results(
            result,
            animal_id=self._animal_id,
            sample_dilution=self._sample_dilution,
        )
        self._navigate(_RESULTS)

    def _on_pipeline_error(self, msg: str) -> None:
        logger.error("Pipeline error: %s", msg)
        self._analysis.set_analysing(False)
        self.statusBar().showMessage(f"⚠ Pipeline error: {msg}", 8000)

    # ── Upload Video (Mock Mode) ─────────────────────────────────────────
    def _on_upload_video(self) -> None:
        """Open file dialog, run video through the real analysis pipeline."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video for Analysis",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)",
        )
        if not filepath:
            return

        logger.info("Uploading video for analysis: %s", filepath)
        self._analysis.set_analysing(True)
        self.statusBar().showMessage(f"Processing video: {filepath}", 5000)

        from core.video_pipeline import VideoPipeline

        self._video_pipeline = VideoPipeline(
            video_path=filepath,
            model_dir="models",
            parent=self,
        )
        self._video_pipeline.stage_changed.connect(
            self._analysis.update_pipeline_stage
        )
        self._video_pipeline.progress_updated.connect(
            self._analysis.update_progress
        )
        self._video_pipeline.detection_frame.connect(
            self._on_detection_frame
        )
        self._video_pipeline.analysis_complete.connect(
            self._on_analysis_complete
        )
        self._video_pipeline.error_occurred.connect(
            self._on_pipeline_error
        )
        self._video_pipeline.start()

    # ── Report ───────────────────────────────────────────────────────────
    def _on_generate_report(self) -> None:
        if self._last_result is None:
            return
        self._results.set_report_generating(True)
        report_cfg = self._config.get("report", {})

        self._report_gen = ReportGenerator(
            result=self._last_result,
            config=report_cfg,
            animal_id=self._animal_id,
            sample_dilution=self._sample_dilution,
            parent=self,
        )
        self._report_gen.progress_updated.connect(
            lambda p: self.statusBar().showMessage(f"Generating report… {p}%")
        )
        self._report_gen.report_ready.connect(self._on_report_ready)
        self._report_gen.error_occurred.connect(self._on_report_error)
        self._report_gen.start()

    def _on_report_ready(self, filepath: str) -> None:
        self._results.set_report_done(filepath)
        self._fsm.handle_event(Event.REPORT_DONE)
        self.statusBar().showMessage(f"✅ Report saved: {filepath}", 10000)

        # Generate QR code data and show on results screen
        sample_id = self._report_gen.sample_id if self._report_gen else ""
        r = self._last_result
        if r:
            # If ESP32 serial is connected, encode a network download URL
            if self._serial_connected:
                import socket
                try:
                    hostname = socket.gethostname()
                    local_ip = socket.gethostbyname(hostname)
                except Exception:
                    local_ip = "127.0.0.1"
                import os
                report_filename = os.path.basename(filepath)
                qr_data = f"http://{local_ip}:8080/reports/{report_filename}"
            else:
                qr_data = (
                    f"SampleID:{sample_id}"
                    f"|Motility:{r.total_motility_pct}%"
                    f"|Morphology:{r.normal_morphology_pct}%"
                )
            self._results.show_qr_code(qr_data)

    def _on_report_error(self, msg: str) -> None:
        self._results.set_report_generating(False)
        self.statusBar().showMessage(f"⚠ Report error: {msg}", 8000)

    # ── New Sample ───────────────────────────────────────────────────────
    def _on_new_sample(self) -> None:
        self._captured_frames.clear()
        self._last_result = None
        self._animal_id = ""
        self._sample_dilution = ""
        self._splash.reset_inputs()
        self._fsm.handle_event(Event.NEW_SAMPLE)
        self._navigate(_SPLASH)

    # ── Cleanup ──────────────────────────────────────────────────────────
    def closeEvent(self, event: Any) -> None:
        logger.info("Shutting down…")
        if self._camera:
            self._camera.stop()
            self._camera.wait(2000)
        if self._serial:
            self._serial.stop()
            self._serial.wait(2000)
        if self._pipeline:
            self._pipeline.stop()
            self._pipeline.wait(2000)
        if self._video_pipeline:
            self._video_pipeline.stop()
            self._video_pipeline.wait(2000)
        super().closeEvent(event)
