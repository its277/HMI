# import numpy as np
# from scipy.optimize import linear_sum_assignment
# from filterpy.kalman import KalmanFilter

# # A small constant to prevent division by zero
# EPS = 1e-8

# def iou(bb_test, bb_gt):
#     """
#     Computes IoU between two bboxes in the form [x1,y1,x2,y2]
#     """
#     xx1 = np.maximum(bb_test[0], bb_gt[0])
#     yy1 = np.maximum(bb_test[1], bb_gt[1])
#     xx2 = np.minimum(bb_test[2], bb_gt[2])
#     yy2 = np.minimum(bb_test[3], bb_gt[3])
#     w = np.maximum(0., xx2 - xx1)
#     h = np.maximum(0., yy2 - yy1)
#     wh = w * h
#     o = wh / ((bb_test[2] - bb_test[0]) * (bb_test[3] - bb_test[1])
#               + (bb_gt[3] - bb_gt[0]) * (bb_gt[2] - bb_gt[1]) - wh + EPS)
#     return o

# class KalmanBoxTracker:
#     """
#     This class represents the internal state of individual tracked objects observed as bbox.
#     """
#     count = 0
#     def __init__(self, bbox):
#         # Define constant velocity model
#         self.kf = KalmanFilter(dim_x=7, dim_z=4) 
#         self.kf.F = np.array([[1,0,0,0,1,0,0],[0,1,0,0,0,1,0],[0,0,1,0,0,0,1],[0,0,0,1,0,0,0],  [0,0,0,0,1,0,0],[0,0,0,0,0,1,0],[0,0,0,0,0,0,1]])
#         self.kf.H = np.array([[1,0,0,0,0,0,0],[0,1,0,0,0,0,0],[0,0,1,0,0,0,0],[0,0,0,1,0,0,0]])

#         self.kf.R[2:,2:] *= 10.
#         self.kf.P[4:,4:] *= 1000. # Give high uncertainty to the unobservable initial velocities
#         self.kf.P *= 10.
#         self.kf.Q[-1,-1] *= 0.01
#         self.kf.Q[4:,4:] *= 0.01

#         self.kf.x[:4] = self.convert_bbox_to_z(bbox)
#         self.time_since_update = 0
#         self.id = KalmanBoxTracker.count
#         KalmanBoxTracker.count += 1
#         self.history = []
#         self.hits = 0
#         self.hit_streak = 0
#         self.age = 0

#     def convert_bbox_to_z(self, bbox):
#         """
#         Takes a bounding box in the form [x1,y1,x2,y2] and returns z in the form
#         [x,y,s,r] where x,y is the centre of the box and s is the scale/area and r is
#         the aspect ratio
#         """
#         w = bbox[2] - bbox[0]
#         h = bbox[3] - bbox[1]
#         x = bbox[0] + w/2.
#         y = bbox[1] + h/2.
#         s = w * h    # scale is just area
#         r = w / float(h)
#         return np.array([x, y, s, r]).reshape((4, 1))

#     def convert_x_to_bbox(self, x, score=None):
#         """
#         Takes a bounding box in the centre form [x,y,s,r] and returns it in the form
#         [x1,y1,x2,y2] where x1,y1 is the top-left and x2,y2 is the bottom-right
#         """
#         w = np.sqrt(x[2] * x[3])
#         h = x[2] / w
#         if(score==None):
#             return np.array([x[0]-w/2.,x[1]-h/2.,x[0]+w/2.,x[1]+h/2.]).reshape((1,4))
#         else:
#             return np.array([x[0]-w/2.,x[1]-h/2.,x[0]+w/2.,x[1]+h/2.,score]).reshape((1,5))

#     def update(self, bbox):
#         """
#         Updates the state vector with observed bbox.
#         """
#         self.time_since_update = 0
#         self.history = []
#         self.hits += 1
#         self.hit_streak += 1
#         self.kf.update(self.convert_bbox_to_z(bbox))

#     def predict(self):
#         """
#         Advances the state vector and returns the predicted bounding box estimate.
#         """
#         if((self.kf.x[6]+self.kf.x[2])<=0):
#             self.kf.x[6] *= 0.0
#         self.kf.predict()
#         self.age += 1
#         if(self.time_since_update > 0):
#             self.hit_streak = 0
#         self.time_since_update += 1
#         self.history.append(self.convert_x_to_bbox(self.kf.x))
#         return self.history[-1]

#     def get_state(self):
#         """
#         Returns the current bounding box estimate.
#         """
#         return self.convert_x_to_bbox(self.kf.x)

# # from filterpy.kalman import UnscentedKalmanFilter
# # from filterpy.kalman import MerweScaledSigmaPoints

# # class KalmanBoxTracker:
# #     """
# #     This class represents the internal state of individual tracked objects observed as bbox,
# #     using UKF for non-linear motion.
# #     """
# #     count = 0
# #     def __init__(self, bbox):
# #         # Define state: [x, y, s, r, vx, vy, vs] (position, scale, aspect ratio, velocities)
# #         self.dim_x = 7
# #         self.dim_z = 4
        
# #         # Non-linear motion model (simple constant velocity with non-linear adjustment)
# #         def motion_model(x, dt=1.0):
# #             F = np.eye(self.dim_x)
# #             F[0, 4] = dt  # x velocity
# #             F[1, 5] = dt  # y velocity
# #             F[2, 6] = dt  # scale velocity
# #             # Add non-linear term (e.g., sinusoidal for sperm-like motion)
# #             x[4] += 0.1 * np.sin(x[1])  # Adjust x velocity based on y position
# #             return F @ x

# #         # Measurement function (linear, maps state to [x, y, s, r])
# #         def measurement_function(x):
# #             return x[:4]

# #         # Initialize sigma points
# #         self.points = MerweScaledSigmaPoints(n=self.dim_x, alpha=0.1, beta=2.0, kappa=0.0)
        
# #         # Initialize UKF
# #         self.ukf = UnscentedKalmanFilter(dim_x=self.dim_x, dim_z=self.dim_z, dt=1.0, fx=motion_model, hx=measurement_function, points=self.points)
        
# #         # Initial state: [x, y, s, r, vx, vy, vs]
# #         w = bbox[2] - bbox[0]
# #         h = bbox[3] - bbox[1]
# #         x = bbox[0] + w/2.
# #         y = bbox[1] + h/2.
# #         s = w * h
# #         r = w / float(h)
# #         self.ukf.x = np.array([x, y, s, r, 0.0, 0.0, 0.0])  # Initial state with zero velocities
        
# #         # Covariance matrices
# #         self.ukf.P *= 10.0  # Initial uncertainty
# #         self.ukf.R *= 10.0  # Measurement noise
# #         self.ukf.Q *= 0.01  # Process noise
        
# #         self.time_since_update = 0
# #         self.id = KalmanBoxTracker.count
# #         KalmanBoxTracker.count += 1
# #         self.history = []
# #         self.hits = 0
# #         self.hit_streak = 0
# #         self.age = 0

# #     def update(self, bbox):
# #         self.time_since_update = 0
# #         self.history = []
# #         self.hits += 1
# #         self.hit_streak += 1
# #         z = self.convert_bbox_to_z(bbox)
# #         self.ukf.update(z)

# #     def predict(self):
# #         self.ukf.predict()
# #         self.age += 1
# #         if self.time_since_update > 0:
# #             self.hit_streak = 0
# #         self.time_since_update += 1
# #         self.history.append(self.convert_x_to_bbox(self.ukf.x))
# #         return self.history[-1]

# #     def convert_bbox_to_z(self, bbox):
# #         w = bbox[2] - bbox[0]
# #         h = bbox[3] - bbox[1]
# #         x = bbox[0] + w/2.
# #         y = bbox[1] + h/2.
# #         s = w * h
# #         r = w / float(h)
# #         return np.array([x, y, s, r]).reshape((4, 1))

# #     def convert_x_to_bbox(self, x, score=None):
# #         w = np.sqrt(x[2] * x[3])
# #         h = x[2] / w
# #         if score is None:
# #             return np.array([x[0]-w/2., x[1]-h/2., x[0]+w/2., x[1]+h/2.]).reshape((1,4))
# #         else:
# #             return np.array([x[0]-w/2., x[1]-h/2., x[0]+w/2., x[1]+h/2., score]).reshape((1,5))

# #     def get_state(self):
# #         return self.convert_x_to_bbox(self.ukf.x)

# class Sort:
#     def __init__(self, max_age=1, min_hits=3, iou_threshold=0.3):
#         self.max_age = max_age
#         self.min_hits = min_hits
#         self.iou_threshold = iou_threshold
#         self.trackers = []
#         self.frame_count = 0

#     def update(self, dets=np.empty((0, 5))):
#         self.frame_count += 1
#         trks = np.zeros((len(self.trackers), 5))
#         to_del = []
#         ret = []
#         for t, trk in enumerate(trks):
#             pos = self.trackers[t].predict()[0]
#             trk[:] = [pos[0], pos[1], pos[2], pos[3], 0]
#             if np.any(np.isnan(pos)):
#                 to_del.append(t)
#         trks = np.ma.compress_rows(np.ma.masked_invalid(trks))
#         for t in reversed(to_del):
#             self.trackers.pop(t)

#         if dets.any():
#             iou_matrix = np.zeros((len(dets), len(trks)), dtype=np.float32)
#             for d, det in enumerate(dets):
#                 for t, trk in enumerate(trks):
#                     iou_matrix[d, t] = iou(det, trk)
            
#             # Using linear_sum_assignment for Hungarian algorithm
#             matched_indices = linear_sum_assignment(-iou_matrix)
#             matched_indices = np.asarray(matched_indices)
#             matched_indices = np.transpose(matched_indices)
#         else:
#             matched_indices = np.empty(shape=(0,2))

#         unmatched_detections = []
#         for d, det in enumerate(dets):
#             if(d not in matched_indices[:,0]):
#                 unmatched_detections.append(d)
        
#         unmatched_trackers = []
#         for t, trk in enumerate(trks):
#             if(t not in matched_indices[:,1]):
#                 unmatched_trackers.append(t)

#         # Create and initialise new trackers for unmatched detections
#         for i in unmatched_detections:
#             trk = KalmanBoxTracker(dets[i,:])
#             self.trackers.append(trk)
        
#         # Update matched trackers with assigned detections
#         for m in matched_indices:
#             if(iou_matrix[m[0], m[1]] >= self.iou_threshold):
#                 self.trackers[m[1]].update(dets[m[0], :])

#         # Return active trackers
#         ret = []
#         for trk in reversed(self.trackers):
#             if (trk.time_since_update < 1) and (trk.hit_streak >= self.min_hits or self.frame_count <= self.min_hits):
#                 ret.append(np.concatenate((trk.get_state()[0], [trk.id+1])).reshape(1,-1))
        
#         # Remove dead tracklets
#         if(len(ret)>0):
#             i = len(self.trackers)
#             for trk in reversed(self.trackers):
#                 if(trk.time_since_update > self.max_age):
#                     self.trackers.pop(i-1)
#                 i -= 1
        
#         if(len(ret)>0):
#             return np.concatenate(ret)
#         return np.empty((0,5))


from filterpy.kalman import UnscentedKalmanFilter
from filterpy.kalman import MerweScaledSigmaPoints
import numpy as np
from scipy.optimize import linear_sum_assignment

EPS = 1e-8

def iou(bb_test, bb_gt):
    """ Computes IoU between two bboxes [x1,y1,x2,y2]. """
    xx1 = np.maximum(bb_test[0], bb_gt[0])
    yy1 = np.maximum(bb_test[1], bb_gt[1])
    xx2 = np.minimum(bb_test[2], bb_gt[2])
    yy2 = np.minimum(bb_test[3], bb_gt[3])
    w = np.maximum(0., xx2 - xx1)
    h = np.maximum(0., yy2 - yy1)
    inter = w * h
    union = ((bb_test[2] - bb_test[0]) * (bb_test[3] - bb_test[1])
             + (bb_gt[2] - bb_gt[0]) * (bb_gt[3] - bb_gt[1]) - inter + EPS)
    return inter / union

class KalmanBoxTracker:
    """Tracks one object (bbox) with an Unscented Kalman Filter."""
    count = 0

    def __init__(self, bbox):
        self.dim_x = 7
        self.dim_z = 4

        # Define motion & measurement functions
        def motion_model(x, dt=1.):
            F = np.eye(self.dim_x)
            F[0,4] = dt
            F[1,5] = dt
            F[2,6] = dt
            x[4] += 0.1 * np.sin(x[1])
            return F @ x

        def meas_model(x):
            return x[:4]

        # Sigma points for the UKF
        sigmas = MerweScaledSigmaPoints(n=self.dim_x, alpha=0.1, beta=2., kappa=0.)

        # Initialize UKF
        self.ukf = UnscentedKalmanFilter(
            dim_x=self.dim_x, dim_z=self.dim_z,
            dt=1., fx=motion_model, hx=meas_model,
            points=sigmas
        )

        # Initialize state [x, y, s, r, vx, vy, vs] as 1-D array
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x_c = bbox[0] + w/2.
        y_c = bbox[1] + h/2.
        s = w * h
        r = w / float(h)
        self.ukf.x = np.array([x_c, y_c, s, r, 0., 0., 0.])

        # Set covariances
        self.ukf.P *= 10.
        self.ukf.R *= 10.
        self.ukf.Q *= 0.01

        # Tracking bookkeeping
        self.time_since_update = 0
        self.id = KalmanBoxTracker.count
        KalmanBoxTracker.count += 1
        self.history = []
        self.hits = 0
        self.hit_streak = 0
        self.age = 0

    def update(self, bbox):
        """Update filter with observed bbox [x1,y1,x2,y2]."""
        self.time_since_update = 0
        self.history.clear()
        self.hits += 1
        self.hit_streak += 1

        z = self.convert_bbox_to_z(bbox)  # 1-D measurement (4,)
        self.ukf.update(z)

    def predict(self):
        """Advance the filter and return the predicted bbox."""
        self.ukf.predict()
        self.age += 1
        if self.time_since_update > 0:
            self.hit_streak = 0
        self.time_since_update += 1

        bbox = self.convert_x_to_bbox(self.ukf.x)
        self.history.append(bbox)
        return bbox

    def convert_bbox_to_z(self, bbox):
        """Convert [x1,y1,x2,y2] → [x_c,y_c,scale,ratio]."""
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x_c = bbox[0] + w/2.
        y_c = bbox[1] + h/2.
        s = w * h
        r = w / float(h)
        return np.array([x_c, y_c, s, r])

    def convert_x_to_bbox(self, x, score=None):
        """Convert state x → [x1,y1,x2,y2] (+ score)."""
        s = max(x[2], 1e-5)  # scale
        r = max(x[3], 1e-5)  # aspect ratio

        w = np.sqrt(s * r)
        h = s / w

        x1 = x[0] - w / 2.
        y1 = x[1] - h / 2.
        x2 = x[0] + w / 2.
        y2 = x[1] + h / 2.

        if score is None:
            return np.array([x1, y1, x2, y2])
        return np.array([x1, y1, x2, y2, score])

    def get_state(self):
        """Get current bbox estimate."""
        return self.convert_x_to_bbox(self.ukf.x)

class Sort:
    """Simple Online and Realtime Tracking with UKF per object."""
    def __init__(self, max_age=5, min_hits=3, iou_threshold=0.3):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.trackers = []
        self.frame_count = 0

    def update(self, dets=np.empty((0,5))):
        self.frame_count += 1

        # 1) Predict all trackers
        trks = []
        to_del = []
        for t, trk in enumerate(self.trackers):
            pred = trk.predict()
            if np.any(np.isnan(pred)):
                to_del.append(t)
            else:
                trks.append(pred)
        for idx in reversed(to_del):
            self.trackers.pop(idx)
        trks = np.array(trks)

        # 2) Associate detections to tracked boxes
        if dets.shape[0] and trks.shape[0]:
            iou_mat = np.zeros((dets.shape[0], trks.shape[0]), dtype=np.float32)
            for d in range(dets.shape[0]):
                for t in range(trks.shape[0]):
                    iou_mat[d, t] = iou(dets[d], trks[t])
            matched_idx = linear_sum_assignment(-iou_mat)
            matches = np.stack(matched_idx, axis=1)
        else:
            matches = np.empty((0,2), dtype=int)

        unmatched_dets = [d for d in range(dets.shape[0]) if d not in matches[:,0]]
        unmatched_trks = [t for t in range(trks.shape[0]) if t not in matches[:,1]]

        # 3) Create new trackers for unmatched detections
        for d in unmatched_dets:
            self.trackers.append(KalmanBoxTracker(dets[d,:4]))

        # 4) Update matched trackers
        for m in matches:
            d, t = m
            if iou_mat[d,t] >= self.iou_threshold:
                self.trackers[t].update(dets[d,:4])

        # 5) Build output
        ret = []
        for trk in self.trackers:
            if (trk.time_since_update < 1 and
                (trk.hits >= self.min_hits or self.frame_count <= self.min_hits)):
                bbox = trk.get_state()
                ret.append(np.append(bbox, trk.id+1))
        # 6) Remove old trackers
        self.trackers = [t for t in self.trackers if t.time_since_update <= self.max_age]

        if ret:
            return np.stack(ret, axis=0)
        return np.empty((0,5))
