import asyncio
import os
import logging
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import json

from services.progress_manager import progress_manager, ProcessingPhase
from modules.detection.detector import VideoDetector
from modules.edition.video_editor import VideoAnonymizer
from modules.verification.parallel_processor import ParallelProcessor
from core.dependencies import _db_instance

logger = logging.getLogger('video_processor')

class VideoProcessor:
    """
    Orchestrates the video processing pipeline.
    Phase 1: Detection -> Verification -> DB Persistence (Waits for User)
    Phase 2: Edition (triggered by user) -> Final Video
    """
    def __init__(self):
        # Initialize modules
        self.detector = VideoDetector() 
        self.verifier = ParallelProcessor(max_workers=4)
        self.anonymizer = VideoAnonymizer(use_gpu=True)
        
    async def process_full_pipeline(self, video_id: str, input_path: str):
        """
        Runs Phase 1: Detection and Verification.
        Saves results to DB sets status to 'WAITING_FOR_REVIEW'.
        """
        db_conn = None
        try:
            logger.info(f"Starting pipeline for {video_id}")
            db_conn = await _db_instance.getting_db("test") 
            
            # --- 0. INIT ---
            await progress_manager.register_video(video_id)
            await progress_manager.change_phase(video_id, ProcessingPhase.DETECTING, "Starting detection analysis...")
            
            # --- 1. DETECTION PHASE ---
            output_dir = Path("storage/captures") / video_id
            output_dir.mkdir(parents=True, exist_ok=True)
            
            detection_result = await self.detector.process_video(
                video_id=video_id,
                video_path=input_path, 
                output_dir=str(output_dir)
            )
            
            # Save Detections to DB
            saved_detections_map = {} # track_id -> db_record_id
            
            # Ensure video_id format for DB linking (video:ID)
            db_video_id = video_id if video_id.startswith("video:") else f"video:{video_id}"

            for track in detection_result.detections:
                 d_record = {
                     "video": db_video_id,
                     "track_id": track.track_id,
                     "detection_type": track.detection_type,
                     "first_frame": track.first_frame,
                     "last_frame": track.last_frame,
                     "avg_confidence": track.avg_confidence,
                     # Store full history for later edition
                     "bbox_history": [b.to_dict() for b in track.bbox_history],
                     "captures": [c.to_dict() for c in track.captures],
                 }
                 
                 # Create detection record
                 created = await db_conn.create("detection", d_record)
                 if created:
                     # Surreal returns list of created records, take first
                     rec = created[0] if isinstance(created, list) else created
                     saved_detections_map[track.track_id] = rec['id']

            # --- 2. VERIFICATION PHASE (Temporal Consensus Mode) ---
            await progress_manager.change_phase(video_id, ProcessingPhase.VERIFYING, "Verifying GDPR compliance...")
            
            verification_requests = []
            
            for track in detection_result.detections:
                if not track.captures: continue
                
                db_det_id = saved_detections_map.get(track.track_id)
                if not db_det_id: continue
                
                # Temporal Consensus: Send ALL captures for this track (up to 6)
                # Each capture will be verified independently, then aggregated by ConsensusAgent
                for capture in track.captures:
                    verification_requests.append({
                        "image_path": capture.image_path,
                        "detection": {
                            "id": db_det_id,  # Link result to DB record ID
                            "track_id": track.track_id, 
                            "detection_type": track.detection_type,
                            "bbox": capture.bbox.to_dict(),
                            "frame": capture.frame,
                            "timestamp": capture.timestamp
                        }
                    })
            
            await progress_manager.change_phase(video_id, ProcessingPhase.VERIFYING, f"Analyzing {len(verification_requests)} objects...")
            
            v_results = await self.verifier.process_requests(video_id, verification_requests)
            
            total_violations = 0
            for res in v_results:
                # detection_id here is the DB ID we passed
                det_db_id = res.get("detection_id")
                is_violation = res.get("is_violation", False)
                if is_violation: total_violations += 1
                
                v_record = {
                    "detection": det_db_id,  # Link to detection table
                    "is_violation": is_violation,
                    "severity": res.get("severity", "none"),
                    "description": res.get("reasoning", ""),
                    "violated_articles": res.get("violated_articles", []),
                    "confidence": res.get("confidence", 0.0),
                    "max_confidence": res.get("max_confidence", 0.0),
                    "recommended_action": res.get("recommended_action", "none"),
                    "frames_analyzed": res.get("frames_analyzed", 1),  # Temporal Consensus
                    "frames_with_violation": res.get("frames_with_violation", 0),
                    "llm_raw_response": str(res)
                }
                await db_conn.create("gdpr_verification", v_record)
            
            # Update video status to WAITING_FOR_REVIEW
            await db_conn.merge(db_video_id, {
                "status": "waiting_for_review",
                "analysis_completed_at": str(asyncio.get_event_loop().time())
            })

            # Notify Analysis Complete
            await progress_manager.change_phase(
                video_id, 
                ProcessingPhase.WAITING_FOR_REVIEW, 
                f"Analysis complete. Found {total_violations} potential violations. Waiting for review."
            )
            
        except Exception as e:
            logger.error(f"Pipeline error for {video_id}: {e}", exc_info=True)
            await progress_manager.error(video_id, "PROCESSING_ERROR", str(e))
            if db_conn:
                try:
                    db_video_id = video_id if video_id.startswith("video:") else f"video:{video_id}"
                    await db_conn.merge(db_video_id, {"status": "error", "error_message": str(e)})
                except: pass

    async def apply_anonymization(self, video_id: str, decisions: List[Any], user_id: str = "unknown"):
        """
        Runs Phase 2: Anonymization.
        Triggered after user reviews violations.
        decisions: List of decision objects (from UserDecisionBatch).
                   Each has 'verification_id' and 'action'.
        """
        db_conn = None
        try:
            logger.info(f"Starting anonymization for {video_id} (User: {user_id})")
            db_conn = await _db_instance.getting_db("test")
            db_video_id = video_id if video_id.startswith("video:") else f"video:{video_id}"

            # 1. Fetch Video Info
            videos = await db_conn.select(db_video_id)
            if not videos: raise ValueError("Video not found")
            video_info = videos[0] if isinstance(videos, list) else videos
            
            input_path = video_info.get("original_path")
            if not input_path or not os.path.exists(input_path):
                raise ValueError(f"Original video file missing: {input_path}")

            await progress_manager.change_phase(video_id, ProcessingPhase.ANONYMIZING, "Preparing anonymization...")

            actions = []
            
            # Map decisions to dict for easy lookup if needed, but we can just iterate.
            # We need to get the linked detection for each verification decision.
            
            for decision in decisions:
                # Decision object might be pydantic model or dict depending on how it's passed
                if hasattr(decision, 'verification_id'):
                    ver_id = decision.verification_id
                    action_type = decision.action
                else:
                    ver_id = decision.get('verification_id')
                    action_type = decision.get('action')
                
                if not ver_id or action_type == 'no_modify':
                    continue
                
                # Fetch verification record to get detection link
                # verification record ID format: "gdpr_verification:..."
                # If ver_id comes from frontend without prefix, might need adjustment, but usually we send full ID.
                try:
                    # Fetch verification record
                    ver_rec = await db_conn.select(ver_id)
                    if not ver_rec: continue
                    ver_rec = ver_rec[0] if isinstance(ver_rec, list) else ver_rec
                    
                    # Get detection link
                    det_id = ver_rec.get('detection')
                    if not det_id: continue
                    
                    # Fetch detection record
                    det_rec = await db_conn.select(det_id)
                    if not det_rec: continue
                    det_rec = det_rec[0] if isinstance(det_rec, list) else det_rec
                    
                    # Reconstruct bbox history
                    hist = det_rec.get("bbox_history", [])
                    bboxes_map = {
                        int(item['frame']): [
                            int(item['x1']), int(item['y1']), int(item['x2']), int(item['y2'])
                        ] 
                        for item in hist
                    }
                    
                    # Reconstruct masks map
                    masks_map = {
                        int(item['frame']): item['mask']
                        for item in hist
                        if item.get('mask') is not None
                    }
                    
                    actions.append({
                        "type": action_type,
                        "track_id": det_rec.get("track_id"),
                        "type": action_type,
                        "track_id": det_rec.get("track_id"),
                        "bboxes": bboxes_map,
                        "masks": masks_map,
                        "config": {"kernel_size": 31} # Default config
                    })
                    
                except Exception as ex:
                    logger.warning(f"Error processing decision for {ver_id}: {ex}")
                    continue

            # 3. Running Anonymizer
            output_path = Path("storage/processed") / f"anonymized_{Path(input_path).name}"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if not actions:
                logger.info("No anonymization actions requested. Still processing to clear metadata and add watermark.")
                # We still run it to strip metadata and add watermark as requested
            
            await self.anonymizer.apply_anonymization(
                video_id=video_id,
                input_path=input_path,
                output_path=str(output_path),
                actions=actions,
                user_id=user_id
            )
            
            # 4. Update status
            await db_conn.merge(db_video_id, {
                "status": "completed",
                "processed_path": str(output_path),
                "completed_at": str(asyncio.get_event_loop().time())
            })
            
            await progress_manager.complete(
                video_id,
                total_vulnerabilities=len(decisions), # Approx
                total_violations=len(actions)
            )
            
        except Exception as e:
            logger.error(f"Anonymization error {video_id}: {e}", exc_info=True)
            await progress_manager.error(video_id, "EDITION_ERROR", str(e))
            if db_conn:
                try:
                    db_video_id = video_id if video_id.startswith("video:") else f"video:{video_id}"
                    await db_conn.merge(db_video_id, {"status": "error", "error_message": str(e)})
                except: pass

# Singleton instance
video_processor = VideoProcessor()
