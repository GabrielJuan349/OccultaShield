from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Optional
import os
import uuid
import shutil
import json
from pathlib import Path
from datetime import datetime

from core.dependencies import get_current_user, get_db
from models.video import (
    VideoResponse, VideoUploadResponse, VideoStatus, VideoMetadata, VideoAnalysisConfig,
    ViolationCard, PaginatedResponse, UserDecisionBatch, DetectionType, Severity
)
from services.video_processor import video_processor

router = APIRouter()

STORAGE_DIR = Path("storage")
UPLOAD_DIR = STORAGE_DIR / "uploads"
CAPTURES_DIR = STORAGE_DIR / "captures"
PROCESSED_DIR = STORAGE_DIR / "processed"

# Ensure directories exist
for d in [UPLOAD_DIR, CAPTURES_DIR, PROCESSED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    config_json: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    try:
        # 1. Validate file
        if not file.content_type.startswith("video/"):
            raise HTTPException(400, "Invalid file type")
        
        # 2. Generate ID
        video_id = f"vid_{uuid.uuid4().hex[:12]}"
        
        # 3. Save file
        file_ext = Path(file.filename).suffix
        safename = f"{video_id}{file_ext}"
        file_path = UPLOAD_DIR / safename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 4. Extract metadata (Placeholder)
        # TODO: Use OpenCV to extract real metadata
        metadata = VideoMetadata(
            duration_seconds=120.0,
            fps=30.0,
            width=1920,
            height=1080,
            total_frames=3600,
            has_audio=True
        )
        
        # 5. Create DB record
        video_data = {
            "id": video_id,
            "user_id": current_user["id"],
            "filename": file.filename,
            "original_path": str(file_path),
            "status": VideoStatus.PROCESSING.value,
            "metadata": metadata.model_dump(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Using connect/create logic. 
        # Note: SurrealDB CREATE usually takes `table:id` or just `table`
        # We manually assigned ID, so Create `video:vid_...`
        await db.create(f"video:{video_id}", video_data)
        
        # 6. Create progress record (Placeholder - should be done by processor init or here)
        # Assuming processor handles init of progress record via ProgressManager
        
        # 7. Launch processing
        background_tasks.add_task(video_processor.process_full_pipeline, video_id, str(file_path))
        
        return VideoUploadResponse(
            video_id=video_id,
            status=VideoStatus.PROCESSING,
            message="Video uploaded successfully. Processing started."
        )
        
    except Exception as e:
        # Clean up if failed
        if 'file_path' in locals() and os.path.exists(file_path):
             os.remove(file_path)
        raise HTTPException(500, f"Upload failed: {str(e)}")

@router.get("/{video_id}/status", response_model=VideoResponse)
async def get_video_status(
    video_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    # 1. Get video
    try:
        # Select returns a list or single object depending on if ID is specific
        # Explicitly fetching `video:ID`
        result = await db.select(f"video:{video_id}")
        video = result if not isinstance(result, list) else (result[0] if result else None)
        
        if not video:
            raise HTTPException(404, "Video not found")
            
        # 2. Validate owner (assuming user_id is stored simply or as record link)
        if video.get("user_id") != current_user["id"]:
            # Depending on how link is stored `user:ID` vs `ID`
            # For robustness, check string containment or exact match
            raise HTTPException(403, "Not owner of this video")
            
        return video
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error fetching status: {e}")

@router.get("/{video_id}/violations", response_model=PaginatedResponse)
async def get_violations(
    video_id: str,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    # Verify ownership first (omitted for brevity, assume similar check as above)
    
    # 3. Query Violations (Placeholder mock)
    # In real imp, query `verification` joined with `detection`
    # For Setup Phase, return empty or dummy
    
    items = [] # Populate with ViolationCard objects
    
    return PaginatedResponse(
        items=items,
        total=0,
        page=page,
        page_size=page_size,
        total_pages=0,
        has_next=False,
        has_prev=False
    )

@router.get("/{video_id}/capture/{track_id}/{filename}")
async def get_capture(
    video_id: str,
    track_id: int,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    # Security check omitted
    
    file_path = CAPTURES_DIR / video_id / f"track_{track_id}" / filename
    if not file_path.exists():
        raise HTTPException(404, "Capture not found")
        
    return FileResponse(file_path)

@router.post("/{video_id}/decisions")
async def submit_decisions(
    video_id: str,
    batch: UserDecisionBatch,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    # Logic to save decisions and trigger edition
    
    # Trigger Anonymization
    background_tasks.add_task(video_processor.apply_anonymization, video_id, batch.decisions)
    
    return {
        "status": "editing",
        "message": "Decisions saved. Anonymization started.",
        "video_id": video_id
    }

@router.get("/{video_id}/download")
async def download_video(
    video_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    # Get video path
    processed_path = PROCESSED_DIR / f"anonymized_{video_id}.mp4"
    if not processed_path.exists():
        raise HTTPException(404, "Processed video not available")
        
    return FileResponse(
        processed_path, 
        media_type="video/mp4", 
        filename=f"anonymized_{video_id}.mp4"
    )

@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    # Delete from DB and Storage
    try:
        await db.delete(f"video:{video_id}")
        # Clean storage
        # Placeholder for directory cleanup logic
        
        return {"status": "deleted", "video_id": video_id}
    except Exception as e:
        raise HTTPException(500, f"Delete failed: {e}")
