from typing import List, Tuple, Dict, Optional
import numpy as np
import cv2
from scipy.optimize import linear_sum_assignment
from .models import BoundingBox

class Track:
    def __init__(self, track_id, detection_type, bbox, frame):
        self.track_id = track_id
        self.detection_type = detection_type
        self.last_bbox = bbox
        self.first_frame = frame
        self.last_frame = frame
        self.hits = 1
        self.age = 0
        
        # Initialize Kalman Filter
        # State: [x1, y1, x2, y2, vx1, vy1, vx2, vy2]
        self.kf = cv2.KalmanFilter(8, 4)
        self.kf.measurementMatrix = np.array([
            [1,0,0,0,0,0,0,0],
            [0,1,0,0,0,0,0,0],
            [0,0,1,0,0,0,0,0],
            [0,0,0,1,0,0,0,0]
        ], np.float32)
        
        self.kf.transitionMatrix = np.array([
            [1,0,0,0,1,0,0,0],
            [0,1,0,0,0,1,0,0],
            [0,0,1,0,0,0,1,0],
            [0,0,0,1,0,0,0,1],
            [0,0,0,0,1,0,0,0],
            [0,0,0,0,0,1,0,0],
            [0,0,0,0,0,0,1,0],
            [0,0,0,0,0,0,0,1]
        ], np.float32)
        
        self.kf.processNoiseCov = np.eye(8, dtype=np.float32) * 0.03
        self.kf.measurementNoiseCov = np.eye(4, dtype=np.float32) * 0.1
        
        # Initial state
        self.kf.statePost = np.array([bbox.x1, bbox.y1, bbox.x2, bbox.y2, 0, 0, 0, 0], np.float32)
        
    def predict(self):
        """Predict next state (prior to measurement)"""
        if self.age > 0:
             # Reduce velocity influence if age is high (uncertainty)
             self.kf.statePost[4:] *= 0.95
             
        prediction = self.kf.predict()
        x1, y1, x2, y2 = prediction[:4].flatten()
        
        # Ensure logical box
        if x2 < x1: x2 = x1 + 1
        if y2 < y1: y2 = y1 + 1
        
        return BoundingBox(x1, y1, x2, y2, self.last_bbox.confidence, self.last_frame + 1)

    def update(self, bbox, frame):
        self.last_bbox = bbox
        self.last_frame = frame
        self.hits += 1
        self.age = 0
        
        # Measurement update
        measurement = np.array([bbox.x1, bbox.y1, bbox.x2, bbox.y2], np.float32)
        self.kf.correct(measurement)

class ObjectTracker:
    """
    Rastreador de objetos mejorado con Hungarian Algorithm para asignación óptima.
    """
    def __init__(self, iou_threshold=0.3, max_age=1000, min_hits=0):
        # max_age=1000: Tracks survive practically forever even if lost
        # min_hits=0: Tracks are confirmed IMMEDIATELY
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.min_hits = min_hits
        self.tracks = {}
        self.next_id = 1
        print(f"   [TRACKER] Initialized: iou_threshold={iou_threshold}, max_age={max_age}, min_hits={min_hits}")
        
    def update(self, detections: List[Tuple[str, BoundingBox]], frame_num: int) -> List[Tuple[int, str, BoundingBox]]:
        # DEBUG: Log incoming detections
        if detections:
            print(f"   [TRACKER] Frame {frame_num}: {len(detections)} detections incoming")
            for cls, bbox in detections:
                print(f"      - {cls}: conf={bbox.confidence:.2f}, area={bbox.area:.0f}")
        
        # Envejecer tracks existentes y guardar predicciones
        predictions = {}  # track_id -> predicted_bbox
        for tid, t in self.tracks.items():
            t.age += 1
            pred = t.predict()
            predictions[tid] = pred
            
        dets_by_type = {}
        for cls, bbox in detections:
            dets_by_type.setdefault(cls, []).append(bbox)
            
        for cls, bboxes in dets_by_type.items():
            active_tracks = [t for t in self.tracks.values() if t.detection_type == cls]
            
            # Si no hay tracks, crear nuevos para todas las detecciones
            if not active_tracks:
                for bbox in bboxes:
                    self._create_track(cls, bbox, frame_num)
                    print(f"   [TRACKER] Created new track for {cls} (no active tracks)")
                continue
                
            if not bboxes:
                continue
            
            # Construir matriz de costos para Hungarian Algorithm
            num_tracks = len(active_tracks)
            num_dets = len(bboxes)
            cost_matrix = np.ones((num_tracks, num_dets), dtype=np.float32)
            
            for i, trk in enumerate(active_tracks):
                for j, det in enumerate(bboxes):
                    # Use stored prediction
                    pred_box = predictions.get(trk.track_id)
                    if pred_box is None:
                        x1, y1, x2, y2 = trk.kf.statePre[:4].flatten()
                        pred_box = BoundingBox(x1, y1, x2, y2, 0.0, frame_num)
                    
                    iou = self._calculate_iou(pred_box, det)
                    if iou >= self.iou_threshold:
                        cost_matrix[i, j] = 1.0 - iou  # Menor costo = mejor match
            
            # Asignación óptima con Hungarian Algorithm
            row_indices, col_indices = linear_sum_assignment(cost_matrix)
            
            matched_tracks = set()
            matched_dets = set()
            
            for row, col in zip(row_indices, col_indices):
                if cost_matrix[row, col] < (1.0 - self.iou_threshold):
                    track = active_tracks[row]
                    matched_tracks.add(track.track_id)
                    matched_dets.add(col)
                    self.tracks[track.track_id].update(bboxes[col], frame_num)
                    
            # Create new tracks for unmatched detections
            for j, det in enumerate(bboxes):
                if j not in matched_dets:
                    self._create_track(cls, det, frame_num)
                    print(f"   [TRACKER] Created new track for unmatched {cls}")
                    
        # Limpieza de tracks y reporte
        dead = []
        confirmed_out = []
        
        for tid, t in self.tracks.items():
            if t.age > self.max_age:
                dead.append(tid)
                print(f"   [TRACKER] Track {tid} died (age > {self.max_age})")
            else:
                # Retornamos TODOS los tracks activos, independientemente de hits
                # El usuario quiere ver todo, aunque sea pequeño.
                confirmed_out.append((tid, t.detection_type, t.last_bbox))
                
        for tid in dead:
            del self.tracks[tid]
        
        if confirmed_out:
            print(f"   [TRACKER] Reporting {len(confirmed_out)} active tracks")
        
        return confirmed_out

    def _create_track(self, cls, bbox, frame):
        self.tracks[self.next_id] = Track(self.next_id, cls, bbox, frame)
        self.next_id += 1

    def _calculate_iou(self, bb1, bb2):
        """Calcula Intersection over Union entre dos bounding boxes"""
        xl = max(bb1.x1, bb2.x1)
        yt = max(bb1.y1, bb2.y1)
        xr = min(bb1.x2, bb2.x2)
        yb = min(bb1.y2, bb2.y2)
        if xr < xl or yb < yt:
            return 0.0
        inter = (xr - xl) * (yb - yt)
        union = bb1.area + bb2.area - inter
        return inter / union if union > 0 else 0.0
