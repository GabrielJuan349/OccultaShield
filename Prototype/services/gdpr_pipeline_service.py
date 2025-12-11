from services.progress_manager import progress_manager, ProcessingPhase

class GDPRPipelineService:
    
    async def process_video(
        self,
        video_id: str,
        video_path: str,
        user_id: str
    ):
        """Procesa video con reporting de progreso via SSE."""
        
        # Registrar video para tracking
        await progress_manager.register_video(video_id)
        
        try:
            # ===== FASE 1: DETECCIÓN =====
            await progress_manager.change_phase(
                video_id=video_id,
                phase=ProcessingPhase.DETECTING,
                message="Analyzing video frames for personal data...",
                estimated_time=60
            )
            
            detection_result = await self._run_detection(
                video_path=video_path,
                video_id=video_id,
                on_progress=lambda current, total: progress_manager.update_progress(
                    video_id, 
                    progress=int(current / total * 100),
                    current=current,
                    total=total,
                    message=f"Processing frame {current}/{total}"
                ),
                on_detection=lambda dtype, frame, conf: progress_manager.report_detection(
                    video_id, dtype, frame, conf
                )
            )
            
            # ===== FASE 2: TRACKING =====
            await progress_manager.change_phase(
                video_id=video_id,
                phase=ProcessingPhase.TRACKING,
                message="Grouping detections across frames...",
                estimated_time=10
            )
            
            # ... tracking logic ...
            
            # ===== FASE 3: GUARDANDO =====
            await progress_manager.change_phase(
                video_id=video_id,
                phase=ProcessingPhase.SAVING,
                message="Saving detection data...",
                estimated_time=5
            )
            
            await self._save_to_surrealdb(video_id, user_id, detection_result)
            
            # ===== FASE 4: VERIFICACIÓN =====
            await progress_manager.change_phase(
                video_id=video_id,
                phase=ProcessingPhase.VERIFYING,
                message="AI agents analyzing GDPR compliance...",
                estimated_time=30
            )
            
            verification_result = await self._run_verification(
                video_id=video_id,
                vulnerabilities=detection_result.vulnerabilities,
                on_verification=lambda vuln_id, status, done, total: progress_manager.report_verification(
                    video_id, vuln_id, status, done, total
                )
            )
            
            # ===== COMPLETADO =====
            await progress_manager.complete(
                video_id=video_id,
                total_vulnerabilities=len(detection_result.vulnerabilities),
                total_violations=verification_result.total_violations
            )
            
            return verification_result
            
        except Exception as e:
            await progress_manager.error(
                video_id=video_id,
                code="PROCESSING_ERROR",
                message=str(e),
                recoverable=False
            )
            raise
        
        finally:
            # Cleanup después de un tiempo
            asyncio.create_task(self._delayed_cleanup(video_id, delay=300))
    
    async def _delayed_cleanup(self, video_id: str, delay: int):
        """Limpia estado después de X segundos."""
        await asyncio.sleep(delay)
        await progress_manager.cleanup(video_id)