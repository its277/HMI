"""
tracker.py — UKF-based SORT (Simple Online and Realtime Tracking).

Uses an Unscented Kalman Filter (UKF) with a non-linear motion model
(sinusoidal sperm-like movement) for per-object state estimation,
combined with IoU-based Hungarian assignment for multi-object tracking.

Adapted from the original research pipeline for integration into the
HMI's AI analysis pipeline.
"""

from __future__ import annotations

import numpy as np
from filterpy.kalman import MerweScaledSigmaPoints, UnscentedKalmanFilter
from scipy.optimize import linear_sum_assignment

EPS = 1e-8


def iou(bb_test: np.ndarray, bb_gt: np.ndarray) -> float:
    """Compute IoU between two bboxes in [x1, y1, x2, y2] format."""
    xx1 = np.maximum(bb_test[0], bb_gt[0])
    yy1 = np.maximum(bb_test[1], bb_gt[1])
    xx2 = np.minimum(bb_test[2], bb_gt[2])
    yy2 = np.minimum(bb_test[3], bb_gt[3])
    w = np.maximum(0.0, xx2 - xx1)
    h = np.maximum(0.0, yy2 - yy1)
    inter = w * h
    union = (
        (bb_test[2] - bb_test[0]) * (bb_test[3] - bb_test[1])
        + (bb_gt[2] - bb_gt[0]) * (bb_gt[3] - bb_gt[1])
        - inter
        + EPS
    )
    return inter / union


class KalmanBoxTracker:
    """
    Tracks one object (bounding box) with an Unscented Kalman Filter.

    State vector: [x_center, y_center, scale, aspect_ratio, vx, vy, vs]
    Measurement:  [x_center, y_center, scale, aspect_ratio]

    The motion model includes a sinusoidal perturbation on x-velocity
    based on y-position, which better models the characteristic
    flagellar-driven movement pattern of spermatozoa.
    """

    count = 0

    def __init__(self, bbox: np.ndarray) -> None:
        self.dim_x = 7
        self.dim_z = 4

        # Non-linear motion model with sperm-like sinusoidal wobble
        def motion_model(x: np.ndarray, dt: float = 1.0) -> np.ndarray:
            F = np.eye(self.dim_x)
            F[0, 4] = dt
            F[1, 5] = dt
            F[2, 6] = dt
            x[4] += 0.1 * np.sin(x[1])
            return F @ x

        # Measurement function (linear — maps state to [x, y, s, r])
        def meas_model(x: np.ndarray) -> np.ndarray:
            return x[:4]

        # Sigma points for the UKF
        sigmas = MerweScaledSigmaPoints(
            n=self.dim_x, alpha=0.1, beta=2.0, kappa=0.0
        )

        # Initialize UKF
        self.ukf = UnscentedKalmanFilter(
            dim_x=self.dim_x,
            dim_z=self.dim_z,
            dt=1.0,
            fx=motion_model,
            hx=meas_model,
            points=sigmas,
        )

        # Initialize state [x, y, s, r, vx, vy, vs]
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x_c = bbox[0] + w / 2.0
        y_c = bbox[1] + h / 2.0
        s = w * h
        r = w / float(h)
        self.ukf.x = np.array([x_c, y_c, s, r, 0.0, 0.0, 0.0])

        # Set covariances
        self.ukf.P *= 10.0
        self.ukf.R *= 10.0
        self.ukf.Q *= 0.01

        # Tracking bookkeeping
        self.time_since_update = 0
        self.id = KalmanBoxTracker.count
        KalmanBoxTracker.count += 1
        self.history: list[np.ndarray] = []
        self.hits = 0
        self.hit_streak = 0
        self.age = 0

    def update(self, bbox: np.ndarray) -> None:
        """Update filter with observed bbox [x1, y1, x2, y2]."""
        self.time_since_update = 0
        self.history.clear()
        self.hits += 1
        self.hit_streak += 1
        z = self.convert_bbox_to_z(bbox)
        self.ukf.update(z)

    def predict(self) -> np.ndarray:
        """Advance the filter and return the predicted bbox."""
        self.ukf.predict()
        self.age += 1
        if self.time_since_update > 0:
            self.hit_streak = 0
        self.time_since_update += 1
        bbox = self.convert_x_to_bbox(self.ukf.x)
        self.history.append(bbox)
        return bbox

    def convert_bbox_to_z(self, bbox: np.ndarray) -> np.ndarray:
        """Convert [x1, y1, x2, y2] → [x_c, y_c, scale, ratio]."""
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x_c = bbox[0] + w / 2.0
        y_c = bbox[1] + h / 2.0
        s = w * h
        r = w / float(h)
        return np.array([x_c, y_c, s, r])

    def convert_x_to_bbox(
        self, x: np.ndarray, score: float | None = None
    ) -> np.ndarray:
        """Convert state x → [x1, y1, x2, y2] (+ optional score)."""
        s = max(x[2], 1e-5)
        r = max(x[3], 1e-5)
        w = np.sqrt(s * r)
        h = s / w
        x1 = x[0] - w / 2.0
        y1 = x[1] - h / 2.0
        x2 = x[0] + w / 2.0
        y2 = x[1] + h / 2.0
        if score is None:
            return np.array([x1, y1, x2, y2])
        return np.array([x1, y1, x2, y2, score])

    def get_state(self) -> np.ndarray:
        """Get current bbox estimate."""
        return self.convert_x_to_bbox(self.ukf.x)


class Sort:
    """
    Simple Online and Realtime Tracking with UKF per object.

    Each tracked object maintains its own UKF instance for state
    estimation. Detection-to-track association uses IoU + Hungarian
    algorithm each frame.

    Parameters
    ----------
    max_age : int
        Max frames a track survives without being matched.
    min_hits : int
        Min consecutive hits before a track is output.
    iou_threshold : float
        Minimum IoU for a valid detection-track association.
    """

    def __init__(
        self,
        max_age: int = 5,
        min_hits: int = 3,
        iou_threshold: float = 0.3,
    ) -> None:
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.trackers: list[KalmanBoxTracker] = []
        self.frame_count = 0

    def update(self, dets: np.ndarray = np.empty((0, 5))) -> np.ndarray:
        """
        Process detections for one frame.

        Parameters
        ----------
        dets : np.ndarray
            Detections as Nx5 array [x1, y1, x2, y2, confidence].

        Returns
        -------
        np.ndarray
            Mx5 array of active tracks [x1, y1, x2, y2, track_id].
        """
        self.frame_count += 1

        # 1) Predict all existing trackers
        trks: list[np.ndarray] = []
        to_del: list[int] = []
        for t, trk in enumerate(self.trackers):
            pred = trk.predict()
            if np.any(np.isnan(pred)):
                to_del.append(t)
            else:
                trks.append(pred)
        for idx in reversed(to_del):
            self.trackers.pop(idx)
        trks_arr = np.array(trks) if trks else np.empty((0, 4))

        # 2) Associate detections to tracked boxes via IoU + Hungarian
        if dets.shape[0] and trks_arr.shape[0]:
            iou_mat = np.zeros(
                (dets.shape[0], trks_arr.shape[0]), dtype=np.float32
            )
            for d in range(dets.shape[0]):
                for t in range(trks_arr.shape[0]):
                    iou_mat[d, t] = iou(dets[d], trks_arr[t])
            matched_idx = linear_sum_assignment(-iou_mat)
            matches = np.stack(matched_idx, axis=1)
        else:
            matches = np.empty((0, 2), dtype=int)

        unmatched_dets = [
            d
            for d in range(dets.shape[0])
            if d not in matches[:, 0]
        ]

        # 3) Create new trackers for unmatched detections
        for d in unmatched_dets:
            self.trackers.append(KalmanBoxTracker(dets[d, :4]))

        # 4) Update matched trackers
        for m in matches:
            d, t = m
            if iou_mat[d, t] >= self.iou_threshold:
                self.trackers[t].update(dets[d, :4])

        # 5) Build output of active tracks
        ret: list[np.ndarray] = []
        for trk in self.trackers:
            if trk.time_since_update < 1 and (
                trk.hits >= self.min_hits
                or self.frame_count <= self.min_hits
            ):
                bbox = trk.get_state()
                ret.append(np.append(bbox, trk.id + 1))

        # 6) Remove dead trackers
        self.trackers = [
            t for t in self.trackers if t.time_since_update <= self.max_age
        ]

        if ret:
            return np.stack(ret, axis=0)
        return np.empty((0, 5))
