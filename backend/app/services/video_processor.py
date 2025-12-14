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
            # We need to transform DetectionResult objects to DB records
            # For each tracked object:
            detections_data = []
            for track in detection_result.detections:
                 d_record = {
                     "video_id": video_id,
                     "track_id": track.track_id,
                     "detection_type": track.detection_type,
                     "bbox_history": [b.to_dict() for b in track.bbox_history],
                     "captures": [c.to_dict() for c in track.captures],
                     # ... other fields
                 }
                 # Insert detection
                 # DB insert logic here...
                 created = await db_conn.create("detection", d_record)
                 detections_data.append(created[0] if created else d_record)

            await progress_manager.change_phase(video_id, ProcessingPhase.VERIFYING, "Verifying GDPR compliance...")
            
            # --- VERIFICATION PHASE ---
            # Call verification module (mock integration for now or real if available)
            # verify_video_content(video_id, detections...)
            # We'll simulate verification delay or call real logic if Phase 1 code is ready
            # Phase 1 code: modules.verification.__init__ exposes logic working with Neo4j
            
            # Assuming verify_video_content takes detection data and verifies it
            # results = await verify_video_content(detections_data)
            await asyncio.sleep(2) # Placeholder for actual verification call
            
            # Create dummy violations for testing if verification not fully wired to DB result
            await progress_manager.report_verification(video_id, "vuln_1", "violation", 1, 1)
            
            await progress_manager.complete(
                video_id, 
                total_vulnerabilities=len(detection_result.detections), 
                total_violations=0 # Placeholder
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
