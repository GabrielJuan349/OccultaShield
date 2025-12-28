import asyncio
from typing import Optional, List
from pathlib import Path
import json

from services.progress_manager import progress_manager, ProcessingPhase
from modules.detection.detector import VideoDetector
from modules.edition.video_editor import VideoAnonymizer
from modules.verification import verify_video_content # Assuming this exists from Phase 1
from core.dependencies import _db_instance

class VideoProcessor:
    """
    Orchestrates the video processing pipeline: Detection -> Verification -> Edition.
    """
    def __init__(self):
        # Initialize modules
        import os
        model_path = os.environ.get("DETECTION_MODEL_PATH")
        if not model_path:
             raise ValueError("DETECTION_MODEL_PATH environment variable is required")
        
        self.detector = VideoDetector(model_path=model_path) 
        self.anonymizer = VideoAnonymizer()
        
    async def process_full_pipeline(self, video_id: str, input_path: str):
        """
        Runs the full processing pipeline for a video.
        """
        try:
            db_conn = await _db_instance.getting_db("test")
            
            # 1. Register progress
            await progress_manager.register_video(video_id)
            await progress_manager.change_phase(video_id, ProcessingPhase.DETECTING, "Starting detection...")
            
            # --- DETECTION PHASE ---
            output_dir = Path("storage/captures") / video_id
            
            # Progress callback wrapper
            async def on_detection_progress(current, total, msg):
                pct = int((current / total) * 100)
                await progress_manager.update_progress(video_id, pct, current, total, msg)
                
            detection_result = await self.detector.process_video(
                input_path, 
                str(output_dir), 
                on_progress=on_detection_progress
            )
            
            # Save Detections to DB
            saved_detections_map = {} # track_id -> db_record_id
            
            for track in detection_result.detections:
                 d_record = {
                     "video_id": video_id,
                     "track_id": track.track_id,
                     "detection_type": track.detection_type,
                     "first_frame": track.first_frame,
                     "last_frame": track.last_frame,
                     "avg_confidence": track.avg_confidence,
                     # bbox_history and captures should be compatible lists
                     "bbox_history": [b.to_dict() for b in track.bbox_history],
                     "captures": [c.to_dict() for c in track.captures],
                 }
                 
                 # Create detection record
                 # Since video_id is a string, we ensure it's a record pointer or ID
                 # In Surreal, link is usually record<video>. If video_id is "video:123", it works.
                 # If user passed "123", we might need to format. Assuming video_id is proper ID or we use text.
                 # Schema says: video_id ON TABLE detection TYPE record<video>
                 # So we need "video:ID".
                 if not video_id.startswith("video:"):
                     d_record["video_id"] = f"video:{video_id}"
                 else:
                     d_record["video_id"] = video_id
                     
                 created = await db_conn.create("detection", d_record)
                 if created:
                     saved_detections_map[track.track_id] = created[0]['id']

            await progress_manager.change_phase(video_id, ProcessingPhase.VERIFYING, "Verifying GDPR compliance...")
            
            # --- VERIFICATION PHASE ---
            from modules.verification import verify_image_detections
            
            total_violations = 0
            
            # Verify each tracked object
            # We select the best capture for each track to verify context
            for track in detection_result.detections:
                if not track.captures:
                    continue
                    
                # Pick the capture with highest stability or just the last one
                # For now, taking the last capture
                best_capture = track.captures[-1]
                
                db_det_id = saved_detections_map.get(track.track_id)
                if not db_det_id: continue
                
                det_payload = {
                    "id": db_det_id, # Passes DB ID for result correlation
                    "detection_type": track.detection_type,
                    "bbox": best_capture.bbox.to_dict()
                }
                
                # Perform verification
                v_results = await verify_image_detections(best_capture.image_path, [det_payload])
                
                for res in v_results:
                    # Save "gdpr_verification" record
                    is_violation = res.get("is_violation", False)
                    if is_violation: total_violations += 1
                    
                    v_record = {
                        "detection_id": res.get("detection_id"), 
                        "is_violation": is_violation,
                        "severity": res.get("severity", "none"),
                        "description": res.get("reasoning", ""),
                        "violated_articles": res.get("violated_articles", []),
                        "confidence": res.get("confidence", 0.0),
                        "llm_raw_response": str(res)
                    }
                    await db_conn.create("gdpr_verification", v_record)
            
            await progress_manager.report_verification(video_id, "summary", "completed", len(detection_result.detections), total_violations)
            
            await progress_manager.complete(
                video_id, 
                total_vulnerabilities=len(detection_result.detections), 
                total_violations=total_violations
            )
            
        except Exception as e:
            await progress_manager.error(video_id, "PROCESSING_ERROR", str(e))
            print(f"Error processing video {video_id}: {e}")

    async def apply_anonymization(self, video_id: str, decisions: list):
        """
        Applies anonymization based on user decisions.
        """
        try:
            db_conn = await _db_instance.getting_db("test")
            
            await progress_manager.change_phase(video_id, ProcessingPhase.EDITING, "Applying anonymization...")
            
            # 1. Fetch Video Info
            # 2. Fetch Detection History for confirmed violations needing action
            # 3. Construct Actions Map for Anonymizer
            
            # Placeholder:
            actions = [] # Fill from DB decisions
            
            input_path = "storage/uploads/..." # Need to fetch from DB
            output_path = f"storage/processed/anonymized_{video_id}.mp4"
            
            await self.anonymizer.apply_anonymization(input_path, output_path, actions)
            
            await progress_manager.change_phase(video_id, ProcessingPhase.COMPLETED, "Video ready.")
            
        except Exception as e:
            await progress_manager.error(video_id, "EDITION_ERROR", str(e))

# Singleton instance
video_processor = VideoProcessor()
