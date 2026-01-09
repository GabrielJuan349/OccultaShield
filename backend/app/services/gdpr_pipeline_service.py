import asyncio
import logging
from typing import List, Dict, Any
from pathlib import Path

from ..modules.detection.detector import VideoDetector
from ..modules.verification.parallel_processor import ParallelProcessor
from ..modules.edition.video_editor import VideoAnonymizer
from services.progress_manager import progress_manager, ProcessingPhase

logger = logging.getLogger(__name__)

class GDPRPipelineService:
    
    def __init__(self):
        # Initialize modules
        # We could inject configs here
        self.detector = VideoDetector()
        self.verifier = ParallelProcessor(max_workers=4)
        self.editor = VideoAnonymizer(use_gpu=True)
        
    async def process_video(
        self,
        video_id: str,
        video_path: str,
        output_dir: str,
        user_id: str = "default_user"
    ):
        """Procesa video con reporting de progreso via SSE.
           - Detección
           - Verificación (GDPR)
           - Anonimización
        """
        
        # Registrar video para tracking
        await progress_manager.register_video(video_id)
        
        try:
            # ===== FASE 1: DETECCIÓN =====
            # VideoDetector ya notifica progreso detallado
            detection_result = await self.detector.process_video(
                video_id=video_id,
                video_path=video_path,
                output_dir=output_dir 
            )
            
            # ===== FASE 2: PREPARACIÓN DE VERIFICACIÓN =====
            await progress_manager.change_phase(
                video_id, ProcessingPhase.VERIFYING, "Preparing tracks for verification..."
            )
            
            verification_requests = []
            tracks_map = {} # id -> track
            
            for track in detection_result.detections:
                tracks_map[track.track_id] = track
                capture = track.best_capture
                if capture:
                    verification_requests.append({
                        "image_path": capture.image_path,
                        "detection": {
                            "id": track.track_id, 
                            "detection_type": track.detection_type,
                            "bbox": capture.bbox.to_dict()
                        }
                    })
            
            # ===== FASE 3: VERIFICACIÓN =====
            await progress_manager.change_phase(
                video_id, ProcessingPhase.VERIFYING, 
                f"Analizando {len(verification_requests)} elementos para conformidad GDPR..."
            )
            
            verification_results = await self.verifier.process_requests(
                video_id, verification_requests
            )
            
            # ===== FASE 4: PLANIFICACIÓN DE ANONIMIZACIÓN (ACCIONES) =====
            actions = []
            violations_count = 0
            
            for res in verification_results:
                track_id = res.get("detection_id")
                is_violation = res.get("is_violation", False)
                action_type = res.get("recommended_action", "blur")
                
                if is_violation and track_id in tracks_map:
                    violations_count += 1
                    track = tracks_map[track_id]
                    
                    # Convert bbox history to format expected by Editor
                    bboxes_map = {
                        b.frame: b.to_int_tuple() 
                        for b in track.bbox_history
                    }
                    
                    actions.append({
                        "type": action_type,
                        "track_id": track_id,
                        "bboxes": bboxes_map,
                        "config": {"kernel_size": 31} # Default config
                    })
            
            # ===== FASE 5: ANONIMIZACIÓN =====
            # Editor ya notifica progreso
            anonymized_path = str(Path(output_dir) / f"anonymized_{Path(video_path).name}")
            
            await self.editor.apply_anonymization(
                video_id=video_id,
                input_path=video_path,
                output_path=anonymized_path,
                actions=actions
            )
            
            # ===== COMPLETADO =====
            await progress_manager.complete(
                video_id=video_id,
                total_vulnerabilities=len(detection_result.detections),
                total_violations=violations_count
            )
            
            return {
                "status": "completed",
                "original_video": video_path,
                "anonymized_video": anonymized_path,
                "stats": {
                    "detections": len(detection_result.detections),
                    "violations": violations_count
                }
            }
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            await progress_manager.error(
                video_id=video_id,
                code="PROCESSING_ERROR",
                message=str(e),
                recoverable=False
            )
            raise
The above content shows the entire, complete file contents of the requested file.