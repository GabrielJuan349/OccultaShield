# Plan de Implementación: Corrección de Dimensiones Cero en Blur de Kornia

## Análisis del Problema
El sistema falla en la anonimización con `RuntimeError: Expected 3D or 4D ... got: [1, 3, 0, 823]`.
Esto indica que se está intentando aplicar un difuminado (blur) sobre una región de interés (ROI) que tiene una altura de 0 píxeles.

**Causas Posibles:**
1.  Coordenadas de Bounding Box (`bbox`) donde `y1 == y2` o `x1 == x2`.
2.  Desbordamiento de coordenadas fuera de la imagen que, al ser recortadas (`clamp`), resultan en un tamaño cero.
3.  Interpolación incorrecta de `interpolate_bboxes` que genera coordenadas colapsadas.

En el método `_process_batch_gpu` de `backend/app/modules/edition/video_editor.py` (Línea ~319), extraemos el `bbox` pero no validamos si tiene un área positiva válida antes de pasarlo a `kornia_effects.blur_region`.

La función `_apply_effect_cpu` (Línea 385) sí tiene esta validación:
```python
if x2 <= x1 or y2 <= y1: return
```
Pero la implementación GPU (`_process_batch_gpu`) carece de ella.

## Solución Propuesta
Implementar validaciones robustas en el bucle de procesamiento GPU para descartar regiones inválidas antes de llamar a Kornia.

### Pasos de Implementación

#### 1. Modificar `_process_batch_gpu` en `video_editor.py`
Ubicación: `backend/app/modules/edition/video_editor.py`, alrededor de la línea 320.

**Lógica a insertar:**
-   Al obtener el `bbox` crudo (x1, y1, x2, y2), validar los límites `[0, W]` y `[0, H]`.
-   Calcular ancho y alto efectivos.
-   Si `width < 1` o `height < 1`, descartar la acción para ese frame y continuar (skipear).

```python
# Lógica conceptual
H, W = tensor.shape[2], tensor.shape[3]
x1, y1, x2, y2 = bbox
# Clamping
x1 = max(0, min(x1, W))
y1 = max(0, min(y1, H))
x2 = max(0, min(x2, W))
y2 = max(0, min(y2, H))

# Validar integridad
if x2 <= x1 or y2 <= y1:
    continue # Skip this invalid region
```

#### 2. Modificar `KorniaEffects.blur_region` (Defensa en Profundidad)
Ubicación: `backend/app/modules/edition/video_editor.py`, línea ~66.

Aunque filtremos antes, es buena práctica que la función de bajo nivel también se proteja.
-   Si la ROI tiene tamaño 0, devolver el tensor original sin cambios.

```python
# check dimensions
if roi.shape[2] == 0 or roi.shape[3] == 0:
    return tensor
```

## Archivos Afectados
-   `backend/app/modules/edition/video_editor.py`

## Resultado Esperado
El proceso de anonimización continuará ignorando los frames/bbox defectuosos en lugar de crashear todo el pipeline.
