from typing import List, Tuple, Dict, Optional
import numpy as np
from .models import BoundingBox

class ObjectTracker:
    """
    Simplified SORT tracker to associate detections across frames.
    """
    def __init__(self, iou_threshold: float = 0.3, max_age: int = 30, min_hits: int = 3):
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.min_hits = min_hits
        self.tracks: Dict[int, 'Track'] = {}
        self.next_id = 1
        
    def update(self, detections: List[Tuple[str, BoundingBox]], frame_num: int) -> List[Tuple[int, str, BoundingBox]]:
        """
        Update tracks with new detections.
        Returns: List of confirmed (track_id, type, bbox)
        """
        # 1. Predict (increment age for existing)
        for t in self.tracks.values():
            t.age += 1
            
        # 2. Match
        # Group by type
        dets_by_type = {}
        for cls, bbox in detections:
            dets_by_type.setdefault(cls, []).append(bbox)
            
        confirmed_out = []
        
        # Simple greedy matching per class
        for cls, bboxes in dets_by_type.items():
            active_tracks = [t for t in self.tracks.values() if t.detection_type == cls]
            
            # IoU Matrix
            matches = []
            unmatched_dets = list(range(len(bboxes)))
            unmatched_tracks = list(t.track_id for t in active_tracks)
            
            if active_tracks and bboxes:
                # Greedy match
                # Compute all IoUs
                possible_matches = []
                for i, trk in enumerate(active_tracks):
                    for j, det in enumerate(bboxes):
                        iou = self._calculate_iou(trk.last_bbox, det)
                        if iou >= self.iou_threshold:
                            possible_matches.append((iou, trk.track_id, j))
                            
                # Sort by IoU (desc)
                possible_matches.sort(key=lambda x: x[0], reverse=True)
                
                matched_tracks = set()
                matched_dets = set()
                
                for iou, tid, did in possible_matches:
                    if tid not in matched_tracks and did not in matched_dets:
                        matched_tracks.add(tid)
                        matched_dets.add(did)
                        # Update track
                        self.tracks[tid].update(bboxes[did], frame_num)
                        # Remove from unmatched
                        if tid in unmatched_tracks: unmatched_tracks.remove(tid)
                        if did in unmatched_dets: unmatched_dets.remove(did)

            # Create new tracks for unmatched detections
            for did in unmatched_dets:
                self._create_track(cls, bboxes[did], frame_num)
                
        # 3. Cleanup and Output
        dead_tracks = []
        for tid, t in self.tracks.items():
            if t.age > self.max_age:
                dead_tracks.append(tid)
            elif t.hits >= self.min_hits:
                 # Check if recently updated (age=0 means updated this frame)
                 # Or just return current position?
                 # Return if it was updated this frame OR coasting? 
                 # Usually return if confirmed.
                 # If age > 0, it's a prediction (coasting). We return it if needed.
                 # For simplicity, returning current status.
                 confirmed_out.append((tid, t.detection_type, t.last_bbox))

        for tid in dead_tracks:
            del self.tracks[tid]
            
        return confirmed_out

    def _create_track(self, cls: str, bbox: BoundingBox, frame_num: int):
        self.tracks[self.next_id] = Track(self.next_id, cls, bbox, frame_num)
        self.next_id += 1

    def _calculate_iou(self, bb1: BoundingBox, bb2: BoundingBox) -> float:
        # Determine intersection
        x_left = max(bb1.x1, bb2.x1)
        y_top = max(bb1.y1, bb2.y1)
        x_right = min(bb1.x2, bb2.x2)
        y_bottom = min(bb1.y2, bb2.y2)

        if x_right < x_left or y_bottom < y_top:
            return 0.0

        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        params_area = bb1.area + bb2.area - intersection_area
        
        if params_area <= 0: return 0.0
        return intersection_area / params_area

class Track:
    def __init__(self, track_id, detection_type, bbox, frame):
        self.track_id = track_id
        self.detection_type = detection_type
        self.last_bbox = bbox
        self.first_frame = frame
        self.last_frame = frame
        self.hits = 1
        self.age = 0 # frames since last hit
        
    def update(self, bbox, frame):
        self.last_bbox = bbox
        self.last_frame = frame
        self.hits += 1
        self.age = 0
