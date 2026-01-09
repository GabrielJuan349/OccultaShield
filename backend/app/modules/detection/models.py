from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
import numpy as np

@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    frame: int
    mask: Optional[List[float]] = None # Polygon points [x1, y1, x2, y2, ...] flattened

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> Tuple[float, float]:
        return (self.x1 + self.width / 2, self.y1 + self.height / 2)

    def to_dict(self) -> dict:
        return asdict(self)
        
    def to_int_tuple(self) -> Tuple[int, int, int, int]:
        return int(self.x1), int(self.y1), int(self.x2), int(self.y2)

@dataclass
class Capture:
    frame: int
    image_path: str
    bbox: BoundingBox
    reason: str
    timestamp: float

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class TrackedDetection:
    track_id: int
    detection_type: str
    bbox_history: List[BoundingBox] = field(default_factory=list)
    captures: List[Capture] = field(default_factory=list)
    is_confirmed: bool = False
    
    @property
    def first_frame(self) -> int:
        return self.bbox_history[0].frame if self.bbox_history else 0
        
    @property
    def last_frame(self) -> int:
        return self.bbox_history[-1].frame if self.bbox_history else 0
        
    @property
    def last_bbox(self) -> Optional[BoundingBox]:
        return self.bbox_history[-1] if self.bbox_history else None

    @property
    def avg_confidence(self) -> float:
        if not self.bbox_history: return 0.0
        return sum(b.confidence for b in self.bbox_history) / len(self.bbox_history)
        
    @property
    def max_confidence(self) -> float:
        if not self.bbox_history: return 0.0
        return max(b.confidence for b in self.bbox_history)
        
    @property
    def best_capture(self) -> Optional[Capture]:
        """Retorna la captura con mayor confianza"""
        if not self.captures:
            return None
        return max(self.captures, key=lambda c: c.bbox.confidence)
    
    def add_bbox(self, bbox: BoundingBox):
        self.bbox_history.append(bbox)
        
    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "detection_type": self.detection_type,
            "bbox_history": [b.to_dict() for b in self.bbox_history],
            "captures": [c.to_dict() for c in self.captures],
            "is_confirmed": self.is_confirmed,
            "avg_confidence": self.avg_confidence,
            "total_frames": len(self.bbox_history)
        }

@dataclass
class DetectionResult:
    video_path: str
    total_frames: int
    fps: float
    duration_seconds: float
    width: int
    height: int
    detections: List[TrackedDetection] = field(default_factory=list)
    frames_processed: int = 0
    processing_time_seconds: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "video_path": self.video_path,
            "total_frames": self.total_frames,
            "fps": self.fps,
            "detections_count": len(self.detections),
            "processing_time": self.processing_time_seconds
        }
