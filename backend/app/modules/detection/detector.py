import asyncio
import cv2
import torch
import numpy as np
from pathlib import Path
from ultralytics import YOLO
from typing import List, Optional, Callable, Dict
import logging

from .models import BoundingBox, DetectionResult, TrackedDetection
from .tracker import ObjectTracker
from .capture_manager import CaptureManager

logger = logging.getLogger(__name__)

class VideoDetector:
    def __init__(self, model_path: str, confidence_threshold: float = 0.5):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading YOLO model from {model_path} on {self.device}...")
        self.model = YOLO(model_path) 
        self.conf_threshold = confidence_threshold
        
        # Mappings (COCO default usually, but we might want custom)
        # For now, using COCO classes mapping to our types
        # person(0) -> person
        # car(2), truck(7), bus(5), motorcycle(3) -> license_plate (indirectly, we detect vehicles and then plates? Or assume model detects plates)
        # Provided model should be trained for faces/plates ideally.
        # Fallback: using generic COCO for "person".
        self.class_mapping = {
            0: "person",
            # Add others if custom model
        }

    async def process_video(
        self, 
        video_path: str, 
        output_dir: str,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_detection: Optional[Callable[[str, int, float], None]] = None
    ) -> DetectionResult:
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        tracker = ObjectTracker()
        capture_manager = CaptureManager()
        
        tracked_objects: Dict[int, TrackedDetection] = {}
        
        frame_num = 0
        
        # Loop
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_num += 1
            
            # Run detection every N frames? 
            # For simplicity, every frame or skip logic could be added here
            
            # Predict
            results = self.model.predict(frame, conf=self.conf_threshold, verbose=False, device=self.device)
            result = results[0]
            
            current_detections = []
            
            for box in result.boxes:
                cls_id = int(box.cls[0].item())
                if cls_id not in self.class_mapping:
                    continue
                    
                label = self.class_mapping[cls_id]
                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].tolist()
                
                bbox = BoundingBox(
                    x1=xyxy[0], y1=xyxy[1], x2=xyxy[2], y2=xyxy[3],
                    confidence=conf,
                    frame=frame_num
                )
                current_detections.append((label, bbox))
                
            # Update Tracker
            confirmed_tracks = tracker.update(current_detections, frame_num)
            
            # Process Confirmed
            for tid, label, bbox in confirmed_tracks:
                if tid not in tracked_objects:
                    tracked_objects[tid] = TrackedDetection(tid, label)
                    if on_detection:
                        # await or sync call? on_detection is likely async in our arch
                        # But callable definition didn't specify. Assuming sync wrapper or ignore await.
                        pass 
                        
                tracked_objects[tid].add_bbox(bbox)
                
                # Captures
                capture_manager.consider_frame(
                    tid, frame, frame_num, bbox, output_path, fps, capture_interval=1.0
                )
                
            # Progress
            if frame_num % 10 == 0:
                if on_progress:
                    # await on_progress if async?
                    # Since process_video is async, we should await if on_progress is async
                    if asyncio.iscoroutinefunction(on_progress):
                        await on_progress(frame_num, total_frames, f"Processing frame {frame_num}/{total_frames}")
                
            # Yield to event loop
            if frame_num % 5 == 0:
                await asyncio.sleep(0)
                
        cap.release()
        
        det_list = list(tracked_objects.values())
        
        return DetectionResult(
            video_path=video_path,
            total_frames=total_frames,
            fps=fps,
            duration_seconds=total_frames / fps if fps else 0,
            width=width,
            height=height,
            detections=det_list,
            frames_processed=frame_num
        )
