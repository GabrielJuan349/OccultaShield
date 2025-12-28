# Notebooks de Testing - OccultaShield Backend

Esta carpeta contiene notebooks para probar los módulos del backend de forma aislada.

## Requisitos

Asegúrate de tener instaladas las dependencias del proyecto y `jupyter`/`notebook`.

```bash
pip install jupyter matplotlib ipykernel nest_asyncio
```

## Configuración Previa

1.  **Modelo YOLO**: Asegúrate de tener `yolov10m.pt` (o el que uses) en `backend/app/`.
2.  **Video de Prueba**: Coloca un video mp4 en `backend/storage/uploads/` (ej. `coche.mp4`) o actualiza la variable `VIDEO_PATH` en el notebook.

## Notebooks

### 1. [01_detection_module.ipynb](./01_detection_module.ipynb)
Prueba el detector YOLO y el tracking.
- **Input**: Video local.
- **Output**: Información de tracks y recortes de detecciones en `storage/captures/notebook_test`.

### 2. [02_edition_module.ipynb](./02_edition_module.ipynb)
Prueba la anonimización de video.
- **Input**: Video local.
- **Output**: Video modificado con blur/pixelado.

### 3. [03_verification_module.ipynb](./03_verification_module.ipynb)
Prueba el análisis GDPR (RAG + LLM).
- **Input**: Imágenes recortadas (capturas).
- **Output**: Reporte de violaciones.

### 4. [04_full_pipeline.ipynb](./04_full_pipeline.ipynb)
Corre todo el flujo en secuencia sin levantar el servidor API.

## Ejecución

Desde la carpeta `backend/app`:

```bash
jupyter notebook notebooks/
```
