import sys
import os
import asyncio
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable
import cv2
import numpy as np
import torch
from ultralytics import YOLO

try:
    import kornia
    import kornia.filters
    from kornia.contrib import FaceDetector, FaceDetectorResult
    KORNIA_FACE_AVAILABLE = True
except ImportError:
    KORNIA_FACE_AVAILABLE = False
    
from .models import BoundingBox, Capture, TrackedDetection, DetectionResult
from .tracker import ObjectTracker
from .capture_manager import CaptureManager
from .gpu_manager import gpu_manager
from services.progress_manager import progress_manager, ProcessingPhase

logger = logging.getLogger('detection_module')

MIN_DETECTION_AREA = 500

class HybridDetectorManager:
    """
    Gestor híbrido de detectores: Kornia AI (caras) + YOLO (personas, matrículas).
    """
    
    YOLO_CONFIGS = {
        "nano": {"person": "yolo11n-seg.pt", "plate": "yolov8n.pt"},
        "small": {"person": "yolo11s-seg.pt", "plate": "yolov8s.pt"},
        "medium": {"person": "yolo11m-seg.pt", "plate": "yolov8m.pt"},
    }
    
    def __init__(
        self, 
        gpu_mgr = None,
        person_model: str = None,
        plate_model: str = None,
        face_confidence: float = 0.5,
        person_confidence: float = 0.5
    ):
        self.gpu = gpu_mgr or gpu_manager
        self.device = self.gpu.device
        self.strategy, self.model_size, self.batch_size = self.gpu.get_strategy()
        
        self.face_confidence = face_confidence
        self.person_confidence = person_confidence
        
        self._init_face_detector()
        self._init_yolo_detectors(person_model, plate_model)
        
        logger.info(f"HybridDetectorManager: strategy={self.strategy}, size={self.model_size}, "
                   f"device={self.device}, kornia_face={KORNIA_FACE_AVAILABLE}")
    
    def _init_face_detector(self):
        self.face_detector = None
        
        if KORNIA_FACE_AVAILABLE:
            try:
                self.face_detector = FaceDetector().to(self.device)
                logger.info("✓ Kornia FaceDetector (YuNet) loaded")
            except Exception as e:
                logger.warning(f"Could not load Kornia FaceDetector: {e}")
                self.face_detector = None
        
        if self.face_detector is None:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            logger.info("Using OpenCV Haar Cascade fallback for face detection")
    
    def _init_yolo_detectors(self, person_model: str, plate_model: str):
        config = self.YOLO_CONFIGS[self.model_size]
        
        person_path = person_model or config["person"]
        try:
            self.person_detector = YOLO(person_path)
            logger.info(f"✓ YOLO person detector loaded: {person_path}")
        except Exception as e:
            logger.error(f"Failed to load person model: {e}")
            self.person_detector = None
        
        self.plate_detector = None
        # Only load plate detector if a model is explicitly provided or we have a default path that exists
        # For now, let's assume we might use standard yolov8n.pt if not specified, but usually plate detection needs specialized model.
        if plate_model:
             try:
                self.plate_detector = YOLO(plate_model)
                logger.info(f"✓ YOLO plate detector loaded: {plate_model}")
             except Exception as e:
                logger.warning(f"Could not load plate model: {e}")
        elif config["plate"]: # Try loading default generic model simply to avoid error, though it won't detect plates well without fine-tuning
            try:
                # self.plate_detector = YOLO(config["plate"]) 
                # Actually, standard YOLO models don't detect plates well. User notebook had "license_plate_detector.pt".
                # We skip unless provided to avoid waste.
                pass
            except: pass
    
    def _numpy_to_tensor(self, frame: np.ndarray) -> torch.Tensor:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0).float() / 255.0
        return tensor.to(self.device)
    
    def detect_faces_kornia(self, tensor: torch.Tensor, frame_num: int) -> List[Tuple[str, BoundingBox]]:
        if self.face_detector is None:
            return []

        results = []
        with torch.no_grad():
            detections = self.face_detector(tensor)

        for det in detections:
            try:
                face_result = FaceDetectorResult(det)
                if face_result.score.numel() == 0:
                    continue

                top_left = face_result.top_left.int().tolist()
                bottom_right = face_result.bottom_right.int().tolist()
                scores = face_result.score.tolist()

                for score, tl, br in zip(scores, top_left, bottom_right):
                    if score >= self.face_confidence:
                        x1, y1 = float(tl[0]), float(tl[1])
                        x2, y2 = float(br[0]), float(br[1])
                        bbox = BoundingBox(x1, y1, x2, y2, float(score), frame_num)
                        if bbox.area >= MIN_DETECTION_AREA:
                            results.append(("face", bbox))
            except Exception as e:
                logger.debug(f"Error processing face detection: {e}")
        return results
    
    def detect_faces_opencv(self, frame: np.ndarray, frame_num: int) -> List[Tuple[str, BoundingBox]]:
        if not hasattr(self, 'face_cascade'):
            return []
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        results = []
        for (x, y, w, h) in faces:
            bbox = BoundingBox(float(x), float(y), float(x + w), float(y + h), 0.8, frame_num)
            if bbox.area >= MIN_DETECTION_AREA:
                results.append(("face", bbox))
        return results
    
    def detect_persons(self, frame: np.ndarray, frame_num: int) -> List[Tuple[str, BoundingBox]]:
        if self.person_detector is None:
            return []
        
        # Class 0 is 'person' in COCO
        results_yolo = self.person_detector.predict(frame, conf=self.person_confidence, verbose=False, device=self.device, classes=[0], retina_masks=True)
        
        results = []
        for r in results_yolo:
            masks_xy = r.masks.xy if r.masks is not None else []
            
            for i, box in enumerate(r.boxes):
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                
                mask_points = None
                if i < len(masks_xy):
                    # Flatten the polygon points [x1, y1, x2, y2, ...]
                    mask_points = masks_xy[i].flatten().tolist()
                
                bbox = BoundingBox(x1, y1, x2, y2, float(box.conf[0]), frame_num, mask=mask_points)
                if bbox.area >= MIN_DETECTION_AREA:
                    results.append(("person", bbox))
        return results
    
    def detect_plates(self, frame: np.ndarray, frame_num: int) -> List[Tuple[str, BoundingBox]]:
        if self.plate_detector is None:
            return []
        
        results_yolo = self.plate_detector.predict(frame, conf=self.person_confidence, verbose=False, device=self.device)
        
        results = []
        for r in results_yolo:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                bbox = BoundingBox(x1, y1, x2, y2, float(box.conf[0]), frame_num)
                if bbox.area >= MIN_DETECTION_AREA:
                    results.append(("license_plate", bbox))
        return results
    
    async def detect_all(self, frames: List[np.ndarray], frame_nums: List[int], conf_threshold: float = 0.5) -> Dict[int, List[Tuple[str, BoundingBox]]]:
        """
        Optimizado para GPU: procesa múltiples frames en batch y ejecuta detectores en paralelo.
        """
        import asyncio
        import time
        
        all_detections = {fn: [] for fn in frame_nums}
        start_time = time.time()
        
        # === BATCHED PERSON DETECTION (YOLO procesa múltiples frames a la vez) ===
        total_persons = 0
        if self.person_detector is not None:
            # YOLO puede procesar un batch completo de frames
            results_batch = self.person_detector.predict(
                frames,
                conf=self.person_confidence,
                verbose=False,
                device=self.device,
                classes=[0],  # person class
                retina_masks=True,
                batch=len(frames)  # Batch size
            )
            
            for frame_idx, r in enumerate(results_batch):
                frame_num = frame_nums[frame_idx]
                masks_xy = r.masks.xy if r.masks is not None else []
                
                for i, box in enumerate(r.boxes):
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    mask_points = None
                    if i < len(masks_xy):
                        mask_points = masks_xy[i].flatten().tolist()
                    
                    bbox = BoundingBox(x1, y1, x2, y2, float(box.conf[0]), frame_num, mask=mask_points)
                    if bbox.area >= MIN_DETECTION_AREA:
                        all_detections[frame_num].append(("person", bbox))
                        total_persons += 1
        
        # === PARALLEL FACE DETECTION ===
        total_faces = 0
        if self.face_detector is not None:
            # Convertir todos los frames a tensores y concatenar para batch
            tensors = [self._numpy_to_tensor(f) for f in frames]
            batch_tensor = torch.cat(tensors, dim=0)
            
            with torch.no_grad():
                detections = self.face_detector(batch_tensor)
            
            for frame_idx, det in enumerate(detections):
                frame_num = frame_nums[frame_idx]
                try:
                    face_result = FaceDetectorResult(det)
                    if face_result.score.numel() == 0:
                        continue
                    
                    top_left = face_result.top_left.int().tolist()
                    bottom_right = face_result.bottom_right.int().tolist()
                    scores = face_result.score.tolist()
                    
                    for score, tl, br in zip(scores, top_left, bottom_right):
                        if score >= self.face_confidence:
                            bbox = BoundingBox(float(tl[0]), float(tl[1]), float(br[0]), float(br[1]), float(score), frame_num)
                            if bbox.area >= MIN_DETECTION_AREA:
                                all_detections[frame_num].append(("face", bbox))
                                total_faces += 1
                except Exception:
                    pass
        else:
            # Fallback to OpenCV (sequential)
            for frame, frame_num in zip(frames, frame_nums):
                faces = self.detect_faces_opencv(frame, frame_num)
                all_detections[frame_num].extend(faces)
                total_faces += len(faces)
        
        # === PLATE DETECTION ===
        total_plates = 0
        if self.plate_detector is not None:
            results_batch = self.plate_detector.predict(
                frames, conf=self.person_confidence, verbose=False, device=self.device, batch=len(frames)
            )
            for frame_idx, r in enumerate(results_batch):
                frame_num = frame_nums[frame_idx]
                for box in r.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    bbox = BoundingBox(x1, y1, x2, y2, float(box.conf[0]), frame_num)
                    if bbox.area >= MIN_DETECTION_AREA:
                        all_detections[frame_num].append(("license_plate", bbox))
                        total_plates += 1
        
        elapsed = time.time() - start_time
        if total_persons > 0 or total_faces > 0 or total_plates > 0:
            fps = len(frames) / elapsed if elapsed > 0 else 0
            print(f"   [DETECTOR] Batch {len(frames)} frames in {elapsed:.2f}s ({fps:.1f} FPS): {total_persons} persons, {total_faces} faces, {total_plates} plates")
        
        return all_detections
    
    def get_info(self) -> Dict:
        detectors = []
        if self.person_detector: detectors.append("person (YOLOv10)")
        if self.face_detector: detectors.append("face (Kornia YuNet)")
        elif hasattr(self, 'face_cascade'): detectors.append("face (OpenCV Haar)")
        if self.plate_detector: detectors.append("plate (YOLO)")
        
        return {
            "strategy": self.strategy,
            "model_size": self.model_size,
            "batch_size": self.batch_size,
            "device": self.device,
            "vram_total_mb": self.gpu.vram_total_mb,
            "detectors": detectors,
            "kornia_available": KORNIA_FACE_AVAILABLE
        }


class VideoDetector:
    def __init__(
        self,
        item=None, # For compatibility if needed, but we ignore it
        hybrid_manager: HybridDetectorManager = None,
        person_model: str = None,
        plate_model: str = None,
        confidence_threshold: float = 0.5
    ):
        self.conf_threshold = confidence_threshold
        
        if hybrid_manager:
            self.hybrid_manager = hybrid_manager
        else:
            self.hybrid_manager = HybridDetectorManager(
                person_model=person_model,
                plate_model=plate_model,
                face_confidence=confidence_threshold,
                person_confidence=confidence_threshold
            )
            
        self.batch_size = self.hybrid_manager.batch_size
        logger.info(f"VideoDetector initialized: {self.hybrid_manager.get_info()}")

    async def process_video(
        self,
        video_id: str,
        video_path: str,
        output_dir: str
    ) -> DetectionResult:

        start_time = time.time()
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        cap = None
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Could not open video: {video_path}")

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            tracker = ObjectTracker()
            cm = CaptureManager()
            tracked_objects = {}
            frame_num = 0

            frame_buffer = []
            frame_nums = []

            logger.info(f"Processing video {video_id}: {total_frames} frames at {fps} FPS")

            # Notify start
            await progress_manager.change_phase(
                video_id, ProcessingPhase.DETECTING, "Iniciando detección de objetos..."
            )

            while True:
                ret, frame = cap.read()
                if not ret:
                    if frame_buffer:
                        await self._process_batch(
                            video_id, frame_buffer, frame_nums, tracker, cm,
                            tracked_objects, output_path, fps, total_frames
                        )
                    break

                frame_num += 1
                frame_buffer.append(frame)
                frame_nums.append(frame_num)

                if len(frame_buffer) >= self.batch_size:
                    await self._process_batch(
                        video_id, frame_buffer, frame_nums, tracker, cm,
                        tracked_objects, output_path, fps, total_frames
                    )
                    frame_buffer = []
                    frame_nums = []

            processing_time = time.time() - start_time

            # Notify completion of detection phase
            await progress_manager.update_progress(
                video_id, 100, total_frames, total_frames, "Detección completada"
            )

            # Summary log
            print(f"\n📊 [DETECTION SUMMARY]")
            print(f"   Total frames processed: {frame_num}")
            print(f"   Total unique tracks: {len(tracked_objects)}")
            for tid, track in tracked_objects.items():
                print(f"      Track {tid}: {track.detection_type}, frames {track.first_frame}-{track.last_frame}, {len(track.captures)} captures")
            print(f"   Processing time: {processing_time:.2f}s ({total_frames/processing_time:.1f} FPS)")

            return DetectionResult(
                video_path=video_path,
                total_frames=total_frames,
                fps=fps,
                duration_seconds=total_frames/fps if fps > 0 else 0,
                width=width,
                height=height,
                detections=list(tracked_objects.values()),
                frames_processed=frame_num,
                processing_time_seconds=processing_time
            )

        except Exception as e:
            logger.error(f"Detection failed for video {video_id}: {e}", exc_info=True)
            # Clean up captured files on error
            try:
                if output_path.exists():
                    import shutil
                    shutil.rmtree(output_path)
                    logger.info(f"Cleaned up capture directory: {output_path}")
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup captures: {cleanup_error}")
            raise

        finally:
            # Always release video capture
            if cap is not None:
                cap.release()
                logger.debug(f"Released video capture for {video_id}")

            # Phase 2.4: Release GPU memory explicitly (CRITICAL for NVIDIA DGX Spark)
            if torch.cuda.is_available():
                try:
                    allocated = torch.cuda.memory_allocated() / 1024**3  # GB
                    reserved = torch.cuda.memory_reserved() / 1024**3    # GB
                    logger.info(f"GPU memory before cleanup: allocated={allocated:.2f}GB, reserved={reserved:.2f}GB")

                    # Clear GPU cache
                    torch.cuda.empty_cache()

                    # Synchronize to ensure all GPU operations finished
                    torch.cuda.synchronize()

                    allocated_after = torch.cuda.memory_allocated() / 1024**3
                    reserved_after = torch.cuda.memory_reserved() / 1024**3
                    logger.info(f"GPU memory after cleanup: allocated={allocated_after:.2f}GB, reserved={reserved_after:.2f}GB")
                    logger.info(f"GPU memory freed: {(reserved - reserved_after):.2f}GB")
                except Exception as gpu_cleanup_error:
                    logger.error(f"Failed to cleanup GPU memory: {gpu_cleanup_error}")

    async def _process_batch(
        self, 
        video_id: str,
        frames: List[np.ndarray], 
        frame_nums: List[int], 
        tracker: ObjectTracker, 
        cm: CaptureManager,
        tracked_objects: Dict[int, TrackedDetection], 
        output_path: Path, 
        fps: float,
        total_frames: int
    ):
        all_detections_by_frame = await self.hybrid_manager.detect_all(
            frames, 
            frame_nums, 
            conf_threshold=self.conf_threshold
        )
        
        last_frame_num = frame_nums[-1]
        
        for frame, frame_num in zip(frames, frame_nums):
            current_detections = all_detections_by_frame[frame_num]
            
            # Report individual detections via SSE just for visualization/fun? 
            # Or usually we report counts. Reporting every bbox is too much traffic usually.
            # But the notebook reported 'DetectionEvent'.
            # Let's verify existing progress_manager has 'report_detection'.
            # Yes it has.
            
            confirmed = tracker.update(current_detections, frame_num)
            
            for tid, label, bbox in confirmed:
                if tid not in tracked_objects:
                    tracked_objects[tid] = TrackedDetection(tid, label)
                    
                tracked_objects[tid].add_bbox(bbox)
                
                # Check for capture
                cap_result = cm.consider_frame(
                    tid, frame, frame_num, bbox, output_path, fps, 
                    capture_interval=1.0, detection_type=label
                )
                
                if cap_result:
                    path_clean, path_bbox = cap_result
                    tracked_objects[tid].captures.append(Capture(
                        frame=frame_num, 
                        image_path=path_clean, 
                        bbox=bbox, 
                        reason="periodic", 
                        timestamp=frame_num/fps
                    ))
                    
                    # Report interesting detection event via SSE
                    # Maybe we report every capture as a "Detection" to the user?
                    # Or report every new track?
                    # Let's report periodically or on capture.
                    await progress_manager.report_detection(
                        video_id, label, frame_num, bbox.confidence
                    )
            
        # Update progress for the batch
        percent = int((last_frame_num / total_frames) * 100)
        await progress_manager.update_progress(
            video_id, percent, last_frame_num, total_frames, 
            f"Detectando objetos ({last_frame_num}/{total_frames})"
        )
        
        await asyncio.sleep(0)
