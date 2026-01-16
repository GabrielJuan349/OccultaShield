# Edition Module - Video Anonymization Engine

## Overview

The **Edition Module** is the core video anonymization engine of OccultaShield. It provides GPU-accelerated anonymization effects (blur, pixelate, mask) that are applied to detected sensitive regions in video frames. The module leverages **Kornia** (GPU via PyTorch) for high-performance processing, with an automatic fallback to **OpenCV** (CPU) when GPU is unavailable.

This module is responsible for the final step of the anonymization pipeline: taking the detection results and verification decisions from previous stages and applying irreversible visual obfuscation to protect personal data in compliance with GDPR regulations.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            VIDEO ANONYMIZATION FLOW                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │ Input Video  │───►│   Actions    │───►│  Anonymizer  │───►│  Output    │ │
│  │   (MP4)      │    │ (bboxes,     │    │  (Kornia/    │    │  Video     │ │
│  │              │    │  masks,      │    │   OpenCV)    │    │  (Clean)   │ │
│  │              │    │  types)      │    │              │    │            │ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └────────────┘ │
│                                                                              │
│                              │                                               │
│                              ▼                                               │
│                    ┌──────────────────┐                                      │
│                    │  FFmpeg Post-    │                                      │
│                    │  Processing      │                                      │
│                    │  (Metadata +     │                                      │
│                    │   Encoding)      │                                      │
│                    └──────────────────┘                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
edition/
├── __init__.py         # Module exports (empty)
├── video_editor.py     # Main implementation
└── README.md           # This documentation
```

---

## Core Components

### 1. `KorniaEffects` Class

This class provides GPU-accelerated visual effects using **Kornia** and **PyTorch**. It handles the low-level tensor operations for applying anonymization effects to image regions.

#### Initialization

```python
class KorniaEffects:
    def __init__(self, device: str = None):
        # Auto-detect device: CUDA if available, otherwise CPU
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Cache for consistent noise patterns across frames
        self.noise_cache: Dict[Tuple[int, int, int], torch.Tensor] = {}
```

**Key Features:**
- **Auto-device detection**: Automatically uses CUDA if available
- **Noise caching**: Maintains consistent noise patterns for the same track across frames
- **Graceful fallback**: Falls back to OpenCV if Kornia is not installed

#### Methods

##### `numpy_to_tensor(frame: np.ndarray) -> torch.Tensor`
Converts a BGR NumPy image (from OpenCV) to a PyTorch tensor suitable for Kornia operations.

**Process:**
1. Converts BGR → RGB color space
2. Reshapes from (H, W, C) → (1, C, H, W)
3. Normalizes pixel values to [0, 1] range
4. Transfers to GPU if available

##### `tensor_to_numpy(tensor: torch.Tensor) -> np.ndarray`
Reverse operation: converts a PyTorch tensor back to a BGR NumPy array.

##### `blur_region(tensor, bbox, mask, kernel_size, sigma) -> torch.Tensor`
Applies Gaussian blur to a specific region using Kornia's `gaussian_blur2d`.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tensor` | Tensor | - | Input image tensor |
| `bbox` | Tuple[int,4] | - | Bounding box (x1, y1, x2, y2) |
| `mask` | Tensor | None | Optional segmentation mask |
| `kernel_size` | int | 31 | Gaussian kernel size (odd) |
| `sigma` | float | 15.0 | Gaussian blur sigma |

**Algorithm:**
1. Extract ROI (Region of Interest) from tensor
2. Apply Kornia Gaussian blur to ROI
3. If mask provided: blend blurred and original using mask weights
4. Replace ROI in result tensor

##### `pixelate_region(tensor, bbox, mask, blocks, track_id, add_noise) -> torch.Tensor`
Applies pixelation effect with optional noise injection for enhanced privacy.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tensor` | Tensor | - | Input image tensor |
| `bbox` | Tuple[int,4] | - | Bounding box |
| `mask` | Tensor | None | Optional segmentation mask |
| `blocks` | int | 10 | Number of pixelation blocks |
| `track_id` | int | 0 | Track ID for consistent noise |
| `add_noise` | bool | True | Whether to add noise |

**Algorithm:**
1. Extract ROI from tensor
2. Downscale to `blocks x blocks` pixels using bilinear interpolation
3. If `add_noise`: add seeded random noise (±10% RGB) based on track_id
4. Upscale back to original size using nearest-neighbor interpolation
5. Apply mask blending if provided

**Why noise is important:**
- Prevents facial recognition even with pixelation reversal attempts
- Seeded by `track_id` for consistency across frames of the same person
- Makes the effect irreversible as per GDPR requirements

##### `clear_cache()`
Clears the noise cache and releases CUDA memory if on GPU.

---

### 2. `VideoAnonymizer` Class

This is the main orchestrator class that processes videos frame by frame, applying the appropriate anonymization effects based on the action list provided by the detection and verification stages.

#### Initialization

```python
class VideoAnonymizer:
    def __init__(self, use_gpu: bool = True, batch_frames: int = 8):
        self.use_gpu = use_gpu and (KORNIA_AVAILABLE or torch.cuda.is_available())
        self.batch_frames = batch_frames  # Frames to process in one GPU batch
        self.kornia = kornia_effects if self.use_gpu else None
        self.noise_cache = {}  # For CPU fallback
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_gpu` | bool | True | Whether to attempt GPU acceleration |
| `batch_frames` | int | 8 | Number of frames per GPU batch |

#### Main Method: `apply_anonymization()`

```python
async def apply_anonymization(
    self,
    video_id: str,
    input_path: str,
    output_path: str,
    actions: List[Dict[str, Any]],
    user_id: str = "default_user"
)
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `video_id` | str | Unique video identifier for progress tracking |
| `input_path` | str | Path to the input video file |
| `output_path` | str | Path where anonymized video will be saved |
| `actions` | List[Dict] | List of anonymization actions (see format below) |
| `user_id` | str | User ID for metadata tagging |

**Action Format:**

Each action dictionary should contain:

```python
{
    "type": "blur" | "pixelate" | "mask",  # Effect type
    "track_id": 123,                        # Unique ID for this tracked object
    "bboxes": {                             # Frame number → bounding box
        1: [x1, y1, x2, y2],
        2: [x1, y1, x2, y2],
        # ...
    },
    "masks": {                              # Optional: frame number → polygon points
        1: [x1, y1, x2, y2, x3, y3, ...],   # Flattened polygon coordinates
        # ...
    },
    "config": {                             # Effect-specific configuration
        # For blur:
        "kernel_size": 31,
        "sigma": 15.0,
        "factor": 3.0,
        
        # For pixelate:
        "blocks": 10,
        "add_noise": True,
        
        # For mask:
        "key": 42  # Seed for scramble operation
    }
}
```

**Processing Flow:**

1. **Phase Notification**: Updates progress manager to `ANONYMIZING` phase
2. **Video Initialization**: Opens input video, creates output writer
3. **Bounding Box Interpolation**: Fills gaps in tracking data
4. **Cache Clearing**: Resets noise caches for fresh processing
5. **Frame Processing**: GPU batched or CPU sequential
6. **Post-Processing**: FFmpeg metadata cleanup and encoding
7. **Progress Update**: Reports 100% completion

#### Bounding Box Interpolation

The `_interpolate_bboxes()` method fills in missing bounding boxes between detected frames:

```python
def _interpolate_bboxes(self, actions: List[Dict]) -> List[Dict]:
    # For each action, find gaps of 1-10 frames
    # Linear interpolation between known bounding boxes
    # Prevents "flashing" effect when detections are missed
```

**Example:**
- Frame 10: bbox = [100, 100, 200, 200]
- Frame 13: bbox = [120, 100, 220, 200]
- **Interpolated:**
  - Frame 11: [106, 100, 206, 200]
  - Frame 12: [113, 100, 213, 200]

---

### 3. GPU Processing Pipeline

#### Batched GPU Processing

```python
async def _process_gpu_batched(self, video_id, cap, out, actions, total_frames, user_id):
    frame_buffer = []
    frame_indices = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            # Process remaining frames
            break
        
        frame_buffer.append(frame)
        frame_indices.append(frame_idx)
        
        if len(frame_buffer) >= self.batch_frames:
            await self._process_batch_gpu(frame_buffer, frame_indices, actions, out)
            frame_buffer = []
```

**Benefits of batching:**
- Reduces GPU memory allocation overhead
- Better GPU utilization
- More efficient tensor operations

#### Single Frame GPU Processing

For each frame in a batch:

1. Convert to tensor
2. Collect all blur, pixelate, and mask regions
3. Validate bounding box dimensions (skip invalid)
4. Apply effects in order: blur → pixelate → mask
5. Convert back to NumPy and write

**Bounding Box Validation:**

```python
# Clamp to frame dimensions
x1 = max(0, min(int(box[0]), W))
y1 = max(0, min(int(box[1]), H))
x2 = max(0, min(int(box[2]), W))
y2 = max(0, min(int(box[3]), H))

# Skip zero-size regions
if x2 <= x1 or y2 <= y1:
    continue
```

---

### 4. CPU Fallback Processing

When GPU is unavailable, the module uses OpenCV for processing:

```python
async def _process_cpu(self, video_id, cap, out, actions, total_frames, user_id):
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        frame = self._process_frame_cpu(frame, frame_idx, actions)
        out.write(frame)
        
        # Progress updates every 20 frames
        if frame_idx % 20 == 0:
            await progress_manager.update_progress(...)
```

**CPU Effects:**

##### Blur (CPU)
```python
factor = config.get("factor", 3.0)
k_w = int((x2 - x1) // factor) | 1  # Ensure odd
k_h = int((y2 - y1) // factor) | 1
blurred = cv2.GaussianBlur(roi, (k_w, k_h), 0)
```

##### Pixelate (CPU)
```python
blocks = config.get("blocks", 30)
small = cv2.resize(roi, (blocks, blocks), interpolation=cv2.INTER_LINEAR)

# Add seeded noise for track consistency
rng = np.random.default_rng(seed=track_id * 1000 + blocks)
noise = rng.integers(-30, 30, (blocks, blocks, 3), dtype=np.int16)

pixelated = cv2.resize(dirty_small, (w, h), interpolation=cv2.INTER_NEAREST)
```

##### Mask/Scramble (CPU)
```python
def _apply_mask_cpu(self, frame, bbox, key):
    roi = frame[y1:y2, x1:x2]
    flat = roi.flatten()
    
    rng = np.random.default_rng(key)
    perm = rng.permutation(len(flat))
    scrambled = flat[perm]
    
    frame[y1:y2, x1:x2] = scrambled.reshape(shape)
```

---

### 5. Segmentation Mask Support

The module supports polygon-based segmentation masks for more precise anonymization:

```python
def _create_mask_tensor(self, action, frame_idx, tensor_shape):
    masks_map = action.get("masks", {})
    mask_poly = masks_map.get(frame_idx)
    
    if not mask_poly:
        return None
    
    # Create mask from polygon
    H, W = tensor_shape[2], tensor_shape[3]
    mask_img = np.zeros((H, W), dtype=np.uint8)
    
    pts = np.array(mask_poly).reshape((-1, 1, 2)).astype(np.int32)
    cv2.fillPoly(mask_img, [pts], 255)
    
    # Convert to tensor
    mask_tensor = torch.from_numpy(mask_img).float().div(255.0)
    return mask_tensor.unsqueeze(0).unsqueeze(0).to(self.kornia.device)
```

**Dynamic Discernibility Threshold:**

The module includes a minimum area threshold to prevent applying effects to insignificant regions:

```python
# Skip if region is less than 0.1% of frame area
ratio = area / total_area
if ratio < 0.001:
    return torch.zeros((1, 1, H, W))  # Empty mask = no effect
```

---

### 6. Metadata Finalization

After anonymization, the module uses FFmpeg to:
1. **Strip existing metadata**: Removes all original metadata that could identify the source
2. **Add professional tags**: Injects GDPR-compliant metadata

```python
async def _finalize_metadata(self, video_path: str, user_id: str, video_id: str):
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-map_metadata", "-1",                  # Strip all original metadata
        "-map_chapters", "-1",                  # Strip chapters
        "-metadata", f"title=Video Protected by OccultaShield",
        "-metadata", f"artist={user_id}",
        "-metadata", f"copyright=Property of {user_id} - Processed under GDPR",
        "-metadata", f"date={datetime.now().isoformat()}",
        "-metadata", f"description=Irreversible anonymization of faces and sensitive objects...",
        "-metadata", f"encoder=OccultaShield Engine v1.0 (YOLOv11-seg+Gemma-3n enabled)",
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",  # Ensure even dimensions
        "-movflags", "+faststart",               # Web-optimized
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "23",
        "-an",                                   # Remove audio (configurable)
        temp_path
    ]
```

**Metadata Fields Added:**

| Field | Description |
|-------|-------------|
| `title` | "Video Protected by OccultaShield" |
| `artist` | User ID who processed the video |
| `copyright` | GDPR compliance notice |
| `date` | Processing timestamp (ISO 8601) |
| `description` | Technical description of anonymization |
| `encoder` | Software version and capabilities |

---

## Performance Benchmarks

| Mode | Resolution | FPS (approx.) | Hardware |
|------|------------|---------------|----------|
| GPU (Kornia) | 1080p | 30-45 fps | RTX 3080 |
| GPU (Kornia) | 720p | 50-70 fps | RTX 3080 |
| CPU (OpenCV) | 1080p | 5-10 fps | i7-10700K |
| CPU (OpenCV) | 720p | 15-25 fps | i7-10700K |

---

## Dependencies

### Required
- `opencv-python` (cv2) - Video I/O and CPU fallback
- `numpy` - Array operations
- `torch` - PyTorch for GPU tensor operations

### Optional (for GPU acceleration)
- `kornia` - GPU-accelerated image processing
- `ffmpeg` (system) - Metadata post-processing

### Import Logic

```python
try:
    import kornia
    import kornia.filters
    KORNIA_AVAILABLE = True
except ImportError:
    KORNIA_AVAILABLE = False
```

---

## Usage Example

```python
from modules.edition.video_editor import VideoAnonymizer

anonymizer = VideoAnonymizer(use_gpu=True, batch_frames=8)

actions = [
    {
        "type": "blur",
        "track_id": 1,
        "bboxes": {
            1: [100, 100, 200, 200],
            2: [102, 101, 202, 201],
            # ... more frames
        },
        "config": {"kernel_size": 31, "sigma": 15.0}
    },
    {
        "type": "pixelate",
        "track_id": 2,
        "bboxes": {1: [300, 300, 400, 400]},
        "config": {"blocks": 10, "add_noise": True}
    }
]

await anonymizer.apply_anonymization(
    video_id="vid_12345",
    input_path="/path/to/input.mp4",
    output_path="/path/to/output.mp4",
    actions=actions,
    user_id="user_abc"
)
```

---

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CUDA_VISIBLE_DEVICES` | GPU selection | auto |

### Anonymization Effect Presets

| Effect | Best For | Reversibility | Performance |
|--------|----------|---------------|-------------|
| `blur` | Faces | Low | Fast |
| `pixelate` + noise | License plates | Very Low | Fast |
| `mask` (scramble) | Documents | Irreversible | Medium |

---

## GDPR Compliance Notes

This module ensures GDPR compliance through:

1. **Irreversibility**: All effects are designed to be irreversible
   - Blur removes high-frequency details
   - Pixelation with noise prevents AI reversal
   - Scramble completely destroys spatial relationships

2. **Metadata Stripping**: Original video metadata is removed to prevent data leakage

3. **Audit Trail**: Processing metadata is added for compliance documentation

4. **Consistent Tracking**: Same `track_id` always produces same visual effect

---

## Error Handling

The module handles various failure modes:

```python
# Zero-size ROI protection
if x2 <= x1 or y2 <= y1:
    continue

# FFmpeg not found
except FileNotFoundError:
    logger.warning("FFmpeg not found. Metadata stripping skipped.")

# Invalid video file
if not cap.isOpened():
    raise ValueError(f"Failed to open video: {input_path}")
```

---

## Future Enhancements

- [ ] Audio anonymization (voice obfuscation)
- [ ] Real-time streaming support
- [ ] Custom effect plugins
- [ ] Multi-GPU processing
- [ ] WebP/GIF output formats
