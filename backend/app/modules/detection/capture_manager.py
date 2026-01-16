"""Capture Manager for Detected Object Image Extraction.

This module handles the intelligent capture of detected objects during
video processing. It implements temporal consensus by distributing captures
uniformly across a track's duration for visual diversity.

Features:
    - Stability-based capture decisions
    - Dual image output (clean crop + annotated bbox)
    - Configurable capture quotas based on track duration
    - Color-coded bounding boxes by detection type

Example:
    >>> manager = CaptureManager(stability_threshold=0.5)
    >>> result = manager.consider_frame(track_id=1, frame_img=frame, ...)
    >>> if result:
    ...     clean_path, bbox_path = result
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from .models import BoundingBox

# BGR colors for bounding boxes by detection type
BBOX_COLORS = {
    "person": (0, 255, 0),        # Verde
    "face": (0, 0, 255),          # Rojo
    "license_plate": (255, 0, 0), # Azul
    "default": (0, 255, 255)      # Amarillo
}

class CaptureManager:
    """
    Gestor de capturas de objetos detectados.
    Guarda 2 versiones de cada captura:
    - Versión limpia (crop sin anotaciones)
    - Versión con bounding box coloreado según tipo de detección
    
    Temporal Consensus Mode:
    - Captura entre 1-6 frames por track dependiendo de la duración
    - Distribuye las capturas uniformemente para diversidad visual
    """
    def __init__(self, stability_threshold=0.5, stability_frames=3, image_quality=95, crop_margin=20, max_captures_per_track=6):
        self.stability_threshold = stability_threshold
        self.stability_frames = stability_frames
        self.image_quality = image_quality
        self.crop_margin = crop_margin
        self.max_captures_per_track = max_captures_per_track
        # {track_id: {stable_count, last_capture_time, captures_taken, target_timestamps}}
        self.track_data = {}

    def get_capture_quota(self, track_duration_seconds: float) -> int:
        """
        Calcula cuántas capturas tomar basándose en la duración del rastro.
        - < 2s  → 1 captura
        - 2-4s  → 2 capturas
        - 4-6s  → 3 capturas
        - > 6s  → min(6, duration // 2)
        """
        if track_duration_seconds < 2:
            return 1
        elif track_duration_seconds < 4:
            return 2
        elif track_duration_seconds < 6:
            return 3
        else:
            return min(self.max_captures_per_track, int(track_duration_seconds // 2))
    
    def get_target_timestamps(self, track_start_time: float, track_duration: float, quota: int) -> list:
        """
        Genera timestamps objetivo distribuidos uniformemente a lo largo del rastro.
        """
        if quota <= 1:
            return [track_start_time + track_duration / 2]  # Captura en el medio
        
        interval = track_duration / (quota - 1) if quota > 1 else track_duration
        return [track_start_time + i * interval for i in range(quota)]

    def consider_frame(self, track_id: int, frame_img: np.ndarray, frame_num: int, 
                       bbox: BoundingBox, output_dir: Path, fps: float, 
                       capture_interval: float, detection_type: str = "default") -> Optional[Tuple[str, str]]:
        """
        Evalúa si capturar este frame basándose en estabilidad, tiempo y cuota.
        
        Args:
            track_id: ID único del track
            frame_img: Frame completo BGR
            frame_num: Número de frame actual
            bbox: Bounding box de la detección
            output_dir: Directorio de salida
            fps: Frames por segundo del video
            capture_interval: Intervalo mínimo entre capturas (segundos)
            detection_type: Tipo de detección (person, face, license_plate)
            
        Returns:
            Tuple (path_clean, path_bbox) si se captura, None si no
        """
        if track_id not in self.track_data:
            self.track_data[track_id] = {
                "stable_count": 0, 
                "last_capture_time": -999,
                "captures_taken": 0,
                "first_seen_time": frame_num / fps
            }
            
        data = self.track_data[track_id]
        
        # Check if we've already taken max captures for this track
        if data["captures_taken"] >= self.max_captures_per_track:
            return None
        
        # Check stability
        if bbox.confidence >= self.stability_threshold:
            data["stable_count"] += 1
        else:
            data["stable_count"] = 0
            
        if data["stable_count"] < self.stability_frames:
            return None
            
        # Check timing
        timestamp = frame_num / fps
        if timestamp - data["last_capture_time"] < capture_interval:
            return None
        
        # Save capture and increment counter
        result = self._save_capture(track_id, frame_img, frame_num, bbox, output_dir, timestamp, detection_type)
        if result:
            data["captures_taken"] += 1
        return result

    def _save_capture(self, track_id: int, frame_img: np.ndarray, frame_num: int, 
                      bbox: BoundingBox, output_dir: Path, timestamp: float,
                      detection_type: str) -> Optional[Tuple[str, str]]:
        """
        Guarda 2 versiones del crop: limpia y con bounding box coloreado.
        
        Returns:
            Tuple (path_clean, path_bbox) o None si el crop está vacío
        """
        track_dir = output_dir / f"track_{track_id}"
        track_dir.mkdir(parents=True, exist_ok=True)
        
        h, w = frame_img.shape[:2]
        x1_c = max(0, int(bbox.x1) - self.crop_margin)
        y1_c = max(0, int(bbox.y1) - self.crop_margin)
        x2_c = min(w, int(bbox.x2) + self.crop_margin)
        y2_c = min(h, int(bbox.y2) + self.crop_margin)
        
        crop = frame_img[y1_c:y2_c, x1_c:x2_c]
        if crop.size == 0:
            return None
        
        # 1. Guardar versión limpia (sin anotaciones)
        path_clean = track_dir / f"capture_{frame_num}.jpg"
        cv2.imwrite(str(path_clean), crop, [int(cv2.IMWRITE_JPEG_QUALITY), self.image_quality])
        
        # 2. Guardar versión con bounding box coloreado
        crop_bbox = crop.copy()
        
        # Calcular coordenadas relativas al crop
        rx1 = int(bbox.x1) - x1_c
        ry1 = int(bbox.y1) - y1_c
        rx2 = int(bbox.x2) - x1_c
        ry2 = int(bbox.y2) - y1_c
        
        # Obtener color según tipo de detección
        color = BBOX_COLORS.get(detection_type, BBOX_COLORS["default"])
        
        # Dibujar rectángulo
        cv2.rectangle(crop_bbox, (rx1, ry1), (rx2, ry2), color, 2)
        
        # Dibujar etiqueta con tipo y confianza
        label = f"{detection_type} {bbox.confidence:.0%}"
        label_y = max(ry1 - 5, 15)  # Evitar que la etiqueta salga del frame
        cv2.putText(crop_bbox, label, (rx1, label_y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
        
        path_bbox = track_dir / f"capture_{frame_num}_bbox.jpg"
        cv2.imwrite(str(path_bbox), crop_bbox, [int(cv2.IMWRITE_JPEG_QUALITY), self.image_quality])
        
        self.track_data[track_id]["last_capture_time"] = timestamp
        return str(path_clean), str(path_bbox)
