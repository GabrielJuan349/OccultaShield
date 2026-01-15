import asyncio
import os
import logging
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import json
import surrealdb as sr

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
        
    async def process_full_pipeline(self, video_id: str, input_path: str, timeout_seconds: int = 3600):
        """
        Runs Phase 1: Detection and Verification.
        Saves results to DB sets status to 'WAITING_FOR_REVIEW'.

        Args:
            video_id: Unique video identifier
            input_path: Path to the video file
            timeout_seconds: Maximum processing time (default: 1 hour)
        """
        db_conn = None
        try:
            print(f"\n{'='*60}")
            print(f"🎬 [PIPELINE START] Video: {video_id}")
            print(f"   Input: {input_path}")
            print(f"   Timeout: {timeout_seconds}s")
            print(f"{'='*60}")

            logger.info(f"Starting pipeline for {video_id}")
            db_conn = await _db_instance.getting_db()  # Uses default from .env

            # --- 0. INIT ---
            await progress_manager.register_video(video_id)
            await progress_manager.change_phase(video_id, ProcessingPhase.DETECTING, "Starting detection analysis...")
            
            # --- 1. DETECTION PHASE ---
            output_dir = Path("storage/captures") / video_id
            output_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"\n🔍 [PHASE 1: DETECTION] Starting...")
            print(f"   Output directory: {output_dir}")
            
            detection_result = await self.detector.process_video(
                video_id=video_id,
                video_path=input_path, 
                output_dir=str(output_dir)
            )
            
            print(f"✅ [DETECTION COMPLETE] Found {len(detection_result.detections)} detections")
            
            # Save Detections to DB
            saved_detections_map = {} # track_id -> db_record_id

            # Create proper RecordID for video (SurrealDB requires record<video> type)
            clean_video_id = video_id.replace("video:", "") if video_id.startswith("video:") else video_id
            db_video_record = sr.RecordID("video", clean_video_id)  # For creating detection records (record<video>)
            db_video_id = f"video:{clean_video_id}"  # String format for merge operations

            for track in detection_result.detections:
                 # Calculate duration in seconds based on frame range (assuming 30fps)
                 fps = 30.0  # Default FPS
                 duration_seconds = (track.last_frame - track.first_frame) / fps if track.last_frame > track.first_frame else 0.0

                 d_record = {
                     "video_id": db_video_record,  # Must be RecordID, not string
                     "track_id": track.track_id,
                     "detection_type": track.detection_type,
                     "first_frame": track.first_frame,
                     "last_frame": track.last_frame,
                     "avg_confidence": track.avg_confidence,
                     "max_confidence": track.avg_confidence,  # Use avg as max for now
                     "duration_seconds": duration_seconds,  # Required by DB schema
                     "storage_path": "",  # Required by DB schema - empty for now
                     # Store full history for later edition
                     "bbox_history": [b.to_dict() for b in track.bbox_history],
                     "captures": [c.to_dict() for c in track.captures],
                 }
                 
                 # Create detection record with error handling
                 try:
                     created = await db_conn.create("detection", d_record)
                     if created:
                         # Surreal returns list of created records, take first
                         rec = created[0] if isinstance(created, list) else created
                         # rec can be a dict with 'id' key or a string ID directly
                         if isinstance(rec, dict):
                             rec_id = rec.get('id', rec.get('ID', str(rec)))
                         else:
                             rec_id = str(rec)
                         saved_detections_map[track.track_id] = rec_id
                     else:
                         # Handle case when DB creation returns falsy value
                         rec_id = f"fallback_{track.track_id}"
                         logger.error(f"Failed to create detection for track {track.track_id} - create returned: {created}")
                         print(f"      ❌ Track {track.track_id} FAILED - create returned: {created}")
                         saved_detections_map[track.track_id] = rec_id
                 except Exception as db_error:
                     logger.error(f"DB exception saving track {track.track_id}: {db_error}")
                     print(f"      ❌ Track {track.track_id} DB EXCEPTION: {db_error}")
                     saved_detections_map[track.track_id] = f"error_{track.track_id}"
            print(f"   Saved {len(saved_detections_map)} detections to DB")

            # --- 2. VERIFICATION PHASE (Temporal Consensus Mode) ---
            print(f"\n🔎 [PHASE 2: VERIFICATION] Starting GDPR compliance check...")
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
            print(f"✅ [VERIFICATION] Processed {len(v_results)} results")
            
            total_violations = 0
            for res in v_results:
                # detection_id here is the DB ID we passed - could be RecordID or string
                det_db_id = res.get("detection_id")
                is_violation = res.get("is_violation", False)
                if is_violation: total_violations += 1

                # Convert detection_id to proper RecordID if it's a string
                if isinstance(det_db_id, str):
                    # Parse "detection:xyz" format
                    if ":" in str(det_db_id):
                        table, record_id = str(det_db_id).split(":", 1)
                        # Handle RecordID format like "detection:xyz" or "RecordID(table_name=detection, record_id=xyz)"
                        if "RecordID" in table:
                            # It's already been stringified from a RecordID, extract parts
                            import re
                            match = re.search(r"table_name=(\w+), record_id=([^)]+)", str(det_db_id))
                            if match:
                                table = match.group(1)
                                record_id = match.group(2).strip("'\"")
                        det_record_id = sr.RecordID(table, record_id)
                    else:
                        det_record_id = sr.RecordID("detection", str(det_db_id))
                elif isinstance(det_db_id, sr.RecordID):
                    det_record_id = det_db_id
                else:
                    # Fallback - try to create a RecordID
                    det_record_id = sr.RecordID("detection", str(det_db_id))

                v_record = {
                    "detection_id": det_record_id,  # Must be RecordID for record<detection> type
                    "capture_index": 0,  # Required by schema
                    "is_violation": is_violation,
                    "severity": res.get("severity", "none"),
                    "description": res.get("reasoning", ""),
                    "violated_articles": res.get("violated_articles", []),
                    "detected_personal_data": [],  # Required by schema
                    "legal_basis_required": "",  # Required by schema
                    "confidence": res.get("confidence", 0.0),
                    "processing_time_ms": 0,  # Required by schema
                    "llm_model": "gemma-3-4b",
                    "recommended_action": res.get("recommended_action", "none"),
                    "llm_raw_response": str(res)
                }
                try:
                    await db_conn.create("gdpr_verification", v_record)
                except Exception as verif_error:
                    logger.error(f"Error saving verification for {det_db_id}: {verif_error}")
            
            # Update video status to VERIFIED (mapped from waiting_for_review for DB schema)
            await db_conn.merge(db_video_id, {
                "status": "verified",  # Schema allows: pending, processing, detected, verified, editing, completed, error
                "analysis_completed_at": str(asyncio.get_event_loop().time())
            })

            print(f"\n📊 [RESULTS]")
            print(f"   Total detections: {len(detection_result.detections)}")
            print(f"   Total violations: {total_violations}")

            # Check if there are any DETECTIONS (not just violations)
            # We want human review whenever there are detections, even if AI says no violation
            if len(detection_result.detections) == 0:
                # No detections at all - safe to skip review (only metadata stripping needed)
                print(f"   ℹ️  No detections found - skipping review and going directly to metadata stripping.")
                await db_conn.merge(db_video_id, {"status": "editing"})

                # --- 3. ANONYMIZATION (metadata stripping only) ---
                await progress_manager.change_phase(video_id, ProcessingPhase.ANONYMIZING, "Applying metadata stripping...")
                await self.apply_anonymization(video_id, [], "system")
                print(f"\n✅ [PIPELINE COMPLETE] Video: {video_id}")
                print(f"   Status: COMPLETED (no detections)")
                print(f"{'='*60}\n")
                return

            # There are detections - ALWAYS require human review
            # Even if AI says no violations, human must confirm
            review_message = (
                f"Analysis complete. Found {len(detection_result.detections)} detections"
                f" ({total_violations} potential violations). Waiting for human review."
            )
            print(f"   📋 {review_message}")

            # Notify Analysis Complete - detections found, waiting for human review
            await progress_manager.change_phase(
                video_id,
                ProcessingPhase.WAITING_FOR_REVIEW,
                review_message
            )

            # Send additional progress update to ensure frontend receives the message
            await progress_manager.update_progress(
                video_id,
                progress=100,
                message=review_message
            )

            print(f"\n✅ [PIPELINE COMPLETE] Video: {video_id}")
            print(f"   Status: WAITING_FOR_REVIEW")
            print(f"   Total detections: {len(detection_result.detections)}")
            print(f"   Total violations: {total_violations}")
            print(f"{'='*60}\n")

        except asyncio.TimeoutError:
            print(f"\n⏱️  [PIPELINE TIMEOUT] Video: {video_id}")
            print(f"   Processing exceeded {timeout_seconds}s limit")
            print(f"{'='*60}\n")
            logger.error(f"Pipeline timeout for {video_id} after {timeout_seconds}s")
            await progress_manager.error(video_id, "TIMEOUT_ERROR", f"Processing timeout after {timeout_seconds}s")
            if db_conn:
                try:
                    db_video_id = video_id if video_id.startswith("video:") else f"video:{video_id}"
                    await db_conn.merge(db_video_id, {
                        "status": "error",
                        "error_message": f"Processing timeout after {timeout_seconds}s"
                    })
                except Exception as merge_error:
                    logger.error(f"Failed to update timeout status in DB: {merge_error}")

        except Exception as e:
            print(f"\n❌ [PIPELINE ERROR] Video: {video_id}")
            print(f"   Error: {str(e)}")
            print(f"{'='*60}\n")
            logger.error(f"Pipeline error for {video_id}: {e}", exc_info=True)
            await progress_manager.error(video_id, "PROCESSING_ERROR", str(e))
            if db_conn:
                try:
                    db_video_id = video_id if video_id.startswith("video:") else f"video:{video_id}"
                    await db_conn.merge(db_video_id, {"status": "error", "error_message": str(e)})
                except Exception as merge_error:
                    logger.error(f"Failed to update error status in DB: {merge_error}")
        finally:
            # NOTE: Do NOT close the shared connection - it's used by other endpoints
            # The connection is managed by _db_instance singleton
            pass

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
            print(f"\n{'='*60}")
            print(f"🎨 [ANONYMIZATION START] Video: {video_id}")
            print(f"   User: {user_id}")
            print(f"   Decisions: {len(decisions)}")
            print(f"{'='*60}")
            
            db_conn = await _db_instance.getting_db()  # Uses default from .env
            db_video_id = video_id if video_id.startswith("video:") else f"video:{video_id}"

            # Ensure video is registered in progress_manager for SSE events
            state = await progress_manager.get_state(video_id)
            if not state:
                print(f"   📝 Registering video in progress_manager...")
                await progress_manager.register_video(video_id)

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
                # If ver_id comes from frontend without prefix, add it
                try:
                    # Ensure ver_id has table prefix
                    if not str(ver_id).startswith('gdpr_verification:'):
                        ver_id = f"gdpr_verification:{ver_id}"

                    print(f"   📝 Processing decision: ver_id={ver_id}, action={action_type}")

                    # Fetch verification record
                    ver_rec = await db_conn.select(ver_id)
                    if not ver_rec:
                        print(f"   ⚠️ Verification record not found: {ver_id}")
                        continue
                    ver_rec = ver_rec[0] if isinstance(ver_rec, list) else ver_rec

                    # Get detection link (field is 'detection_id', not 'detection')
                    det_id = ver_rec.get('detection_id')
                    if not det_id:
                        print(f"   ⚠️ No detection_id in verification: {ver_rec.keys()}")
                        continue
                    
                    # Fetch detection record - det_id might be RecordID object
                    det_id_str = str(det_id)
                    print(f"   📝 Fetching detection: {det_id_str}")
                    det_rec = await db_conn.select(det_id_str)
                    if not det_rec:
                        print(f"   ⚠️ Detection record not found: {det_id_str}")
                        continue
                    det_rec = det_rec[0] if isinstance(det_rec, list) else det_rec
                    print(f"   ✅ Found detection: track_id={det_rec.get('track_id')}")

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
                        "bboxes": bboxes_map,
                        "masks": masks_map,
                        "config": {"kernel_size": 31} # Default config
                    })
                    print(f"   ✅ Added action: type={action_type}, track_id={det_rec.get('track_id')}, frames={len(bboxes_map)}")

                except Exception as ex:
                    logger.warning(f"Error processing decision for {ver_id}: {ex}")
                    print(f"   ❌ Error processing decision: {ex}")
                    continue

            print(f"\n   📊 Total actions to apply: {len(actions)}")
            for i, act in enumerate(actions):
                print(f"      [{i+1}] {act['type']} on track {act['track_id']} ({len(act['bboxes'])} frames)")

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
                total_vulnerabilities=len(decisions),
                total_violations=len(actions),
                redirect_url=f"/download/{video_id}"
            )
            
        except Exception as e:
            logger.error(f"Anonymization error {video_id}: {e}", exc_info=True)
            await progress_manager.error(video_id, "EDITION_ERROR", str(e))
            if db_conn:
                try:
                    db_video_id = video_id if video_id.startswith("video:") else f"video:{video_id}"
                    await db_conn.merge(db_video_id, {"status": "error", "error_message": str(e)})
                except Exception as merge_error:
                    logger.error(f"Failed to update error status in DB: {merge_error}")
        finally:
            # NOTE: Do NOT close the shared connection - it's used by other endpoints
            # The connection is managed by _db_instance singleton
            pass

# Singleton instance
video_processor = VideoProcessor()
