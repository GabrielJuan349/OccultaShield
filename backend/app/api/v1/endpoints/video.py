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
    print(f"\n📤 [UPLOAD] New video upload request")
    print(f"   Filename: {file.filename}")
    print(f"   Content-Type: {file.content_type}")
    print(f"   User: {current_user.get('id', 'unknown')}")
    try:
        # 1. Validate file
        if not file.content_type.startswith("video/"):
            print(f"   ❌ Invalid file type")
            raise HTTPException(400, "Invalid file type")
        
        # 2. Generate ID
        video_id = f"vid_{uuid.uuid4().hex[:12]}"
        print(f"   ✅ Generated video ID: {video_id}")
        
        # 3. Save file
        file_ext = Path(file.filename).suffix
        safename = f"{video_id}{file_ext}"
        file_path = UPLOAD_DIR / safename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"   💾 File saved: {file_path}")

        # 4. Extract real metadata using OpenCV with proper resource management
        import cv2
        cap = None
        try:
            cap = cv2.VideoCapture(str(file_path))

            # Validate that video file opened successfully
            if not cap.isOpened():
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise HTTPException(400, "Video file is corrupted or invalid format")

            actual_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            actual_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Validate video has valid dimensions and frames
            if actual_frames == 0 or actual_width == 0 or actual_height == 0:
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise HTTPException(400, "Video has invalid dimensions or no frames")

            actual_duration = actual_frames / actual_fps if actual_fps > 0 else 0
        finally:
            if cap is not None:
                cap.release()
        
        metadata = VideoMetadata(
            duration_seconds=actual_duration,
            fps=actual_fps,
            width=actual_width,
            height=actual_height,
            total_frames=actual_frames,
            has_audio=True  # Assume true; proper check would require ffprobe
        )
        print(f"   📊 Metadata: {actual_frames} frames, {actual_fps:.1f} FPS, {actual_width}x{actual_height}")
        
        # 5. Create DB record with status UPLOADED (not processing yet)
        video_data = {
            "id": video_id,
            "user_id": current_user["id"],
            "filename": file.filename,
            "original_path": str(file_path),
            "status": "uploaded",  # User must click "Start Processing" to begin
            "metadata": metadata.model_dump(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        await db.create(f"video:{video_id}", video_data)
        print(f"   🗄️  Video record created in DB (status: uploaded)")

        # Auto-start processing
        from services.progress_manager import progress_manager
        await progress_manager.register_video(video_id)
        print(f"   📡 Registered in progress manager")

        background_tasks.add_task(video_processor.process_full_pipeline, video_id, str(file_path))
        print(f"   🚀 Background processing task launched")
        print(f"   ✅ Upload complete! Video ID: {video_id}\n")

        return VideoUploadResponse(
            video_id=video_id,
            status=VideoStatus.PROCESSING,
            message="Video uploaded successfully. Processing started automatically."
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

        # Validate required fields are present
        required_fields = ["id", "filename", "status", "created_at"]
        missing_fields = [f for f in required_fields if f not in video]
        if missing_fields:
            print(f"⚠️  Video record missing fields: {missing_fields}")
            raise HTTPException(500, f"Invalid video record: missing fields {missing_fields}")
            
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
    """
    Get all GDPR violations found in a video.
    Returns verification records with linked detection data.
    """
    try:
        # 1. Verify video ownership
        db_video_id = video_id if video_id.startswith("video:") else f"video:{video_id}"
        video_result = await db.select(db_video_id)
        video = video_result if not isinstance(video_result, list) else (video_result[0] if video_result else None)

        if not video:
            raise HTTPException(404, "Video not found")

        if video.get("user_id") != current_user["id"]:
            raise HTTPException(403, "Not authorized")

        # 2. Query all verifications for this video (with detection data)
        # Using SurrealDB query to fetch verifications where detection.video = video_id
        query = f"""
            SELECT * FROM gdpr_verification
            WHERE detection.video = {db_video_id}
            FETCH detection
        """

        verifications = await db.query(query)

        # Extract results from query response
        # SurrealDB returns [{'result': [...], 'status': 'OK', 'time': '...'}]
        if isinstance(verifications, list) and len(verifications) > 0:
            verification_records = verifications[0].get('result', [])
        else:
            verification_records = []

        # 3. Map to ViolationCard objects
        items = []
        for v_rec in verification_records:
            # Get linked detection data
            det_data = v_rec.get('detection', {})

            # Handle if detection is a string ID (fetch it)
            if isinstance(det_data, str):
                det_result = await db.select(det_data)
                det_data = det_result if not isinstance(det_result, list) else (det_result[0] if det_result else {})

            # Get capture image from detection captures
            captures = det_data.get('captures', [])
            first_capture = captures[0] if captures else {}

            # Build capture image URL
            track_id = det_data.get('track_id', 0)
            capture_filename = first_capture.get('filename', 'capture_0.jpg')
            capture_url = f"/api/v1/video/{video_id}/capture/{track_id}/{capture_filename}"

            # Create ViolationCard
            items.append(ViolationCard(
                verification_id=v_rec.get('id', ''),
                detection_id=det_data.get('id', ''),
                track_id=track_id,
                detection_type=DetectionType(det_data.get('detection_type', 'unknown')),
                capture_image_url=capture_url,
                is_violation=v_rec.get('is_violation', False),
                severity=Severity(v_rec.get('severity', 'none')),
                violated_articles=v_rec.get('violated_articles', []),
                description=v_rec.get('description', ''),
                recommended_action=v_rec.get('recommended_action', 'none'),
                confidence=v_rec.get('confidence', 0.0),
                first_frame=det_data.get('first_frame', 0),
                last_frame=det_data.get('last_frame', 0),
                frames_analyzed=v_rec.get('frames_analyzed', 1),
                frames_with_violation=v_rec.get('frames_with_violation', 0)
            ))

        # 4. Pagination (simple in-memory for now)
        total = len(items)
        total_pages = (total + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = items[start_idx:end_idx]

        return PaginatedResponse(
            items=paginated_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching violations: {e}")
        raise HTTPException(500, f"Error fetching violations: {str(e)}")

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
    user_display_name = current_user.get("name") or current_user.get("id", "unknown")
    background_tasks.add_task(video_processor.apply_anonymization, video_id, batch.decisions, user_display_name)
    
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
