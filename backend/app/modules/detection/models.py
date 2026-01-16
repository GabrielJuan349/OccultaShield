"""Detection Data Models for Video Processing Pipeline.

This module defines the core data structures used throughout the detection
and tracking pipeline for GDPR-sensitive content identification.

Classes:
    BoundingBox: Represents a rectangular region in a video frame.
    Capture: Stores a captured image of a detected object.
    TrackedDetection: Tracks an object across multiple frames.
    DetectionResult: Aggregates all detections from a video.

Example:
    >>> bbox = BoundingBox(x1=100, y1=100, x2=200, y2=200, confidence=0.95, frame=1)
    >>> track = TrackedDetection(track_id=1, detection_type="face")
    >>> track.add_bbox(bbox)
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
import numpy as np


@dataclass
class BoundingBox:
    """Represents a bounding box detection in a video frame.

    Stores coordinates, confidence score, frame number, and optional
    segmentation mask for precise object boundaries.

    Attributes:
        x1: Left edge x-coordinate.
        y1: Top edge y-coordinate.
        x2: Right edge x-coordinate.
        y2: Bottom edge y-coordinate.
        confidence: Detection confidence score (0.0-1.0).
        frame: Frame number where detection occurred.
        mask: Optional polygon points for segmentation mask.
    """
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
    """Stores metadata for a captured detection image.

    Captures are taken at key moments during tracking to provide
    visual evidence for AI verification and human review.

    Attributes:
        frame: Frame number of the capture.
        image_path: Filesystem path to the saved capture image.
        bbox: Bounding box of the detection at capture time.
        reason: Why this capture was taken (e.g., "high_confidence").
        timestamp: Video timestamp in seconds.
    """

    frame: int
    image_path: str
    bbox: BoundingBox
    reason: str
    timestamp: float

    def to_dict(self) -> dict:
        """Convert capture to dictionary for serialization."""
        return asdict(self)

@dataclass
class TrackedDetection:
    """Represents a tracked object across multiple video frames.

    Maintains the complete history of bounding boxes and captures
    for a single detected entity (face, person, license plate).

    Attributes:
        track_id: Unique identifier for this track.
        detection_type: Type of detection (face, person, license_plate).
        bbox_history: List of all bounding boxes across frames.
        captures: List of captured images for this track.
        is_confirmed: Whether this detection has been AI-verified.
    """

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
    """Aggregates all detection results from a video processing run.

    Contains video metadata and a list of all tracked detections
    found during the detection phase.

    Attributes:
        video_path: Path to the processed video file.
        total_frames: Total number of frames in the video.
        fps: Frames per second of the video.
        duration_seconds: Video duration in seconds.
        width: Video width in pixels.
        height: Video height in pixels.
        detections: List of all tracked detections.
        frames_processed: Number of frames actually processed.
        processing_time_seconds: Total processing time.
    """

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
