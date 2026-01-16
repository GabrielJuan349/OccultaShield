"""SSE Event Models for Video Processing Progress.

This module defines Pydantic models for Server-Sent Events (SSE) used to
communicate real-time processing progress to connected clients.

Event Types:
    ProgressEvent: General progress update with percentage.
    PhaseChangeEvent: Processing phase transition notification.
    DetectionEvent: New detection found during analysis.
    VerificationEvent: AI verification progress update.
    CompleteEvent: Processing completed successfully.
    ErrorEvent: Error occurred during processing.

Example:
    >>> event = ProgressEvent(phase=ProcessingPhase.DETECTING, progress=50, message="Analyzing...")
    >>> sse_string = event.to_sse()  # Formats for SSE transmission
"""

from pydantic import BaseModel
from typing import Literal, Optional, Any
from enum import Enum
from datetime import datetime


class ProcessingPhase(str, Enum):
    """Enumeration of video processing phases.

    Represents the different stages a video goes through during
    GDPR compliance analysis and anonymization.
    """
    IDLE = "idle"
    UPLOADING = "uploading"
    DETECTING = "detecting"
    TRACKING = "tracking"
    VERIFYING = "verifying"
    SAVING = "saving"
    WAITING_FOR_REVIEW = "waiting_for_review" # New phase
    ANONYMIZING = "anonymizing" # New phase
    COMPLETED = "completed"
    ERROR = "error"

class SSEEventType(str, Enum):
    PHASE_CHANGE = "phase_change"
    PROGRESS = "progress"
    DETECTION = "detection"
    VERIFICATION = "verification"
    MESSAGE = "message"
    COMPLETE = "complete"
    ERROR = "error"
    HEARTBEAT = "heartbeat"

class ProgressEvent(BaseModel):
    """Evento de progreso general."""
    event_type: SSEEventType = SSEEventType.PROGRESS
    phase: ProcessingPhase
    progress: int  # 0-100
    current: Optional[int] = None  # Frame/item actual
    total: Optional[int] = None    # Total frames/items
    message: str
    timestamp: datetime = datetime.now()
    
    def to_sse(self) -> str:
        import json
        data = self.model_dump(mode='json')
        return f"event: {self.event_type.value}\ndata: {json.dumps(data)}\n\n"

class PhaseChangeEvent(BaseModel):
    """Evento de cambio de fase."""
    event_type: SSEEventType = SSEEventType.PHASE_CHANGE
    phase: ProcessingPhase
    previous_phase: Optional[ProcessingPhase] = None
    message: str
    estimated_time_seconds: Optional[int] = None
    timestamp: datetime = datetime.now()
    
    def to_sse(self) -> str:
        import json
        data = self.model_dump(mode='json')
        return f"event: {self.event_type.value}\ndata: {json.dumps(data)}\n\n"

class DetectionEvent(BaseModel):
    """Evento cuando se detecta algo nuevo."""
    event_type: SSEEventType = SSEEventType.DETECTION
    detection_type: str  # face, license_plate, etc.
    count: int
    frame_number: int
    confidence: float
    message: str
    timestamp: datetime = datetime.now()
    
    def to_sse(self) -> str:
        import json
        data = self.model_dump(mode='json')
        return f"event: {self.event_type.value}\ndata: {json.dumps(data)}\n\n"

class VerificationEvent(BaseModel):
    """Evento de progreso de verificación."""
    event_type: SSEEventType = SSEEventType.VERIFICATION
    vulnerability_id: str
    status: str  # analyzing, verified, violation
    agents_completed: int
    total_agents: int
    message: str
    timestamp: datetime = datetime.now()
    
    def to_sse(self) -> str:
        import json
        data = self.model_dump(mode='json')
        return f"event: {self.event_type.value}\ndata: {json.dumps(data)}\n\n"

class CompleteEvent(BaseModel):
    """Evento de procesamiento completado."""
    event_type: SSEEventType = SSEEventType.COMPLETE
    video_id: str
    total_vulnerabilities: int
    total_violations: int
    processing_time_seconds: float
    redirect_url: str
    message: str
    timestamp: datetime = datetime.now()
    
    def to_sse(self) -> str:
        import json
        data = self.model_dump(mode='json')
        return f"event: {self.event_type.value}\ndata: {json.dumps(data)}\n\n"

class ErrorEvent(BaseModel):
    """Evento de error."""
    event_type: SSEEventType = SSEEventType.ERROR
    code: str
    message: str
    details: Optional[str] = None
    recoverable: bool = False
    timestamp: datetime = datetime.now()
    
    def to_sse(self) -> str:
        import json
        data = self.model_dump(mode='json')
        return f"event: {self.event_type.value}\ndata: {json.dumps(data)}\n\n"