"""
ai_pipeline.py — 3-stage AI analysis pipeline (QThread worker).

Stage 1: YOLOv11 object detection & tracking  (sperm-head localization)
Stage 2: Unscented Kalman Filter (UKF)         (motility parameters)
Stage 3: EfficientNet-B0                        (morphology classification)

In --mock mode, all stages produce synthetic results.
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Data classes for pipeline results
# ═════════════════════════════════════════════════════════════════════════════
class MotilityGrade(Enum):
    PROGRESSIVE = auto()
    NON_PROGRESSIVE = auto()
    IMMOTILE = auto()


class MorphologyClass(Enum):
    NORMAL = auto()
    HEAD_DEFECT = auto()
    MIDPIECE_DEFECT = auto()
    TAIL_DEFECT = auto()


@dataclass
class Detection:
    """Single sperm detection within a frame."""
    track_id: int
    x: float
    y: float
    w: float
    h: float
    confidence: float


@dataclass
class TrackMotility:
    """Motility parameters extracted by UKF for one tracked cell."""
    track_id: int
    vsl: float = 0.0   # Straight-line velocity (µm/s)
    vcl: float = 0.0   # Curvilinear velocity (µm/s)
    vap: float = 0.0   # Average path velocity (µm/s)
    lin: float = 0.0   # Linearity = VSL/VCL
    alh: float = 0.0   # Amplitude of lateral head displacement (µm)
    bcf: float = 0.0   # Beat-cross frequency (Hz)
    grade: MotilityGrade = MotilityGrade.IMMOTILE


@dataclass
class MorphologyResult:
    """Morphology classification for one cell."""
    track_id: int
    classification: MorphologyClass = MorphologyClass.NORMAL
    confidence: float = 0.0


@dataclass
class AnalysisResult:
    """Aggregated analysis output."""
    total_cells: int = 0
    motile_cells: int = 0
    progressive_cells: int = 0
    total_motility_pct: float = 0.0
    progressive_motility_pct: float = 0.0
    avg_vcl: float = 0.0
    avg_vsl: float = 0.0
    avg_vap: float = 0.0
    avg_lin: float = 0.0
    normal_morphology_pct: float = 0.0
    concentration: float = 0.0  # million/mL (estimated)
    tracks: list[TrackMotility] = field(default_factory=list)
    morphologies: list[MorphologyResult] = field(default_factory=list)
    detections_per_frame: list[list[Detection]] = field(default_factory=list)
    analysis_duration_s: float = 0.0
    timestamp: str = ""


# ═════════════════════════════════════════════════════════════════════════════
# AI Pipeline Worker
# ═════════════════════════════════════════════════════════════════════════════
class AIPipeline(QThread):
    """
    Three-stage analysis pipeline running on collected frames.

    Signals
    -------
    stage_changed(str)
        Current stage name ("detection", "motility", "morphology", "done").
    progress_updated(int)
        Overall progress 0-100.
    detection_frame(np.ndarray, list)
        Annotated frame + detections for live overlay.
    analysis_complete(AnalysisResult)
        Final aggregated result.
    error_occurred(str)
        Error description.
    """

    stage_changed = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    detection_frame = pyqtSignal(np.ndarray, list)
    analysis_complete = pyqtSignal(object)  # AnalysisResult
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        frames: list[np.ndarray],
        config: dict[str, Any],
        mock: bool = False,
        parent: Any | None = None,
    ) -> None:
        super().__init__(parent)
        self._frames = frames
        self._config = config
        self._mock = mock
        self._running = False

    def stop(self) -> None:
        self._running = False

    # ── QThread entry ────────────────────────────────────────────────────
    def run(self) -> None:
        self._running = True
        t0 = time.time()
        logger.info("AIPipeline started (%d frames, mock=%s)", len(self._frames), self._mock)

        try:
            # Stage 1: Detection & Tracking
            self.stage_changed.emit("detection")
            detections = self._stage_detection()
            if not self._running:
                return
            self.progress_updated.emit(40)

            # Stage 2: UKF Motility
            self.stage_changed.emit("motility")
            tracks = self._stage_motility(detections)
            if not self._running:
                return
            self.progress_updated.emit(70)

            # Stage 3: Morphology
            self.stage_changed.emit("morphology")
            morphologies = self._stage_morphology(detections)
            if not self._running:
                return
            self.progress_updated.emit(95)

            # Aggregate
            result = self._aggregate(tracks, morphologies, detections)
            result.analysis_duration_s = round(time.time() - t0, 2)
            result.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

            self.progress_updated.emit(100)
            self.stage_changed.emit("done")
            self.analysis_complete.emit(result)
            logger.info("Analysis complete in %.1fs", result.analysis_duration_s)

        except Exception as exc:
            logger.exception("Pipeline error")
            self.error_occurred.emit(str(exc))

    # ── Stage 1: Detection ───────────────────────────────────────────────
    def _stage_detection(self) -> list[list[Detection]]:
        all_detections: list[list[Detection]] = []
        n_frames = len(self._frames)

        if self._mock:
            # Generate synthetic detections
            n_cells = random.randint(25, 50)
            base_positions = [
                (random.uniform(50, 1230), random.uniform(50, 670))
                for _ in range(n_cells)
            ]
            for i, frame in enumerate(self._frames):
                if not self._running:
                    return all_detections
                frame_dets: list[Detection] = []
                for tid, (bx, by) in enumerate(base_positions):
                    x = bx + random.gauss(0, 3) + i * random.gauss(0, 1)
                    y = by + random.gauss(0, 3) + i * random.gauss(0, 1)
                    frame_dets.append(Detection(
                        track_id=tid, x=x, y=y,
                        w=random.uniform(12, 20), h=random.uniform(12, 20),
                        confidence=random.uniform(0.6, 0.98),
                    ))
                all_detections.append(frame_dets)
                pct = int(10 + (i / max(n_frames, 1)) * 25)
                self.progress_updated.emit(pct)
                # Emit annotated frame
                if i % 5 == 0:
                    self.detection_frame.emit(frame, frame_dets)
                time.sleep(0.01)
        else:
            # Real YOLO inference (placeholder)
            logger.info("Loading YOLO model from %s", self._config.get("yolo_weights", ""))
            # model = YOLO(self._config["yolo_weights"])
            for i, frame in enumerate(self._frames):
                if not self._running:
                    return all_detections
                # results = model.track(frame, persist=True, conf=...)
                # Parse results into Detection objects
                all_detections.append([])  # placeholder
                pct = int(10 + (i / max(n_frames, 1)) * 25)
                self.progress_updated.emit(pct)

        return all_detections

    # ── Stage 2: UKF Motility ────────────────────────────────────────────
    def _stage_motility(self, detections: list[list[Detection]]) -> list[TrackMotility]:
        tracks: list[TrackMotility] = []

        if not detections:
            return tracks

        # Gather unique track IDs
        all_ids: set[int] = set()
        for frame_dets in detections:
            for d in frame_dets:
                all_ids.add(d.track_id)

        dt = self._config.get("dt", 0.033)
        pixel_to_um = 0.5  # Calibration: µm per pixel

        if self._mock:
            for tid in all_ids:
                if not self._running:
                    return tracks
                # Gather positions across frames
                positions = [
                    (d.x, d.y)
                    for frame_dets in detections
                    for d in frame_dets
                    if d.track_id == tid
                ]
                if len(positions) < 5:
                    tracks.append(TrackMotility(track_id=tid, grade=MotilityGrade.IMMOTILE))
                    continue

                # Compute mock CASA parameters
                dists = [
                    math.hypot(positions[i + 1][0] - positions[i][0],
                               positions[i + 1][1] - positions[i][1])
                    for i in range(len(positions) - 1)
                ]
                total_dist = sum(dists) * pixel_to_um
                straight_dist = math.hypot(
                    positions[-1][0] - positions[0][0],
                    positions[-1][1] - positions[0][1],
                ) * pixel_to_um
                duration = len(positions) * dt

                vcl = total_dist / max(duration, 0.001)
                vsl = straight_dist / max(duration, 0.001)
                vap = (vcl + vsl) / 2
                lin = vsl / max(vcl, 0.001)

                if vcl > 25:
                    grade = MotilityGrade.PROGRESSIVE
                elif vcl > 5:
                    grade = MotilityGrade.NON_PROGRESSIVE
                else:
                    grade = MotilityGrade.IMMOTILE

                tracks.append(TrackMotility(
                    track_id=tid, vcl=round(vcl, 1), vsl=round(vsl, 1),
                    vap=round(vap, 1), lin=round(lin, 3),
                    alh=round(random.uniform(1.0, 5.0), 1),
                    bcf=round(random.uniform(5.0, 25.0), 1),
                    grade=grade,
                ))
            time.sleep(0.3)
        else:
            # Real UKF implementation (placeholder)
            logger.info("Running UKF motility analysis on %d tracks", len(all_ids))

        return tracks

    # ── Stage 3: Morphology ──────────────────────────────────────────────
    def _stage_morphology(self, detections: list[list[Detection]]) -> list[MorphologyResult]:
        morphologies: list[MorphologyResult] = []

        if not detections:
            return morphologies

        all_ids: set[int] = set()
        for frame_dets in detections:
            for d in frame_dets:
                all_ids.add(d.track_id)

        if self._mock:
            classes = list(MorphologyClass)
            weights = [0.72, 0.12, 0.08, 0.08]  # ~72% normal
            for tid in all_ids:
                if not self._running:
                    return morphologies
                cls = random.choices(classes, weights=weights, k=1)[0]
                morphologies.append(MorphologyResult(
                    track_id=tid,
                    classification=cls,
                    confidence=round(random.uniform(0.65, 0.99), 3),
                ))
            time.sleep(0.2)
        else:
            # Real EfficientNet inference (placeholder)
            logger.info("Loading EfficientNet from %s", self._config.get("efficientnet_weights", ""))

        return morphologies

    # ── Aggregation ──────────────────────────────────────────────────────
    def _aggregate(
        self,
        tracks: list[TrackMotility],
        morphologies: list[MorphologyResult],
        detections: list[list[Detection]],
    ) -> AnalysisResult:
        total = len(tracks)
        motile = sum(1 for t in tracks if t.grade != MotilityGrade.IMMOTILE)
        progressive = sum(1 for t in tracks if t.grade == MotilityGrade.PROGRESSIVE)
        normal = sum(1 for m in morphologies if m.classification == MorphologyClass.NORMAL)

        vcl_vals = [t.vcl for t in tracks if t.vcl > 0]
        vsl_vals = [t.vsl for t in tracks if t.vsl > 0]
        vap_vals = [t.vap for t in tracks if t.vap > 0]
        lin_vals = [t.lin for t in tracks if t.lin > 0]

        return AnalysisResult(
            total_cells=total,
            motile_cells=motile,
            progressive_cells=progressive,
            total_motility_pct=round(100 * motile / max(total, 1), 1),
            progressive_motility_pct=round(100 * progressive / max(total, 1), 1),
            avg_vcl=round(sum(vcl_vals) / max(len(vcl_vals), 1), 1),
            avg_vsl=round(sum(vsl_vals) / max(len(vsl_vals), 1), 1),
            avg_vap=round(sum(vap_vals) / max(len(vap_vals), 1), 1),
            avg_lin=round(sum(lin_vals) / max(len(lin_vals), 1), 3),
            normal_morphology_pct=round(100 * normal / max(len(morphologies), 1), 1),
            concentration=round(random.uniform(15, 80), 1) if self._mock else 0.0,
            tracks=tracks,
            morphologies=morphologies,
            detections_per_frame=detections,
        )
