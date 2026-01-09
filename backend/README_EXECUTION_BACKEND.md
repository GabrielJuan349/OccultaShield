# 🚀 Guía de Ejecución y Pruebas del Backend (OccultaShield)

Esta guía detalla los pasos necesarios para levantar el backend, configurar las bases de datos y realizar una prueba completa del pipeline **"Human-in-the-Loop"** con la nueva tecnología de segmentación **YOLOv11 Precision**.

---

## 📋 Requisitos Previos

### 1. Dependencias adicionales
Asegúrate de tener instaladas estas librerías que se han añadido durante la migración (incluyendo YOLOv11 y herramientas de tracking):
```bash
pip install kornia scipy pypdf ultralytics opencv-python
```

### 2. Bases de Datos
Necesitas dos bases de datos funcionando localmente:

*   **SurrealDB** (Persistencia de aplicación):
    ```bash
    surreal start --log debug --user root --pass root memory # Para pruebas rápidas en memoria
    ```
    *   Endpoint por defecto: `http://localhost:8000`

*   **Neo4j** (Conocimiento legal GDPR):
    *   Tener Neo4j Desktop o un contenedor de Docker.
    *   Habilitar APOC y GDS (opcional, pero recomendado).
    *   Endpoint por defecto: `bolt://localhost:7687`
    *   Contraseña recomendada: `Occultashield_neo4j` (configurada en scripts).

---

## 🛠️ Configuración Inicial

### 1. Ingesta de Datos GDPR (Neo4j)
Antes de procesar videos, el "cerebro legal" debe estar cargado.
1. Coloca un PDF del reglamento GDPR en una ruta conocida.
2. Ejecuta el script de ingesta:
   ```bash
   python app/modules/verification/ingest_gdpr.py path/to/your/gdpr.pdf
   ```
   *Esto creará los nodos `GDPRArticle` y los índices vectoriales.*

### 2. Variables de Entorno
Crea o actualiza el archivo `backend/app/.env`:
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=Occultashield_neo4j
SURREAL_URL=http://localhost:8000
DETECTION_MODEL_PATH=yolo11n-seg.pt
```

---

## 🏃 Ejecución del Servidor

Levanta el servidor FastAPI:
```bash
cd backend/app
uvicorn main:app --host 0.0.0.0 --port 8900 --reload
```

---

## 🧪 Pasos para probar el Pipeline Completo (Precision Mode)

Sigue este flujo para verificar que todo funciona con la nueva arquitectura de segmentación:

### FASE 1: Subida y Análisis de Precisión (IA)
1.  **Subir Video**: Usa un cliente como Postman o el Swagger (`http://localhost:8900/docs`).
    *   `POST /api/v1/video/upload`
    *   Body: `file` (tu video)
    *   Response: `video_id` (ej. `vid_123`)
    *   **Nota**: En la primera ejecución, el sistema descargará automáticamente el modelo `yolo11n-seg.pt`.
2.  **Monitorear Progreso (SSE)**:
    *   Abre un navegador en: `http://localhost:8900/api/v1/process/vid_123/progress`
    *   Verás eventos de `phase_change` (detecting -> verifying).
    *   **Novedad**: El sistema ahora detecta **siluetas exactas** (segmentación) y aplica un **Filtro de Kalman** para estabilizar el rastreo en videos con movimiento (drones, cámaras en mano).

### FASE 2: Revisión (Humana)
1.  **Obtener Vulnerabilidades**:
    *   `GET /api/v1/video/vid_123/violations`
    *   Este JSON contendrá las detecciones con sus respectivas máscaras de segmentación.
2.  **Enviar Decisiones**:
    *   `POST /api/v1/video/vid_123/decisions`
    *   Body: Lista de objetos con `verification_id` y `action` (`blur`, `pixelate`, `mask` o `no_modify`).

### FASE 3: Anonimización de Precisión y Fading Dinámico
1.  **Procesamiento Final**:
    *   El backend aplica los efectos **solo sobre la silueta detectada**.
    *   **Umbral de Discernibilidad**: Si un sujeto está demasiado lejos (área < 0.1%), el sistema desvanece automáticamente la máscara para preservar la estética del paisaje, cumpliendo con el criterio de "identificabilidad" del RGPD.
2.  **Descargar**:
    *   `GET /api/v1/video/vid_123/download`

---

## 🔍 Verificación de Componentes
*   **SurrealDB**: Revisa que existen datos en las tablas:
    *   `video`, `gdpr_verification`, `detection`: Pipeline de procesamiento.
    *   `user`: Usuarios con campos `isApproved` y `role`.
    *   `app_settings`: Configuración global (ej. `closedBetaMode`).
    *   `audit_log`: Historial de acciones administrativas.
    *   `session`: Sesiones de Better-Auth.
*   **Neo4j**: Ejecuta `MATCH (n:GDPRArticle) RETURN n LIMIT 1` en el browser de Neo4j.
*   **GPU**: Vigila con `nvidia-smi`. La segmentación YOLOv11 es más intensiva que YOLOv10 pero ofrece una protección de privacidad mucho más quirúrgica.
