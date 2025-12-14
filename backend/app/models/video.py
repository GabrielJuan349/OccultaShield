from datetime import datetime
from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator, ConfigDict

# --- Enums ---

class VideoStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DETECTED = "detected"
    VERIFIED = "verified"
    EDITING = "editing"
    COMPLETED = "completed"
    ERROR = "error"

class ProcessingPhase(str, Enum):
    PENDING = "pending"
    DETECTING = "detecting"
    TRACKING = "tracking"
    VERIFYING = "verifying"
    SAVING = "saving"
    EDITING = "editing"
    COMPLETED = "completed"
    ERROR = "error"

class DetectionType(str, Enum):
    FACE = "face"
    LICENSE_PLATE = "license_plate"
    PERSON = "person"
    DOCUMENT = "document"
    MINOR = "minor"
    NUDE_BODY = "nude_body"
    OTHER = "other"

class Severity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AnonymizationAction(str, Enum):
    NO_MODIFY = "no_modify"
    BLUR = "blur"
    PIXELATE = "pixelate"
    MASK = "mask"

# --- Base Models ---

class BoundingBoxModel(BaseModel):
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
    frame: int
    image_path: str
    bbox: BoundingBoxModel
    reason: str
    timestamp: float

class VideoMetadata(BaseModel):
    duration_seconds: float
    fps: float
    width: int
    height: int
    total_frames: int
    codec: Optional[str] = None
    has_audio: bool = False

# --- Request Models ---

class VideoAnalysisConfig(BaseModel):
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
    decisions: List[UserDecisionCreate]

    @field_validator('decisions')
    def validate_decisions_not_empty(cls, v):
        if not v:
            raise ValueError('Decisions list cannot be empty')
        return v

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
