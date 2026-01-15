# Plan de Implementación: Corrección Definitiva de Kornia FaceDetector (Parsing Manual)

## Problema Crítico Confirmado
El uso de la clase auxiliar `FaceDetectorResult` de Kornia está causando fallos continuos porque la salida del modelo YuNet (tensor) tiene dimensiones o formatos que no coinciden exactamente con lo que espera esa clase (espera 14 valores, recibe tensores de forma variable como `[N, 15]` o `[N, 14]` que a veces fallan en la validación interna).

Intentar recortar el tensor `det[..., :14]` no fue suficiente o seguro, ya que la validación interna de Kornia sigue lanzando excepciones.

## Solución Técnica: Parsing Manual
En lugar de intentar ajustar el tensor para que le guste a `FaceDetectorResult`, vamos a **dejar de usar esa clase completamente**.
Parsearemos el tensor crudo directamente basándonos en la especificación de salida de YuNet.

### Estructura del Tensor de Salida (YuNet)
El tensor tiene la forma `[N, 14]` o `[N, 15]`.
Los índices clave son:
-   `0`: x1 (top-left x)
-   `1`: y1 (top-left y)
-   `2`: w (ancho)
-   `3`: h (alto)
-   `...`: landmarks (ojos, nariz, boca - índices 4-12)
-   `13`: score (confianza)

### Cambios Requeridos en `backend/app/modules/detection/detector.py`

Reemplazar todo el bloque `try-except` que usa `FaceDetectorResult` con lógica de extracción directa de tensores.

#### Algoritmo de Extracción Propuesto:
```python
# 1. Validar que hay detecciones
if det.numel() == 0:
    continue

# 2. Extracción vectorizada o por lista de índices conocidos
# Asumimos que el score está en el índice 13 y el bbox en 0-3
x1_list = det[:, 0].int().tolist()
y1_list = det[:, 1].int().tolist()
w_list = det[:, 2].int().tolist()
h_list = det[:, 3].int().tolist()
scores_list = det[:, 13].tolist() # El score suele ser el último o posición 13

# 3. Iterar y crear BoundingBox
for i, score in enumerate(scores_list):
    if score >= self.face_confidence:
        x1 = float(x1_list[i])
        y1 = float(y1_list[i])
        x2 = float(x1 + w_list[i])
        y2 = float(y1 + h_list[i])
        
        bbox = BoundingBox(x1, y1, x2, y2, float(score), frame_num)
        
        # Mantener umbral de área ajustado (200)
        if bbox.area >= 200:
             results.append(("face", bbox))
```

## Ventajas
1.  **Robustez**: No dependemos de validaciones estrictas de versiones específicas de Kornia.
2.  **Flexibilidad**: Si el modelo devuelve 15 valores (un campo extra irrelevante), nuestro código lo ignora y sigue funcionando siempre que los índices 0-3 y 13 sean correctos.

## Archivos Afectados
-   `backend/app/modules/detection/detector.py`: Métodos `detect_faces_kornia` y `detect_all`.
