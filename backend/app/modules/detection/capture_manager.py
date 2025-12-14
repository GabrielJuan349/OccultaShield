from pathlib import Path
import cv2
import numpy as np
from datetime import datetime
from .models import Capture, BoundingBox

class CaptureManager:
    def __init__(self, stability_threshold=0.5, stability_frames=3, image_quality=95, crop_margin=20):
        self.stability_threshold = stability_threshold
        self.stability_frames = stability_frames
        self.image_quality = image_quality
        self.crop_margin = crop_margin
        
        # State per track
        self.track_data = {} # {id: {stable_count: 0, last_capture_time: 0, best_capture: None}}

    def consider_frame(self, track_id: int, frame_img: np.ndarray, frame_num: int, bbox: BoundingBox, output_dir: Path, fps: float, capture_interval: float) -> str:
        """
        Evaluate if a capture should be saved. Returns path if saved, None otherwise.
        """
        if track_id not in self.track_data:
            self.track_data[track_id] = {"stable_count": 0, "last_capture_time": -999}
            
        data = self.track_data[track_id]
        
        # Stability check
        if bbox.confidence >= self.stability_threshold:
            data["stable_count"] += 1
        else:
            data["stable_count"] = 0
            
        if data["stable_count"] < self.stability_frames:
            return None
            
        # Timing check
        timestamp = frame_num / fps
        if timestamp - data["last_capture_time"] < capture_interval:
            return None
            
        # Save capture
        return self._save_capture(track_id, frame_img, frame_num, bbox, output_dir, timestamp)

    def _save_capture(self, track_id: int, frame_img: np.ndarray, frame_num: int, bbox: BoundingBox, output_dir: Path, timestamp: float) -> str:
        track_dir = output_dir / f"track_{track_id}"
        track_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"capture_{frame_num}.jpg"
        filepath = track_dir / filename
        
        # Crop
        h, w = frame_img.shape[:2]
        x1 = max(0, int(bbox.x1) - self.crop_margin)
        y1 = max(0, int(bbox.y1) - self.crop_margin)
        x2 = min(w, int(bbox.x2) + self.crop_margin)
        y2 = min(h, int(bbox.y2) + self.crop_margin)
        
        crop = frame_img[y1:y2, x1:x2]
        
        if crop.size > 0:
            cv2.imwrite(str(filepath), crop, [int(cv2.IMWRITE_JPEG_QUALITY), self.image_quality])
            
        self.track_data[track_id]["last_capture_time"] = timestamp
        return str(filepath)
