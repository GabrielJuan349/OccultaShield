# Modelos de Detección - OccultaShield

## Estado Actual

El sistema detecta **simultáneamente** tres tipos de objetos sensibles:

| Tipo | Modelo | Estado | Precisión |
|------|--------|--------|-----------|
| **Personas** | YOLO11n-seg | ✅ Activo | Alta (segmentación incluida) |
| **Caras** | Kornia FaceDetector (YuNet) | ✅ Activo | Alta |
| **Vehículos/Placas** | YOLOv8n (fallback) | ⚠️ Proxy | Media (detecta vehículos, no placas específicas) |

## Mejora de Detección de Placas

### Opción 1: Modelo Pre-entrenado de Roboflow

```bash
# Descargar modelo especializado de Roboflow
cd backend/app/modules/detection/models/
wget https://app.roboflow.com/ds/xxxxx -O license_plate_detector.pt

# Actualizar configuración
# En detector.py, línea 94, cambiar:
plate_model = "modules/detection/models/license_plate_detector.pt"
```

### Opción 2: Modelo de Hugging Face

```bash
# Instalar transformers
uv add transformers

# Usar modelo pre-entrenado
from transformers import AutoImageProcessor, AutoModelForObjectDetection
model = AutoModelForObjectDetection.from_pretrained("nickmuchi/yolos-small-finetuned-license-plate-detection")
```

### Opción 3: Fine-tune YOLOv8

```python
# Entrenar con dataset de placas
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
model.train(
    data='license_plates.yaml',  # Dataset YAML
    epochs=50,
    imgsz=640,
    device='0'  # GPU
)
```

## Datasets Recomendados para Placas

1. **CCPD (Chinese City Parking Dataset)**: 250k imágenes
   - https://github.com/detectRecog/CCPD

2. **OpenALPR Benchmark**: Dataset europeo
   - https://github.com/openalpr/benchmarks

3. **Roboflow Universe - License Plates**
   - https://universe.roboflow.com/search?q=license+plate

## Configuración Actual

### Clases COCO Detectadas (vehículos como proxy)

```python
vehicle_classes = [
    2,  # car
    3,  # motorcycle
    5,  # bus
    7   # truck
]
```

### Umbrales de Confianza

```python
face_confidence = 0.5      # 50% confianza mínima para caras
person_confidence = 0.5    # 50% confianza mínima para personas
MIN_DETECTION_AREA = 500   # Área mínima (píxeles²)
```

## Cómo Cambiar los Modelos

### En `video_processor.py`

```python
self.detector = VideoDetector(
    person_model="yolo11n-seg.pt",  # Cambiar modelo de personas
    plate_model="license_plate_detector.pt",  # Modelo especializado de placas
    confidence_threshold=0.5
)
```

### Modelos Disponibles

**YOLO Personas** (con segmentación):
- `yolo11n-seg.pt` - Nano (rápido, menos preciso)
- `yolo11s-seg.pt` - Small (balanceado)
- `yolo11m-seg.pt` - Medium (preciso, más lento)

**YOLO Genérico**:
- `yolov8n.pt` - Nano (80 clases COCO)
- `yolov8s.pt` - Small
- `yolov8m.pt` - Medium

## Problemas Conocidos

### 1. Detección de Personas Falla Ocasionalmente

**Causa**: Oclusiones, ángulos difíciles, iluminación baja

**Solución**:
```python
# Reducir threshold
person_confidence = 0.3  # Más detecciones, más falsos positivos

# Usar modelo más grande
person_model = "yolo11m-seg.pt"  # Más preciso
```

### 2. Placas No Se Detectan

**Causa**: YOLOv8 estándar no está entrenado para placas

**Solución**: Usar modelo especializado (ver Opción 1, 2 o 3 arriba)

### 3. Múltiples Detecciones del Mismo Objeto

**Causa**: Tracker puede perder objetos entre frames

**Solución**:
```python
# En tracker.py, ajustar IOU threshold
self.iou_threshold = 0.3  # Más estricto (menos duplicados)
```

## Rendimiento

### GPU NVIDIA DGX Spark

- **Batch Size**: Ajustado automáticamente según VRAM
- **FPS**: ~25-30 FPS en detección (con batch processing)
- **Memoria GPU**: ~2-4 GB por video (liberada automáticamente)

### Optimizaciones

1. **Batch Processing**: Procesa múltiples frames simultáneamente
2. **GPU Memory Management**: Libera explícitamente después de cada video
3. **Parallel Detection**: Personas, caras y placas en paralelo

## Logs de Ejemplo

```
✓ YOLO person detector loaded: yolo11n-seg.pt
✓ Kornia FaceDetector (YuNet) loaded
✓ YOLO vehicle detector loaded as plate fallback: yolov8n.pt
⚠️  Using vehicle detection as plate proxy. For better plate detection, provide a specialized model.

HybridDetectorManager: strategy=batch, size=nano, device=cuda:0, kornia_face=True

[DETECTOR] Batch 94 frames in 3.73s (25.2 FPS): 12 persons, 5 faces, 3 plates
```

## Referencias

- **YOLO11**: https://docs.ultralytics.com/models/yolo11/
- **Kornia**: https://kornia.readthedocs.io/
- **License Plate Detection**: https://github.com/topics/license-plate-detection
