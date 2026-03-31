"""
video_pipeline.py — Offline video analysis pipeline (QThread worker).

Processes a pre-recorded video file through:
  Stage 1: YOLOv11 OBB detection + SORT tracking
  Stage 2: Motility analysis (distance-based from tracked positions)
  Stage 3: EfficientNet-V2-L morphology classification (normal vs bent_tail)

Adapted from the oldproject/ pipeline to produce AnalysisResult objects
compatible with the HMI results screen.
"""

from __future__ import annotations

import logging
import math
import os
import time
from typing import Any

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from core.ai_pipeline import (
    AnalysisResult,
    Detection,
    MorphologyClass,
    MorphologyResult,
    MotilityGrade,
    TrackMotility,
)

logger = logging.getLogger(__name__)

# ── Constants (from old project) ─────────────────────────────────────────────
MOTILITY_FRAME_WINDOW = 20
MOTILITY_DISTANCE_THRESHOLD = 0.01
BENT_TAIL_THRESHOLD = 0.95
CONCENTRATION_MULTIPLIER = 5.476
PIXEL_TO_UM = 0.5  # Calibration: µm per pixel


class VideoPipeline(QThread):
    """
    Processes a video file through the full analysis pipeline.

    Signals
    -------
    stage_changed(str)
        Current stage name.
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
        video_path: str,
        model_dir: str = "models",
        parent: Any | None = None,
    ) -> None:
        super().__init__(parent)
        self._video_path = video_path
        self._model_dir = model_dir
        self._running = False

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        self._running = True
        t0 = time.time()
        logger.info("VideoPipeline started: %s", self._video_path)

        try:
            # ── Load Models ──────────────────────────────────────────────
            self.stage_changed.emit("detection")
            self.progress_updated.emit(5)

            yolo_path = os.path.join(self._model_dir, "best.pt")
            enet_path = os.path.join(
                self._model_dir, "efficientnetv2_l_sperm_morphology2.pth"
            )

            if not os.path.exists(yolo_path):
                self.error_occurred.emit(f"YOLO model not found: {yolo_path}")
                return
            if not os.path.exists(enet_path):
                self.error_occurred.emit(f"EfficientNet model not found: {enet_path}")
                return

            # Import heavy deps inside thread
            import torch
            from torchvision import transforms
            from torchvision.models import efficientnet_v2_l
            from ultralytics import YOLO

            model = YOLO(yolo_path)
            logger.info("YOLO model loaded. Classes: %s", model.names)

            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            classifier = efficientnet_v2_l(weights=None)
            classifier.classifier[1] = torch.nn.Linear(
                classifier.classifier[1].in_features, 2
            )
            classifier.load_state_dict(torch.load(enet_path, map_location=device))
            classifier.eval()
            classifier.to(device)
            logger.info("EfficientNet classifier loaded on %s", device)

            preprocess = transforms.Compose([
                transforms.ToPILImage(),
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ])

            self.progress_updated.emit(10)

            # ── Initialize Tracker ───────────────────────────────────────
            tracker = self._create_tracker()

            # ── Open Video ───────────────────────────────────────────────
            cap = cv2.VideoCapture(self._video_path)
            if not cap.isOpened():
                self.error_occurred.emit(f"Cannot open video: {self._video_path}")
                return

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            dt = 1.0 / fps

            # ── Processing Loop ──────────────────────────────────────────
            tracked_sperms: dict[int, dict] = {}
            all_seen_ids: set[int] = set()
            bent_ids: set[int] = set()
            motile_ids: set[int] = set()
            total_sperm_count = 0
            bent_tail_count = 0
            motile_sperm_count = 0

            all_detections: list[list[Detection]] = []
            frame_idx = 0

            while self._running:
                ret, frame = cap.read()
                if not ret:
                    break

                # YOLO detection
                results = model.predict(frame, verbose=False)

                detections_raw = []
                if (results[0].obb is not None
                        and hasattr(results[0].obb, "cls")):
                    for obb in results[0].obb:
                        cls_id = int(obb.cls[0].cpu().numpy())
                        if cls_id == 1:  # Sperm class
                            xyxy = obb.xyxy[0].cpu().numpy().astype(int)
                            conf = float(obb.conf[0].cpu().numpy())
                            detections_raw.append([
                                xyxy[0], xyxy[1], xyxy[2], xyxy[3], conf
                            ])

                dets_np = (
                    np.array(detections_raw)
                    if detections_raw
                    else np.empty((0, 5))
                )
                tracked_objects = tracker.update(dets_np)

                frame_dets: list[Detection] = []

                for obj in tracked_objects:
                    x1, y1, x2, y2, obj_id = map(int, obj)
                    obj_id = int(obj_id)

                    if obj_id not in all_seen_ids:
                        all_seen_ids.add(obj_id)
                        total_sperm_count += 1

                        # Morphology classification
                        morphology = "normal"
                        patch = frame[max(0, y1):max(0, y2),
                                      max(0, x1):max(0, x2)]
                        if patch.size > 0:
                            try:
                                patch_tensor = (
                                    preprocess(patch).unsqueeze(0).to(device)
                                )
                                with torch.no_grad():
                                    output = classifier(patch_tensor)
                                    probs = torch.softmax(output, dim=1)
                                    if (output.argmax(1).item() == 1
                                            and probs[0][1].item()
                                            >= BENT_TAIL_THRESHOLD):
                                        morphology = "bent_tail"
                            except Exception as e:
                                logger.warning("Morphology error: %s", e)

                        if morphology == "bent_tail" and obj_id not in bent_ids:
                            bent_ids.add(obj_id)
                            bent_tail_count += 1

                        tracked_sperms[obj_id] = {
                            "positions": [],
                            "is_bent": obj_id in bent_ids,
                            "is_motile": False,
                            "morphology": morphology,
                        }

                    tracked_sperms[obj_id]["positions"].append(
                        (frame_idx, (x1 + x2) // 2, (y1 + y2) // 2)
                    )

                    # Motility check
                    if (not tracked_sperms[obj_id]["is_motile"]
                            and len(tracked_sperms[obj_id]["positions"])
                            > MOTILITY_FRAME_WINDOW):
                        pos = tracked_sperms[obj_id]["positions"]
                        distance = math.sqrt(
                            (pos[-1][1] - pos[0][1]) ** 2
                            + (pos[-1][2] - pos[0][2]) ** 2
                        )
                        if (distance > MOTILITY_DISTANCE_THRESHOLD
                                and obj_id not in motile_ids):
                            tracked_sperms[obj_id]["is_motile"] = True
                            motile_ids.add(obj_id)
                            motile_sperm_count += 1
                        pos.pop(0)

                    # Detection for HMI overlay
                    frame_dets.append(Detection(
                        track_id=obj_id,
                        x=float((x1 + x2) / 2),
                        y=float((y1 + y2) / 2),
                        w=float(x2 - x1),
                        h=float(y2 - y1),
                        confidence=0.9,
                    ))

                    # Draw on frame
                    color = (0, 255, 0)
                    if tracked_sperms[obj_id]["is_bent"]:
                        color = (0, 0, 255)
                    if tracked_sperms[obj_id]["is_motile"]:
                        color = (255, 0, 0)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                all_detections.append(frame_dets)

                # Progress & live frame
                if total_frames > 0:
                    pct = int(10 + (frame_idx / total_frames) * 80)
                    self.progress_updated.emit(min(pct, 90))

                if frame_idx % 3 == 0:
                    self.detection_frame.emit(frame, frame_dets)

                frame_idx += 1

            cap.release()

            if not self._running:
                return

            # ── Build AnalysisResult ─────────────────────────────────────
            self.stage_changed.emit("motility")
            self.progress_updated.emit(92)

            # Build TrackMotility for each tracked sperm
            tracks: list[TrackMotility] = []
            for tid, info in tracked_sperms.items():
                positions = info["positions"]
                if len(positions) < 5:
                    tracks.append(TrackMotility(
                        track_id=tid, grade=MotilityGrade.IMMOTILE
                    ))
                    continue

                # Compute CASA-like parameters
                dists = [
                    math.hypot(
                        positions[i + 1][1] - positions[i][1],
                        positions[i + 1][2] - positions[i][2],
                    )
                    for i in range(len(positions) - 1)
                ]
                total_dist = sum(dists) * PIXEL_TO_UM
                straight_dist = math.hypot(
                    positions[-1][1] - positions[0][1],
                    positions[-1][2] - positions[0][2],
                ) * PIXEL_TO_UM
                duration = len(positions) * dt

                vcl = total_dist / max(duration, 0.001)
                vsl = straight_dist / max(duration, 0.001)
                vap = (vcl + vsl) / 2
                lin = vsl / max(vcl, 0.001)

                if info["is_motile"] and vcl > 25:
                    grade = MotilityGrade.PROGRESSIVE
                elif info["is_motile"]:
                    grade = MotilityGrade.NON_PROGRESSIVE
                else:
                    grade = MotilityGrade.IMMOTILE

                tracks.append(TrackMotility(
                    track_id=tid,
                    vcl=round(vcl, 1),
                    vsl=round(vsl, 1),
                    vap=round(vap, 1),
                    lin=round(lin, 3),
                    alh=0.0,
                    bcf=0.0,
                    grade=grade,
                ))

            self.stage_changed.emit("morphology")
            self.progress_updated.emit(95)

            # Build MorphologyResult
            morphologies: list[MorphologyResult] = []
            for tid, info in tracked_sperms.items():
                if info["morphology"] == "bent_tail":
                    cls = MorphologyClass.TAIL_DEFECT
                else:
                    cls = MorphologyClass.NORMAL
                morphologies.append(MorphologyResult(
                    track_id=tid,
                    classification=cls,
                    confidence=0.9,
                ))

            # Aggregate
            total = len(tracks)
            motile = sum(
                1 for t in tracks if t.grade != MotilityGrade.IMMOTILE
            )
            progressive = sum(
                1 for t in tracks if t.grade == MotilityGrade.PROGRESSIVE
            )
            normal = sum(
                1 for m in morphologies
                if m.classification == MorphologyClass.NORMAL
            )

            vcl_vals = [t.vcl for t in tracks if t.vcl > 0]
            vsl_vals = [t.vsl for t in tracks if t.vsl > 0]
            vap_vals = [t.vap for t in tracks if t.vap > 0]
            lin_vals = [t.lin for t in tracks if t.lin > 0]

            concentration = round(
                total_sperm_count * CONCENTRATION_MULTIPLIER, 1
            )

            result = AnalysisResult(
                total_cells=total,
                motile_cells=motile,
                progressive_cells=progressive,
                total_motility_pct=round(
                    100 * motile / max(total, 1), 1
                ),
                progressive_motility_pct=round(
                    100 * progressive / max(total, 1), 1
                ),
                avg_vcl=round(
                    sum(vcl_vals) / max(len(vcl_vals), 1), 1
                ),
                avg_vsl=round(
                    sum(vsl_vals) / max(len(vsl_vals), 1), 1
                ),
                avg_vap=round(
                    sum(vap_vals) / max(len(vap_vals), 1), 1
                ),
                avg_lin=round(
                    sum(lin_vals) / max(len(lin_vals), 1), 3
                ),
                normal_morphology_pct=round(
                    100 * normal / max(len(morphologies), 1), 1
                ),
                concentration=concentration,
                tracks=tracks,
                morphologies=morphologies,
                detections_per_frame=all_detections,
                analysis_duration_s=round(time.time() - t0, 2),
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )

            self.progress_updated.emit(100)
            self.stage_changed.emit("done")
            self.analysis_complete.emit(result)
            logger.info(
                "Video analysis complete in %.1fs — %d cells detected",
                result.analysis_duration_s, total,
            )

        except Exception as exc:
            logger.exception("VideoPipeline error")
            self.error_occurred.emit(str(exc))

    # ── SORT Tracker (inline from oldproject/tracker.py) ─────────────────
    @staticmethod
    def _create_tracker():
        """Create a SORT tracker using the UKF-based implementation."""
        try:
            # Try importing from the oldproject tracker
            import sys
            sys.path.insert(0, os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "oldproject"
            ))
            from tracker import Sort
            return Sort(max_age=5, min_hits=3, iou_threshold=0.3)
        except ImportError:
            logger.warning(
                "Could not import SORT tracker from oldproject — "
                "using fallback simple tracker"
            )
            return _FallbackTracker()


class _FallbackTracker:
    """Minimal fallback if oldproject tracker is not importable."""

    def __init__(self):
        self._next_id = 1
        self._tracks: dict[int, np.ndarray] = {}

    def update(self, dets: np.ndarray) -> np.ndarray:
        """Simple nearest-neighbor association."""
        if dets.shape[0] == 0:
            return np.empty((0, 5))

        result = []
        for det in dets:
            x1, y1, x2, y2 = det[:4]
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

            best_id = None
            best_dist = 50.0  # Max association distance

            for tid, prev in self._tracks.items():
                dist = math.hypot(cx - prev[0], cy - prev[1])
                if dist < best_dist:
                    best_dist = dist
                    best_id = tid

            if best_id is None:
                best_id = self._next_id
                self._next_id += 1

            self._tracks[best_id] = np.array([cx, cy])
            result.append([x1, y1, x2, y2, best_id])

        return np.array(result)
