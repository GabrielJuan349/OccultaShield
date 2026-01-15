# Plan de Implementación: Corrección de Imágenes (404) y Rediseño de UI en ViolationCard

## Objetivo
Solucionar los errores 404 al cargar imágenes de "captures" en el frontend y mejorar significativamente la interfaz de usuario de la tarjeta de violación (`ViolationCard`) para que los detalles técnicos no se muestren como texto plano.

## Parte 1: Corrección de Imágenes (Error 404)

### Diagnóstico
Los logs muestran que el frontend intenta cargar imágenes como `.../capture/1/capture_0.jpg`. Sin embargo, `CaptureManager` guarda los archivos usando el número de frame real (ej: `capture_157.jpg`).
El endpoint `video.py` intenta leer una clave `filename` del objeto `Capture` almacenado en DB.
El modelo `Capture` (en `models.py`) tiene el campo `image_path` pero **no** tiene un campo `filename`.
Por tanto, `video.py` falla al obtener el nombre y usa el valor por defecto `'capture_0.jpg'`, que no existe físicamente, provocando el 404.

### Solución (Backend)
Modificar `backend/app/api/v1/endpoints/video.py` en la función `get_violations`:
-   En lugar de buscar `first_capture.get('filename')`, obtener `image_path`.
-   Extraer el nombre del archivo dinámicamente usando `pathlib.Path(image_path).name`.

```python
# Lógica corregida propuesta:
from pathlib import Path

# ... dentro del loop ...
image_path = first_capture.get('image_path', '')
if image_path:
    capture_filename = Path(image_path).name
else:
    capture_filename = 'capture_0.jpg' # Fallback
```

## Parte 2: Rediseño de UI (ViolationCard)

### Diagnóstico
Actualmente, la descripción se muestra como un string técnico generado por el backend (`"Violación confirmada en 6/6 frames..."`), lo cual es difícil de leer y estéticamente pobre.

### Solución (Frontend)
Rediseñar `ViolationCard.ts` y su template HTML para ignorar este string y reconstruir la información visualmente usando los datos estructurados ya disponibles (`framesAnalyzed`, `confidence`, `violatedArticles`, `severity`).

#### Cambios de Diseño Propuestos:
1.  **Sección de "Evidence" (Evidencia):**
    -   Mostrar el rango de frames verificados visualmente (ej: Icono de clip de película con "Frames: 746 - 896").
    -   Barra de confianza (Confidence Level) con color dinámico.
2.  **Sección de "Compliance" (Cumplimiento):**
    -   Listar los artículos vulnerados como "Chips" o etiquetas (ej: `[GDPR Art. 6]`, `[GDPR Art. 17]`).
    -   Añadir tooltips explicativos si es posible (future enhancement).
3.  **Eliminar Texto Plano:**
    -   Ocultar o eliminar el párrafo `<p class="description">` actual.
    -   Reemplazarlo por un grid de `kv-pairs` (Key-Value pairs) estilizados.

### Archivos Afectados
1.  `backend/app/api/v1/endpoints/video.py`: Lógica de extracción de nombre de archivo.
2.  `frontend/src/app/components/ViolationCard/ViolationCard.ts`: Template HTML y estilos CSS (si inline o archivo externo).

## Pasos de Ejecución
1.  **Backend Fix:** Aplicar el cambio en `video.py` para corregir la URL de la imagen.
2.  **Frontend Layout:** Modificar el template de `ViolationCard` para estructurar la data.
3.  **Frontend Styles:** Añadir CSS para los nuevos elementos (chips de artículos, métricas de frames).
