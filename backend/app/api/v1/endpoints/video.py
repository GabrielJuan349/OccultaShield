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


def normalize_user_id(user_id) -> str:
    """
    Normaliza un user_id para comparaciones consistentes.
    Maneja formatos: RecordID objects, "user:⟨UUID⟩", "user:UUID", o solo "UUID"
    Retorna siempre el formato "user:UUID" sin corchetes angulares.
    """
    user_str = str(user_id).replace("⟨", "").replace("⟩", "")
    if not user_str.startswith("user:"):
        return f"user:{user_str}"
    return user_str


def normalize_video_id(video_id: str) -> str:
    """
    Normaliza un video_id para queries de SurrealDB.
    Retorna el formato "video:`ID`" con backticks para evitar interpretación de guiones como resta.
    """
    # Remover prefijo si ya existe
    vid = video_id.replace("video:", "").replace("`", "")
    return f"video:`{vid}`"


def extract_uuid_from_user_id(user_id) -> str:
    """
    Extrae solo el UUID de un user_id en cualquier formato.
    """
    user_str = str(user_id).replace("⟨", "").replace("⟩", "")
    if user_str.startswith("user:"):
        return user_str[5:]  # Remover "user:"
    return user_str


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
        
        # 5. Create DB record with initial status PENDING
        # Schema permite: ['pending', 'processing', 'detected', 'verified', 'editing', 'completed', 'error']
        # Usar query raw para manejar correctamente record<user>
        user_id_raw = current_user["id"]  # Ej: "user:⟨019bb260-300d-7802-ad8d-f95a9690416b⟩"

        # Extraer solo el UUID del user_id para construir el record reference
        # El formato puede ser "user:⟨UUID⟩" o "user:UUID"
        if "⟨" in user_id_raw:
            user_uuid = user_id_raw.split("⟨")[1].rstrip("⟩")
        else:
            user_uuid = user_id_raw.replace("user:", "")

        print(f"   🔍 [UPLOAD] Creando video en DB: video:{video_id}")
        print(f"   🔍 [UPLOAD] User UUID extraído: {user_uuid}")

        # Usar query raw para insertar con el tipo record<user> correcto
        import json
        metadata_json = json.dumps(metadata.model_dump())
        escaped_filename = file.filename.replace("'", "\\'")
        escaped_path = str(file_path).replace("'", "\\'")

        # Usar backticks para escapar los IDs con guiones (SurrealDB los interpreta como resta)
        query = f"""
            CREATE video:`{video_id}` SET
                user_id = user:`{user_uuid}`,
                filename = '{escaped_filename}',
                original_path = '{escaped_path}',
                status = 'pending',
                metadata = {metadata_json},
                error_message = '',
                processed_path = '',
                processing_started_at = time::now(),
                processing_completed_at = time::now()
        """

        print(f"   🔍 [UPLOAD] Query: {query[:200]}...")
        try:
            create_result = await db.query(query)
            print(f"   🔍 [UPLOAD] Create result: {create_result}")
            print(f"   🗄️  Video record created in DB (status: pending)")
        except Exception as e:
            print(f"   ❌ [UPLOAD] Error en query: {e}")
            import traceback
            traceback.print_exc()
            raise

        # Verificar inmediatamente que se creó (usar backticks)
        verify_result = await db.select(f"video:`{video_id}`")
        print(f"   🔍 [UPLOAD] Verification select result: {verify_result}")

        # Register video in progress manager (but don't start processing yet)
        from services.progress_manager import progress_manager
        await progress_manager.register_video(video_id)
        print(f"   📡 Registered in progress manager")
        print(f"   ⏸️  Waiting for frontend SSE connection to auto-start processing")
        print(f"   ✅ Upload complete! Video ID: {video_id}\n")

        return VideoUploadResponse(
            video_id=video_id,
            status=VideoStatus.UPLOADED,
            message="Video uploaded successfully. Processing will start automatically when you connect to SSE."
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
        # Usar backticks para evitar interpretación de guiones como resta
        result = await db.select(f"video:`{video_id}`")
        video = result if not isinstance(result, list) else (result[0] if result else None)

        if not video:
            raise HTTPException(404, "Video not found")

        # Validate required fields are present
        required_fields = ["id", "filename", "status", "created_at"]
        missing_fields = [f for f in required_fields if f not in video]
        if missing_fields:
            print(f"⚠️  Video record missing fields: {missing_fields}")
            raise HTTPException(500, f"Invalid video record: missing fields {missing_fields}")
            
        # 2. Validate owner (normalize both IDs for consistent comparison)
        if normalize_user_id(video.get("user_id")) != normalize_user_id(current_user["id"]):
            raise HTTPException(403, "Not owner of this video")
            
        return video
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error fetching status: {e}")

@router.get("/{video_id}/violations", response_model=PaginatedResponse)
async def get_violations(
    video_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get all GDPR violations found in a video.
    Returns ALL verification records with linked detection data (no pagination).
    """
    try:
        # 1. Verify video ownership (use normalized IDs with backticks)
        db_video_id = normalize_video_id(video_id)
        video_result = await db.select(db_video_id)
        video = video_result if not isinstance(video_result, list) else (video_result[0] if video_result else None)

        if not video:
            raise HTTPException(404, "Video not found")

        if normalize_user_id(video.get("user_id")) != normalize_user_id(current_user["id"]):
            raise HTTPException(403, "Not authorized")

        # 2. Get ALL detections and filter in Python (RecordID comparison in SurrealDB is problematic)
        all_det_query = "SELECT * FROM detection"
        all_det_result = await db.query(all_det_query)

        print(f"[VIOLATIONS DEBUG] Raw query result type: {type(all_det_result)}, len: {len(all_det_result) if isinstance(all_det_result, list) else 'N/A'}")

        all_detections = []
        if isinstance(all_det_result, list) and len(all_det_result) > 0:
            first_item = all_det_result[0]
            print(f"[VIOLATIONS DEBUG] First item type: {type(first_item)}, keys: {first_item.keys() if isinstance(first_item, dict) else 'N/A'}")
            if isinstance(first_item, dict) and 'result' in first_item:
                all_detections = first_item.get('result', [])
            elif isinstance(first_item, dict):
                # Maybe it's direct records without 'result' wrapper
                all_detections = all_det_result
            else:
                all_detections = all_det_result

        print(f"[VIOLATIONS DEBUG] all_detections count: {len(all_detections)}")
        if all_detections:
            # Only print essential fields, not the huge bbox_history/mask data
            first_det = all_detections[0] if isinstance(all_detections[0], dict) else {}
            first_video_id = first_det.get('video_id')
            print(f"[VIOLATIONS DEBUG] First detection: id={first_det.get('id')}, video_id={first_video_id}, track_id={first_det.get('track_id')}")
            print(f"[VIOLATIONS DEBUG] First detection video_id type: {type(first_video_id)}")

        # Filter detections that match this video_id (check string representation)
        detection_records = []
        for det in all_detections:
            if not isinstance(det, dict):
                continue
            det_video_id = det.get('video_id')
            # Convert to string and check if it contains our video_id
            det_video_str = str(det_video_id)
            if video_id in det_video_str:
                detection_records.append(det)

        print(f"[VIOLATIONS] video_id: {video_id}, found {len(detection_records)} detections (from {len(all_detections)} total)")

        # 3. First, get ALL verifications to debug
        all_verif_query = "SELECT * FROM gdpr_verification"
        all_verif_result = await db.query(all_verif_query)
        all_verifications = []
        if isinstance(all_verif_result, list) and len(all_verif_result) > 0:
            all_verifications = all_verif_result[0].get('result', []) if isinstance(all_verif_result[0], dict) and 'result' in all_verif_result[0] else all_verif_result

        print(f"[VIOLATIONS DEBUG] Total verifications in DB: {len(all_verifications)}")
        if all_verifications:
            first_v = all_verifications[0] if isinstance(all_verifications[0], dict) else {}
            print(f"[VIOLATIONS DEBUG] First verification: id={first_v.get('id')}, detection_id={first_v.get('detection_id')}, type={type(first_v.get('detection_id'))}")

        # Build a map of detection_id -> verifications for faster lookup
        verif_by_detection = {}
        for v in all_verifications:
            if not isinstance(v, dict):
                continue
            v_det_id = v.get('detection_id')
            v_det_str = str(v_det_id)
            if v_det_str not in verif_by_detection:
                verif_by_detection[v_det_str] = []
            verif_by_detection[v_det_str].append(v)

        print(f"[VIOLATIONS DEBUG] Verification map keys: {list(verif_by_detection.keys())[:5]}")

        # 3. For each detection, get its verification from the map
        verification_records = []
        for det in detection_records:
            det_id = det.get('id')
            if not det_id:
                continue

            det_id_str = str(det_id)
            v_records = verif_by_detection.get(det_id_str, [])

            print(f"[VIOLATIONS DEBUG] Detection {det_id_str} has {len(v_records)} verifications")

            for v_rec in v_records:
                # Attach the detection data to the verification record
                v_rec['detection_id'] = det
                verification_records.append(v_rec)

        print(f"[VIOLATIONS DEBUG] Total verifications: {len(verification_records)}")

        # 4. Map to ViolationCard objects
        items = []
        for v_rec in verification_records:
            # Get linked detection data (field is 'detection_id', fetched via FETCH detection_id)
            det_data = v_rec.get('detection_id', {})

            # Handle if detection is a string ID or RecordID (fetch it manually)
            if isinstance(det_data, str) or (det_data and not isinstance(det_data, dict)):
                det_id_str = str(det_data)
                det_result = await db.select(det_id_str)
                det_data = det_result if not isinstance(det_result, list) else (det_result[0] if det_result else {})

            # Get capture image from detection captures
            captures = det_data.get('captures', [])
            first_capture = captures[0] if captures else {}

            # Build capture image URL
            track_id = det_data.get('track_id', 0)
            capture_filename = first_capture.get('filename', 'capture_0.jpg')
            capture_url = f"/api/v1/video/{video_id}/capture/{track_id}/{capture_filename}"

            # Calculate duration from frames if available
            first_frame = det_data.get('first_frame', 0)
            last_frame = det_data.get('last_frame', 0)
            duration_seconds = det_data.get('duration_seconds', 0.0)

            # Generate fine_text based on severity
            severity_val = v_rec.get('severity', 'none')
            fine_texts = {
                'critical': 'Multa potencial: hasta 20M€ o 4% facturación global',
                'high': 'Multa potencial: hasta 10M€ o 2% facturación global',
                'medium': 'Advertencia formal con posible sanción',
                'low': 'Recomendación de corrección',
                'none': 'Sin riesgo identificado'
            }
            fine_text = fine_texts.get(severity_val, 'No determinado')

            # Create ViolationCard with all required fields
            items.append(ViolationCard(
                verification_id=str(v_rec.get('id', '')),
                detection_id=str(det_data.get('id', '')),
                track_id=track_id,
                detection_type=DetectionType(det_data.get('detection_type', 'face')),
                capture_image_url=capture_url,
                is_violation=v_rec.get('is_violation', False),
                severity=Severity(severity_val),
                violated_articles=v_rec.get('violated_articles', []),
                description=v_rec.get('description', ''),
                fine_text=fine_text,
                recommended_action=v_rec.get('recommended_action', 'blur'),
                duration_seconds=duration_seconds,
                confidence=v_rec.get('confidence', 0.0),
                first_frame=first_frame,
                last_frame=last_frame
            ))

        # Return all items (no pagination - frontend handles scroll)
        total = len(items)
        print(f"[VIOLATIONS] Returning {total} violations to frontend")

        return PaginatedResponse(
            items=items,
            total=total,
            page=1,
            page_size=total,
            total_pages=1,
            has_next=False,
            has_prev=False
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
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    # Security check: Verify ownership
    try:
        # Check video ownership first
        simple_video_id = f"video:`{video_id}`"
        # We need to fetch the video to check the user
        result = await db.select(f"video:`{video_id}`") # Use backticks for safety
        if not result:
             raise HTTPException(404, "Video not found")
             
        video = result[0] if isinstance(result, list) else result
        
        if normalize_user_id(video.get("user_id")) != normalize_user_id(current_user["id"]):
            raise HTTPException(403, "Not authorized to view captures for this video")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error checking capture ownership: {e}")
        raise HTTPException(500, "Error verifying capture access")
    
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
    """
    Submit user decisions for violations and trigger anonymization.
    """
    print(f"\n📝 [DECISIONS] Received decisions for video: {video_id}")
    print(f"   Decisions count: {len(batch.decisions)}")
    
    # Security: Verify ownership BEFORE updating
    try:
        result = await db.select(f"video:`{video_id}`")
        if not result:
            raise HTTPException(404, "Video not found")
        
        video = result[0] if isinstance(result, list) else result
        
        if normalize_user_id(video.get("user_id")) != normalize_user_id(current_user["id"]):
            raise HTTPException(403, "Not authorized to submit decisions for this video")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error verifying ownership: {e}")

    # Update video status to 'editing' (schema allowed) BEFORE starting background task
    # This prevents the SSE endpoint from restarting the full pipeline
    db_video_id = f"video:`{video_id}`"
    await db.update(db_video_id, {"status": "editing"})
    print(f"   ✅ Updated video status to 'editing' (anonymizing phase)")
    
    # Trigger Anonymization in background
    user_display_name = current_user.get("name") or current_user.get("id", "unknown")
    background_tasks.add_task(video_processor.apply_anonymization, video_id, batch.decisions, user_display_name)
    print(f"   🚀 Started anonymization task in background")
    
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
    # Get video info from DB to find the correct path
    simple_video_id = f"video:`{video_id}`" # Use backticks
    result = await db.select(simple_video_id)
    
    if not result:
        raise HTTPException(404, "Video not found")
        
    video_record = result[0] if isinstance(result, list) else result
    
    # Security: Verify ownership
    if normalize_user_id(video_record.get("user_id")) != normalize_user_id(current_user["id"]):
        raise HTTPException(403, "Not authorized to download this video")

    db_path = video_record.get("processed_path")
    
    # Validation logic
    if not db_path:
        # Fallback to default naming if DB path is missing but file exists
        fallback_path = PROCESSED_DIR / f"anonymized_{video_id}.mp4"
        if fallback_path.exists():
            final_path = fallback_path
        else:
            raise HTTPException(404, "Processed video path not found in DB")
    else:
        final_path = Path(db_path)
    
    if not final_path.exists():
        print(f"❌ Video file not found at: {final_path}")
        raise HTTPException(404, "Processed video file deleted or missing")
        
    return FileResponse(
        final_path, 
        media_type="video/mp4", 
        filename=final_path.name
    )

@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    # Delete from DB and Storage (usar backticks)
    try:
        # Security: Check ownership first
        result = await db.select(f"video:`{video_id}`")
        if not result:
            raise HTTPException(404, "Video not found")
            
        video = result[0] if isinstance(result, list) else result
        
        if normalize_user_id(video.get("user_id")) != normalize_user_id(current_user["id"]):
            raise HTTPException(403, "Not authorized to delete this video")
            
        await db.delete(f"video:`{video_id}`")
        # Clean storage
        # Placeholder for directory cleanup logic
        
        return {"status": "deleted", "video_id": video_id}
    except Exception as e:
        raise HTTPException(500, f"Delete failed: {e}")
