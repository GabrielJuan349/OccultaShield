# Detection Models - OccultaShield

## Architecture Overview

OccultaShield uses a **Hybrid Detection System** managed by `HybridDetectorManager`, which automatically selects the optimal strategy based on available GPU resources.

## Current Detection Stack

| Type | Model | Technology | Status | Accuracy |
|------|--------|------------|--------|-----------|
| **People** | YOLO11n-seg | Ultralytics + Segmentation | ✅ Active | High (precise silhouettes) |
| **Faces** | Kornia FaceDetector | YuNet DNN + GPU Acceleration | ✅ Active | High |
| **Faces (Fallback)** | OpenCV Haar Cascade | CPU-based | ⚠️ Backup | Medium |
| **Vehicles/Plates** | YOLOv8n | COCO classes proxy | ⚠️ Proxy | Medium |

## GPU Management System

### GPUManager Singleton

The `GPUManager` class automatically detects available VRAM and selects the optimal strategy:

| VRAM | Strategy | Model Size | Batch Size |
|------|----------|------------|------------|
| < 8GB | Sequential | Nano | 8 |
| 8-16GB | Parallel | Small | 32 |
| 16-32GB | Parallel | Medium | 64 |
| 32GB+ (DGX Spark) | Parallel | Medium | up to 128 |

```python
# Automatic strategy selection
from modules.detection.gpu_manager import gpu_manager

strategy, model_size, batch_size = gpu_manager.get_strategy()
# Example: ("parallel", "medium", 128) on DGX Spark
```

## Model Configurations

### YOLO Configurations (in `detector.py`)

```python
YOLO_CONFIGS = {
    "nano": {
        "model_file": "yolo11n-seg.pt",
        "vram_mb": 500,
        "description": "Fast, lower accuracy"
    },
    "small": {
        "model_file": "yolo11s-seg.pt", 
        "vram_mb": 800,
        "description": "Balanced speed/accuracy"
    },
    "medium": {
        "model_file": "yolo11m-seg.pt",
        "vram_mb": 1500,
        "description": "High accuracy, slower"
    }
}
```

### Kornia Face Detection

The system prioritizes **Kornia FaceDetector (YuNet)** for GPU-accelerated face detection:

```python
# Kornia YuNet - GPU optimized
self.kornia_face_detector = FaceDetector(
    model_path=None  # Uses bundled YuNet model
)

# Fallback: OpenCV Haar Cascade (CPU)
self.haar_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)
```

## Detection Thresholds

### Area Thresholds

```python
MIN_DETECTION_AREA = 500     # Minimum pixels² for any detection
FACE_AREA_THRESHOLD = 200    # Minimum pixels² for face detection
```

### Confidence Thresholds (from `detection.yaml`)

```yaml
confidence_threshold: 0.5    # 50% minimum confidence
iou_threshold: 0.45          # NMS overlap threshold
```

## Tracking System

### Kalman Filter Tracker

The `ObjectTracker` class uses **Hungarian Algorithm** with **Kalman Filter** for smooth tracking:

```python
# State vector: [x1, y1, x2, y2, vx1, vy1, vx2, vy2]
# Predicts position + velocity for stable tracking

tracker = ObjectTracker(
    iou_threshold=0.3,   # Association threshold
    max_age=1000,        # Track survives practically forever
    min_hits=0           # Immediate confirmation
)
```

**Key Features:**
- **Immediate Track Confirmation**: `min_hits=0` means detections are tracked from first frame
- **Persistent Tracks**: `max_age=1000` keeps tracks alive even with temporary occlusions
- **Velocity Damping**: Reduces velocity influence when age increases (uncertainty)

## License Plate Detection Enhancement

### Current Behavior (Vehicle Proxy)

```python
vehicle_classes = [
    2,  # car
    3,  # motorcycle
    5,  # bus
    7   # truck
]
```

### Option 1: Pre-trained Roboflow Model

```bash
# Download specialized model from Roboflow
cd backend/app/modules/detection/models/
wget https://app.roboflow.com/ds/xxxxx -O license_plate_detector.pt
```

### Option 2: Hugging Face Model

```python
from transformers import AutoModelForObjectDetection
model = AutoModelForObjectDetection.from_pretrained(
    "nickmuchi/yolos-small-finetuned-license-plate-detection"
)
```

### Option 3: Fine-tune YOLOv8

```python
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
model.train(
    data='license_plates.yaml',
    epochs=50,
    imgsz=640,
    device='0'
)
```

## Batch Processing

### Frame Batch Processing

```python
def _detect_batch(self, frames: List[np.ndarray], frame_indices: List[int]):
    """Process multiple frames in parallel for GPU efficiency."""
    
    # Batch YOLO inference
    yolo_results = self.person_model(
        frames,
        conf=self.confidence,
        iou=self.iou_threshold,
        device=self.device,
        verbose=False
    )
    
    # Parallel face detection with Kornia
    for i, frame in enumerate(frames):
        faces = self._detect_faces_kornia(frame)
        # ...
```

### GPU Memory Optimization

- **Explicit VRAM Release**: After each video processing
- **Batch Size Calculation**: Based on available VRAM
- **Safety Margin**: 20% buffer when checking model fit

## Sensitive Content Classification

The system can also detect **non-person** sensitive content using the LLM:

```python
SENSITIVE_CONTENT_TYPES = [
    "fingerprint",      # Visible ridge patterns
    "id_document",      # Passports, IDs, licenses
    "credit_card",      # Bank cards with visible numbers
    "signature",        # Handwritten signatures
    "hand_biometric"    # Palm print recognition
]
```

## Performance Metrics

### NVIDIA DGX Spark GPU (128GB VRAM)

- **Batch Size**: Up to 128 frames per batch
- **FPS**: ~25-30 FPS in detection
- **GPU Memory**: 2-4 GB per video (auto-released)

### Standard GPU (8-16GB)

- **Batch Size**: 16-32 frames
- **FPS**: ~15-20 FPS
- **Fallback**: CPU mode if CUDA unavailable

## Example Logs

```
🚀 [GPU] DGX Spark mode: 128GB VRAM, batch_size=128

✓ YOLO person detector loaded: yolo11n-seg.pt
✓ Kornia FaceDetector (YuNet) loaded
✓ YOLO vehicle detector loaded as plate fallback: yolov8n.pt
⚠️  Using vehicle detection as plate proxy. For better plate detection, provide a specialized model.

HybridDetectorManager: strategy=batch, size=nano, device=cuda:0, kornia_face=True

[TRACKER] Initialized: iou_threshold=0.3, max_age=1000, min_hits=0
[DETECTOR] Batch 94 frames in 3.73s (25.2 FPS): 12 persons, 5 faces, 3 plates
```

## Known Issues & Solutions

### 1. Person Detection Fails in Low Light

```python
# Reduce confidence threshold
person_confidence = 0.3  # More detections, more false positives

# Or use larger model
person_model = "yolo11m-seg.pt"
```

### 2. Face Detection Fails

The system automatically falls back to OpenCV Haar Cascade if Kornia fails:

```python
if not faces_detected and self.haar_cascade:
    faces = self._detect_faces_haar(frame)  # CPU fallback
```

### 3. Duplicate Detections

```python
# Adjust tracker IOU threshold
tracker.iou_threshold = 0.4  # Stricter matching
```

## References

- **YOLO11**: https://docs.ultralytics.com/models/yolo11/
- **Kornia**: https://kornia.readthedocs.io/
- **OpenCV DNN**: https://docs.opencv.org/master/d2/d58/tutorial_table_of_content_dnn.html
- **Hungarian Algorithm**: https://en.wikipedia.org/wiki/Hungarian_algorithm
