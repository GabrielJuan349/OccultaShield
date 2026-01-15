import cv2
import numpy as np
import logging
import torch
import torch.nn.functional as F
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
import asyncio
import time

try:
    import kornia
    import kornia.filters
    KORNIA_AVAILABLE = True
except ImportError:
    KORNIA_AVAILABLE = False

from services.progress_manager import progress_manager, ProcessingPhase

logger = logging.getLogger(__name__)

# =============================================================================
# KORNIA EFFECTS - Efectos acelerados por GPU
# =============================================================================
class KorniaEffects:
    """
    Efectos de anonimización acelerados por GPU usando Kornia + PyTorch.
    """
    
    def __init__(self, device: str = None):
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        # Cache de tensores de ruido para consistencia entre frames
        self.noise_cache: Dict[Tuple[int, int, int], torch.Tensor] = {}
        
        logger.info(f"KorniaEffects initialized on {self.device}")
        
        if self.device == "cuda" and not KORNIA_AVAILABLE:
            logger.warning("Kornia not available, falling back to CPU OpenCV")
    
    def numpy_to_tensor(self, frame: np.ndarray) -> torch.Tensor:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0)
        tensor = tensor.float().div(255.0).to(self.device)
        return tensor
    
    def tensor_to_numpy(self, tensor: torch.Tensor) -> np.ndarray:
        arr = tensor.squeeze(0).permute(1, 2, 0)
        arr = arr.mul(255.0).clamp(0, 255).byte()
        arr = arr.cpu().numpy()
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    
    def blur_region(self, tensor: torch.Tensor, bbox: Tuple[int, int, int, int], mask: Optional[torch.Tensor] = None, kernel_size: int = 31, sigma: float = 15.0) -> torch.Tensor:
        if not KORNIA_AVAILABLE:
            return self._blur_opencv_fallback(tensor, bbox, kernel_size, sigma)
        
        x1, y1, x2, y2 = bbox
        result = tensor.clone()
        roi = tensor[:, :, y1:y2, x1:x2]

        # Defense in depth: Skip if ROI has zero dimensions
        if roi.shape[2] == 0 or roi.shape[3] == 0:
            return tensor

        if kernel_size % 2 == 0: kernel_size += 1

        blurred_roi = kornia.filters.gaussian_blur2d(roi, (kernel_size, kernel_size), (sigma, sigma))
        
        if mask is not None:
            # Mask is 1.0 where we want effect, 0.0 where we keep original
            m_roi = mask[:, :, y1:y2, x1:x2]
            # Ensure proper broadcasting if mask is single channel
            if m_roi.shape[1] == 1:
                m_roi = m_roi.expand_as(roi)
            result[:, :, y1:y2, x1:x2] = roi * (1.0 - m_roi) + blurred_roi * m_roi
        else:
            result[:, :, y1:y2, x1:x2] = blurred_roi
            
        return result
    
    def _blur_opencv_fallback(self, tensor: torch.Tensor, bbox: Tuple[int, int, int, int], kernel_size: int, sigma: float) -> torch.Tensor:
        frame = self.tensor_to_numpy(tensor)
        x1, y1, x2, y2 = bbox
        roi = frame[y1:y2, x1:x2]
        k = kernel_size | 1
        blurred = cv2.GaussianBlur(roi, (k, k), sigma)
        frame[y1:y2, x1:x2] = blurred
        return self.numpy_to_tensor(frame)
    
    def pixelate_region(self, tensor: torch.Tensor, bbox: Tuple[int, int, int, int], mask: Optional[torch.Tensor] = None, blocks: int = 10, track_id: int = 0, add_noise: bool = True) -> torch.Tensor:
        x1, y1, x2, y2 = bbox
        result = tensor.clone()
        roi = tensor[:, :, y1:y2, x1:x2]
        orig_h, orig_w = roi.shape[2], roi.shape[3]
        
        if orig_h < 2 or orig_w < 2: return result
        
        small = F.interpolate(roi, size=(blocks, blocks), mode='bilinear', align_corners=False)
        
        if add_noise:
            cache_key = (track_id, blocks, 3)
            if cache_key not in self.noise_cache:
                gen = torch.Generator(device=self.device)
                gen.manual_seed(track_id * 1000 + blocks)
                noise = torch.rand(1, 3, blocks, blocks, generator=gen, device=self.device) * 0.2 - 0.1
                self.noise_cache[cache_key] = noise
            
            small = small + self.noise_cache[cache_key]
            small = small.clamp(0, 1)
        
        pixelated = F.interpolate(small, size=(orig_h, orig_w), mode='nearest')
        
        if mask is not None:
             m_roi = mask[:, :, y1:y2, x1:x2]
             if m_roi.shape[1] == 1:
                m_roi = m_roi.expand_as(roi)
             result[:, :, y1:y2, x1:x2] = roi * (1.0 - m_roi) + pixelated * m_roi
        else:
             result[:, :, y1:y2, x1:x2] = pixelated
             
        return result
    
    def clear_cache(self):
        self.noise_cache.clear()
        if self.device == "cuda":
            torch.cuda.empty_cache()

# Instancia global
kornia_effects = KorniaEffects() if KORNIA_AVAILABLE or torch.cuda.is_available() else None


class VideoAnonymizer:
    """
    Anonimizador de video con aceleración GPU (Kornia) y fallback CPU (OpenCV).
    """
    
    def __init__(self, use_gpu: bool = True, batch_frames: int = 8):
        self.use_gpu = use_gpu and (KORNIA_AVAILABLE or torch.cuda.is_available())
        self.batch_frames = batch_frames
        self.kornia = kornia_effects if self.use_gpu else None
        self.noise_cache = {}
        
        logger.info(f"VideoAnonymizer: GPU={self.use_gpu}, batch={batch_frames}")

    def _interpolate_bboxes(self, actions: List[Dict]) -> List[Dict]:
        for action in actions:
            bboxes = action.get("bboxes", {})
            if not bboxes: continue
                
            frames = sorted(bboxes.keys())
            if len(frames) < 2: continue
            
            interpolated = dict(bboxes)
            for i in range(len(frames) - 1):
                f1, f2 = frames[i], frames[i + 1]
                gap = f2 - f1
                if 1 < gap <= 10:
                    b1 = bboxes[f1]
                    b2 = bboxes[f2]
                    for f in range(f1 + 1, f2):
                        t = (f - f1) / gap
                        interpolated[f] = [
                            int(b1[0] + t * (b2[0] - b1[0])),
                            int(b1[1] + t * (b2[1] - b1[1])),
                            int(b1[2] + t * (b2[2] - b1[2])),
                            int(b1[3] + t * (b2[3] - b1[3])),
                        ]
            action["bboxes"] = interpolated
        return actions

    async def apply_anonymization(
        self,
        video_id: str,
        input_path: str,
        output_path: str,
        actions: List[Dict[str, Any]],
        user_id: str = "default_user"
    ):
        start_time = time.time()
        logger.info(f"Anonymizing video {video_id}: {input_path} -> {output_path} (User: {user_id})")
        
        # Notify phase change
        await progress_manager.change_phase(
            video_id, ProcessingPhase.ANONYMIZING, "Aplicando efectos de anonimización..."
        )
        
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Failed to open video: {input_path}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        actions = self._interpolate_bboxes(actions)
        self.noise_cache = {}
        if self.kornia: self.kornia.clear_cache()
        
        try:
            if self.use_gpu and self.kornia:
                await self._process_gpu_batched(video_id, cap, out, actions, total_frames, user_id)
            else:
                await self._process_cpu(video_id, cap, out, actions, total_frames, user_id)
        finally:
            cap.release()
            out.release()
        
        # --- POST-PROCESSING: STRIP AND SET METADATA ---
        await self._finalize_metadata(output_path, user_id, video_id)
        
        elapsed = time.time() - start_time
        fps_proc = total_frames / elapsed if elapsed > 0 else 0
        logger.info(f"Anonymization completed: {elapsed:.2f}s ({fps_proc:.1f} fps)")
        
        await progress_manager.update_progress(
            video_id, 100, total_frames, total_frames, "Anonimización completada"
        )

    async def _finalize_metadata(self, video_path: str, user_id: str, video_id: str):
        """
        Elimina metadatos sensibles y establece etiquetas profesionales traducidas al inglés.
        Requiere ffmpeg instalado.
        """
        import os
        import subprocess
        from datetime import datetime
        
        temp_path = video_path.replace(".mp4", "_clean.mp4")
        if temp_path == video_path: temp_path += ".tmp.mp4"
        
        # English translations for metadata tags
        title = "Video Protected by OccultaShield"
        copyright_msg = f"Property of {user_id} - Processed under GDPR"
        description = "Irreversible anonymization of faces and sensitive objects via OccultaShield Engine."
        comment = f"Processing ID: {video_id}"
        software = "OccultaShield Engine v1.0 (YOLOv11-seg+Gemma-3n enabled)"
        curr_date = datetime.now().isoformat()
        
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-map_metadata", "-1",                 # Strip all original global metadata
            "-map_chapters", "-1",                 # Strip chapters
            "-metadata", f"title={title}",
            "-metadata", f"artist={user_id}",
            "-metadata", f"copyright={copyright_msg}",
            "-metadata", f"date={curr_date}",
            "-metadata", f"description={description}",
            "-metadata", f"comment={comment}",
            "-metadata", f"encoder={software}",    # Standard field for software/encoder
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-movflags", "+faststart",
            "-c:v", "libx264", 
            "-pix_fmt", "yuv420p", # Ensure compatibility with all players
            "-preset", "fast",
            "-crf", "23",          # Quality preset
            #"-c:a", "aac",         # AAC audio if present
            "-an", # para asegurar que no escriba pista de audio basura
            temp_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                os.replace(temp_path, video_path)
                logger.info(f"Metadata finalized for {video_id}")
            else:
                logger.warning(f"FFmpeg metadata error: {result.stderr}")
                if os.path.exists(temp_path): os.remove(temp_path)
        except FileNotFoundError:
            logger.warning("FFmpeg not found. Metadata stripping skipped.")
        except Exception as e:
            logger.error(f"Error finalizing metadata: {e}")

    async def _process_gpu_batched(self, video_id, cap, out, actions, total_frames, user_id):
        frame_buffer = []
        frame_indices = []
        frame_idx = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                if frame_buffer:
                    await self._process_batch_gpu(frame_buffer, frame_indices, actions, out)
                break
            
            frame_idx += 1
            frame_buffer.append(frame)
            frame_indices.append(frame_idx)
            
            if len(frame_buffer) >= self.batch_frames:
                await self._process_batch_gpu(frame_buffer, frame_indices, actions, out)
                frame_buffer = []
                frame_indices = []
                
                percent = int((frame_idx / total_frames) * 100)
                await progress_manager.update_progress(
                    video_id, percent, frame_idx, total_frames, 
                    f"Anonimizando - Frame {frame_idx}/{total_frames}"
                )

    async def _process_batch_gpu(self, frames, frame_indices, actions, out):
        for frame, frame_idx in zip(frames, frame_indices):
            tensor = self.kornia.numpy_to_tensor(frame)
            
            blur_regions = []
            pixelate_regions = []
            mask_regions = []
            
            for action in actions:
                bboxes_map = action.get("bboxes", {})
                action_type = action.get("type", "blur")
                config = action.get("config", {})
                track_id = action.get("track_id", 0)
                
                box = bboxes_map.get(frame_idx)
                if not box: continue

                # FIX: Validate bbox dimensions to prevent zero-size ROI errors
                H, W = tensor.shape[2], tensor.shape[3]
                x1 = max(0, min(int(box[0]), W))
                y1 = max(0, min(int(box[1]), H))
                x2 = max(0, min(int(box[2]), W))
                y2 = max(0, min(int(box[3]), H))

                # Skip invalid regions (zero or negative dimensions)
                if x2 <= x1 or y2 <= y1:
                    continue

                bbox = (x1, y1, x2, y2)

                if action_type == "blur":
                    blur_regions.append({
                        "bbox": bbox, "mask": self._create_mask_tensor(action, frame_idx, tensor.shape), 
                        "kernel_size": config.get("kernel_size", 31), "sigma": config.get("sigma", 15.0)
                    })
                elif action_type == "pixelate":
                    pixelate_regions.append({
                        "bbox": bbox, "mask": self._create_mask_tensor(action, frame_idx, tensor.shape),
                        "blocks": config.get("blocks", 10), "track_id": track_id, "add_noise": config.get("add_noise", True)
                    })
                elif action_type == "mask":
                    mask_regions.append({"bbox": bbox, "key": config.get("key", 42)})
            
            for region in blur_regions:
                tensor = self.kornia.blur_region(tensor, region["bbox"], mask=region["mask"], kernel_size=region["kernel_size"], sigma=region["sigma"])
            
            for region in pixelate_regions:
                tensor = self.kornia.pixelate_region(tensor, region["bbox"], mask=region["mask"], blocks=region["blocks"], track_id=region["track_id"], add_noise=region["add_noise"])
            
            result_frame = self.kornia.tensor_to_numpy(tensor)
            
            for region in mask_regions:
                self._apply_mask_cpu(result_frame, region["bbox"], region["key"])
            
            out.write(result_frame)
        
        await asyncio.sleep(0)

    async def _process_cpu(self, video_id, cap, out, actions, total_frames, user_id):
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret: break
                
            frame_idx += 1
            frame = self._process_frame_cpu(frame, frame_idx, actions)
            out.write(frame)
            
            if frame_idx % 20 == 0:
                percent = int((frame_idx / total_frames) * 100)
                await progress_manager.update_progress(
                    video_id, percent, frame_idx, total_frames, 
                    f"Anonimizando - Frame {frame_idx}/{total_frames}"
                )
                await asyncio.sleep(0)

    def _process_frame_cpu(self, frame, frame_idx, actions):
        for action in actions:
            bboxes_map = action.get("bboxes", {})
            action_type = action.get("type", "blur")
            config = action.get("config", {})
            track_id = action.get("track_id", 0)
            
            box = bboxes_map.get(frame_idx)
            if box:
                self._apply_effect_cpu(frame, box, action_type, config, track_id)
        
        return frame

    def _apply_effect_cpu(self, frame, bbox, effect, config, track_id=0):
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = map(int, bbox)
        x1 = max(0, x1); y1 = max(0, y1); x2 = min(w, x2); y2 = min(h, y2)
        if x2 <= x1 or y2 <= y1: return

        roi = frame[y1:y2, x1:x2]
        
        if effect == 'blur':
            factor = config.get("factor", 3.0)
            k_w = int((x2 - x1) // factor) | 1
            k_h = int((y2 - y1) // factor) | 1
            blurred = cv2.GaussianBlur(roi, (k_w, k_h), 0)
            frame[y1:y2, x1:x2] = blurred
        elif effect == 'pixelate':
            blocks = config.get("blocks", 30)
            small = cv2.resize(roi, (blocks, blocks), interpolation=cv2.INTER_LINEAR)
            cache_key = (track_id, blocks)
            if cache_key not in self.noise_cache:
                rng = np.random.default_rng(seed=track_id * 1000 + blocks)
                self.noise_cache[cache_key] = rng.integers(-30, 30, (blocks, blocks, 3), dtype=np.int16)
            noise = self.noise_cache[cache_key]
            dirty_small = small.astype(np.int16) + noise
            dirty_small = np.clip(dirty_small, 0, 255).astype(np.uint8)
            pixelated = cv2.resize(dirty_small, (x2-x1, y2-y1), interpolation=cv2.INTER_NEAREST)
            frame[y1:y2, x1:x2] = pixelated
        elif effect == 'mask':
            self._apply_mask_cpu(frame, (x1, y1, x2, y2), config.get("key", 42))

    def _apply_mask_cpu(self, frame, bbox, key):
        x1, y1, x2, y2 = bbox
        roi = frame[y1:y2, x1:x2]
        shape = roi.shape
        flat = roi.flatten()
        rng = np.random.default_rng(key)
        perm = rng.permutation(len(flat))
        scrambled = flat[perm]
        frame[y1:y2, x1:x2] = scrambled.reshape(shape)
    def _create_mask_tensor(self, action, frame_idx, tensor_shape):
        """Creates a boolean mask tensor from polygon points or returns None if no mask."""
        masks_map = action.get("masks", {})
        mask_poly = masks_map.get(frame_idx)
        
        # Dynamic Discernibility Threshold
        # Calculate BBox area ratio
        bboxes_map = action.get("bboxes", {})
        box = bboxes_map.get(frame_idx)
        if box:
             x1, y1, x2, y2 = box
             area = (x2 - x1) * (y2 - y1)
             # tensor_shape is (B, C, H, W) -> H, W = shape[2], shape[3]
             H, W = tensor_shape[2], tensor_shape[3]
             total_area = H * W
             ratio = area / total_area
             
             # If extremely small, we can skip or fade.
             # Threshold: 0.1% (0.001)
             if ratio < 0.001:
                 return torch.zeros((1, 1, H, W)).to(self.kornia.device) # Empty mask = no effect
                 
             # TODO: Implement gradual fading alpha based on ratio, but for now strict threshold is better than giant blob.

        if not mask_poly:
            return None
            
        # Create mask from poly
        H, W = tensor_shape[2], tensor_shape[3]
        mask_img = np.zeros((H, W), dtype=np.uint8)
        
        # mask_poly is flattened list [x1, y1, x2, y2...]
        pts = np.array(mask_poly).reshape((-1, 1, 2)).astype(np.int32)
        cv2.fillPoly(mask_img, [pts], 255)
        
        # Convert to tensor
        # shape (1, 1, H, W)
        mask_tensor = torch.from_numpy(mask_img).float().div(255.0).unsqueeze(0).unsqueeze(0).to(self.kornia.device)
        return mask_tensor
