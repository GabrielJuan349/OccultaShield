import cv2
import numpy as np
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

class VideoAnonymizer:
    def __init__(self):
        pass

    async def apply_anonymization(
        self,
        input_path: str,
        output_path: str,
        actions: List[Dict[str, Any]] # List of {action: 'blur', tracks: [bbox_history...]}
    ):
        """
        actions structure:
        [
            {
                "type": "blur",
                "bboxes": {frame_idx: [x1, y1, x2, y2]}  # Optimized lookup
            },
            ...
        ]
        """
        logger.info(f"Anonymizing video: {input_path} -> {output_path}")
        
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Failed to open video: {input_path}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_idx = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                frame_idx += 1
                
                # Apply effects
                frame = self._process_frame(frame, frame_idx, actions)
                
                out.write(frame)
                
                if frame_idx % 20 == 0:
                    await asyncio.sleep(0) # Yield
                    
        finally:
            cap.release()
            out.release()
            
        logger.info("Anonymization completed.")

    def _process_frame(self, frame: np.ndarray, frame_idx: int, actions: List[Dict]) -> np.ndarray:
        for action_item in actions:
            bboxes_map = action_item.get("bboxes", {})
            action_type = action_item.get("type", "blur")
            
            box = bboxes_map.get(frame_idx) 
            # box could be a list of boxes for this frame (if multiple tracks merged)
            # Or simplified: one entry per action object.
            
            # Assuming 'box' is a single [x1, y1, x2, y2] or None
            if box:
                 self._apply_effect(frame, box, action_type)
                 
        return frame

    def _apply_effect(self, frame: np.ndarray, bbox: list, effect: str):
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = map(int, bbox)
        
        # Clip
        x1 = max(0, x1); y1 = max(0, y1)
        x2 = min(w, x2); y2 = min(h, y2)
        
        if x2 <= x1 or y2 <= y1:
            return

        roi = frame[y1:y2, x1:x2]
        
        if effect == 'blur':
            # Gaussian Blur
            # Kernel size depends on ROI size
            k_w = (x2 - x1) // 3 | 1 # Odd number
            k_h = (y2 - y1) // 3 | 1
            blurred = cv2.GaussianBlur(roi, (k_w, k_h), 0)
            frame[y1:y2, x1:x2] = blurred
            
        elif effect == 'pixelate':
            # Resize down and up
            p_w, p_h = max(1, (x2-x1)//10), max(1, (y2-y1)//10)
            temp = cv2.resize(roi, (p_w, p_h), interpolation=cv2.INTER_LINEAR)
            pixelated = cv2.resize(temp, (x2-x1, y2-y1), interpolation=cv2.INTER_NEAREST)
            frame[y1:y2, x1:x2] = pixelated
            
        elif effect == 'mask':
            # Black rectangle
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), -1)
