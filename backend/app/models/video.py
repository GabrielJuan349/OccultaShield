"""Video Processing Models for OccultaShield API.

This module defines all Pydantic models used in the video processing pipeline,
including enums for status tracking, request/response models for API endpoints,
and data structures for detections, verifications, and user decisions.

Sections:
    - Enums: VideoStatus, ProcessingPhase, DetectionType, Severity, AnonymizationAction
    - Base Models: BoundingBoxModel, CaptureEntry, VideoMetadata
    - Request Models: VideoAnalysisConfig, UserDecisionCreate, UserDecisionBatch
    - Response Models: VideoUploadResponse, VideoResponse, DetectionResponse, etc.
    - Filter Models: DetectionFilter

Example:
    >>> from models.video import VideoStatus, UserDecisionCreate, AnonymizationAction
    >>> decision = UserDecisionCreate(
    ...     verification_id="ver_123",
    ...     action=AnonymizationAction.BLUR,
    ...     confirmed_violation=True
    ... )
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator, ConfigDict


# --- Enums ---

class VideoStatus(str, Enum):
    """Video processing lifecycle status values.

    Tracks the state of a video through the OccultaShield pipeline:
    PENDING → UPLOADED → PROCESSING → DETECTED → VERIFIED →
    WAITING_FOR_REVIEW → ANONYMIZING → COMPLETED
    """

    PENDING = "pending"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    DETECTED = "detected"
    VERIFIED = "verified"
    WAITING_FOR_REVIEW = "waiting_for_review"
    ANONYMIZING = "anonymizing"
    COMPLETED = "completed"
    ERROR = "error"


class ProcessingPhase(str, Enum):
    """Real-time processing phase for SSE progress updates.

    More granular than VideoStatus, used for live progress feedback.
    """
    IDLE = "idle"
    UPLOADING = "uploading"
    DETECTING = "detecting"
    TRACKING = "tracking"
    VERIFYING = "verifying"
    SAVING = "saving"
    WAITING_FOR_REVIEW = "waiting_for_review" # New
    ANONYMIZING = "anonymizing" # New
    COMPLETED = "completed"
    ERROR = "error"

class DetectionType(str, Enum):
    """Types of GDPR-sensitive content that can be detected."""

    FACE = "face"
    LICENSE_PLATE = "license_plate"
    PERSON = "person"
    DOCUMENT = "document"
    MINOR = "minor"
    NUDE_BODY = "nude_body"
    OTHER = "other"


class Severity(str, Enum):
    """GDPR violation severity levels for risk assessment."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnonymizationAction(str, Enum):
    """Available anonymization effects for detected regions."""

    NO_MODIFY = "no_modify"
    BLUR = "blur"
    PIXELATE = "pixelate"
    MASK = "mask"


# --- Base Models ---

class BoundingBoxModel(BaseModel):
    """Bounding box coordinates with validation.

    Attributes:
        x1: Left edge x-coordinate.
        y1: Top edge y-coordinate.
        x2: Right edge x-coordinate (must be > x1).
        y2: Bottom edge y-coordinate (must be > y1).
        confidence: Detection confidence (0.0-1.0).
        frame: Frame number where detection occurred.
    """
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float = Field(..., ge=0.0, le=1.0)
    frame: int = Field(..., ge=0)

    @field_validator('x2')
    def validate_x2(cls, v, info):
        if 'x1' in info.data and v < info.data['x1']:
            raise ValueError('x2 must be greater than x1')
        return v
    
    @field_validator('y2')
    def validate_y2(cls, v, info):
        if 'y1' in info.data and v < info.data['y1']:
            raise ValueError('y2 must be greater than y1')
        return v

class CaptureEntry(BaseModel):
    """Metadata for a captured detection image.

    Attributes:
        frame: Frame number of the capture.
        image_path: Filesystem path to saved image.
        bbox: Bounding box at capture time.
        reason: Why this capture was taken.
        timestamp: Video timestamp in seconds.
    """

    frame: int
    image_path: str
    bbox: BoundingBoxModel
    reason: str
    timestamp: float


class VideoMetadata(BaseModel):
    """Technical metadata extracted from a video file.

    Attributes:
        duration_seconds: Video length.
        fps: Frames per second.
        width: Video width in pixels.
        height: Video height in pixels.
        total_frames: Total frame count.
        codec: Video codec (e.g., "h264").
        has_audio: Whether video has audio track.
    """

    duration_seconds: float
    fps: float
    width: int
    height: int
    total_frames: int
    codec: Optional[str] = None
    has_audio: bool = False


# --- Request Models ---

class VideoAnalysisConfig(BaseModel):
    """Configuration options for video analysis.

    Controls detection parameters, capture frequency,
    and verification settings.
    """
    detection_types: List[DetectionType] = [DetectionType.FACE, DetectionType.LICENSE_PLATE, DetectionType.PERSON]
    confidence_threshold: float = 0.5
    detection_interval: int = 3
    capture_interval: float = 1.5
    max_captures_per_detection: int = 8
    skip_verification: bool = False
    priority: str = "normal"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detection_types": ["face", "license_plate"],
                "confidence_threshold": 0.6,
                "skip_verification": False
            }
        }
    )

class UserDecisionCreate(BaseModel):
    verification_id: str
    action: AnonymizationAction
    confirmed_violation: bool = True
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None

class UserDecisionBatch(BaseModel):
    decisions: List[UserDecisionCreate] = []  # Allow empty list for no-violations case

# --- Response Models ---

class VideoUploadResponse(BaseModel):
    video_id: str
    status: VideoStatus
    message: str

class VideoResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    original_path: str
    processed_path: Optional[str] = None
    status: VideoStatus
    metadata: VideoMetadata
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class DetectionResponse(BaseModel):
    id: str
    video_id: str
    track_id: int
    detection_type: DetectionType
    first_frame: int
    last_frame: int
    duration_seconds: float
    avg_confidence: float
    max_confidence: float
    captures_count: int
    storage_path: Optional[str] = None

class VerificationResponse(BaseModel):
    id: str
    detection_id: str
    capture_index: int
    is_violation: bool
    severity: Severity = Severity.NONE
    violated_articles: List[str] = []
    detected_personal_data: List[str] = []
    description: str = ""
    recommended_action: str = ""
    confidence: float

class ViolationCard(BaseModel):
    verification_id: str
    detection_id: str
    track_id: int
    detection_type: DetectionType
    capture_image_url: str
    thumbnail_url: Optional[str] = None
    is_violation: bool
    severity: Severity
    article_title: Optional[str] = None
    article_subtitle: Optional[str] = None
    violated_articles: List[str] = []
    description: str
    fine_text: str
    recommended_action: str
    duration_seconds: float
    confidence: float
    first_frame: int
    last_frame: int

class ProcessingProgressResponse(BaseModel):
    video_id: str
    phase: ProcessingPhase
    current_frame: int
    total_frames: int
    percentage: int
    fps_processing: float
    active_detections: int
    total_detections: int
    total_violations: int
    message: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    estimated_time_remaining: Optional[float] = None

class VideoSummary(BaseModel):
    video_id: str
    filename: str
    status: VideoStatus
    duration_seconds: float
    total_detections: int
    total_violations: int
    violations_by_type: Dict[str, int]
    violations_by_severity: Dict[str, int]
    processing_time_seconds: Optional[float] = None
    compliance_status: str

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

# --- Filter Models ---

class DetectionFilter(BaseModel):
    detection_type: Optional[DetectionType] = None
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None
    min_duration: Optional[float] = None
    is_violation: Optional[bool] = None
    severity: Optional[Severity] = None
    page: int = 1
    page_size: int = 20
