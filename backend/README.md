<div align="center">

# 🛡️ OccultaShield Backend

### Motor de Anonimización de Video Impulsado por IA y Grafos Legales

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Kornia](https://img.shields.io/badge/Kornia-Enabled-orange?style=for-the-badge)](https://kornia.readthedocs.io/)
[![SurrealDB](https://img.shields.io/badge/SurrealDB-2.0-FF00A0?style=for-the-badge)](https://surrealdb.com/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-008CC1?style=for-the-badge&logo=neo4j)](https://neo4j.com/)

**Tecnología de privacidad quirúrgica que combina YOLOv11, Kornia (YuNet), Rastreo Kalman y Grafos de Conocimiento (GraphRAG)**

</div>

---

## 📖 Descripción Detallada

El backend de OccultaShield es el núcleo de procesamiento intensivo del sistema. Diseñado para ejecutarse en servidores con aceleración GPU, este módulo orquesta un pipeline complejo de visión artificial y razonamiento legal.

### Capacidades del Motor:
1.  **Detección Híbrida Inteligente**: 
    *   Utiliza **YOLOv11-seg** (Instance Segmentation) para obtener contornos precisos de peatones y vehículos, evitando las "cajas negras" rectangulares que ocultan información irrelevante.
    *   Integra **Kornia FaceDetector (YuNet)** para la detección de rostros de alta fidelidad, capaz de detectar caras de hasta 10x10 píxeles en multitudes densas.
2.  **Rastreo Temporal (MOT)**:
    *   Implementa algoritmos de **SORT/DeepSORT** con filtros de Kalman para mantener la coherencia de identidad (ID) de cada sujeto a lo largo del video, evitando que las máscaras "parpadeen".
3.  **Verificación Legal (Brain)**:
    *   No se limita a ocultar; **pregunta**. Un motor RAG (Retrieval-Augmented Generation) consulta una base de datos vectorial en Neo4j con el reglamento RGPD para justificar si una detección es una infracción.
4.  **Edición Tensorial en GPU**:
    *   El renderizado final no usa ffmpeg clásico para los efectos. Utiliza **operaciones tensoriales directas** sobre la VRAM (vía Kornia), aplicando desenfoques Gaussianos o pixelados criptográficamente seguros.

---

## 🛠️ Stack Tecnológico Actualizado

*   **FastAPI**: API REST asíncrona de alto rendimiento con soporte nativo para `asyncio`.
*   **Gestor de Paquetes**: `uv` (Rust-based) para una gestión de dependencias instantánea.
*   **Visión**: `ultralytics` (YOLO) + `kornia` (PyTorch Vision).
*   **Datos**: `SurrealDB` (Logs, Auth, Metadata) + `Neo4j` (Graph Knowledge).
*   **LLM**: Integración con Ollama/HuggingFace para el razonamiento legal (módulo `verification`).

---

## 🚀 Guía de Instalación y Ejecución

### 1. Requisitos del Sistema
*   **OS**: Linux (Ubuntu 22.04+ recomendado).
*   **Python**: 3.11 o superior.
*   **GPU**: NVIDIA Pascal o superior (con drivers 535+ y CUDA 12) para rendimiento óptimo.

### 2. Instalación con `uv`
```bash
cd backend
# Crear entorno virtual e instalar dependencias (incluyendo torch y kornia)
uv sync
```

### 3. Configuración del Entorno (`.env`)
Es crítico configurar correctamente las variables de entorno para la conexión con los modelos y bases de datos.

```bash
cd app
cp .env.example .env
nano .env
```
**Variables Clave:**
*   `DETECTION_MODEL_PATH`: Ruta al modelo YOLO (ej: `yolo11n-seg.pt`).
*   `NEO4J_URI` / `NEO4J_PASSWORD`: Credenciales del Grafo Legal.
*   `SURREALDB_URL`: URL de conexión a SurrealDB (normalmente `ws://localhost:8000/rpc`).

### 4. Inicialización de Datos
Antes de procesar, carga el conocimiento legal inicial:
```bash
# Activa el entorno
source .venv/bin/activate
# Ingesta el PDF del RGPD en Neo4j
python app/modules/verification/ingest_gdpr.py path/to/gdpr.pdf
```

### 5. Iniciar el Servidor
```bash
# Modo desarrollo con recarga en caliente
cd app
uvicorn main:app --host 0.0.0.0 --port 8980 --reload
```
*   **Swagger API Docs**: `http://localhost:8980/docs`
*   **Endpoint Health**: `http://localhost:8980/api/v1/health`

---

## 📂 Organización de Módulos (Architecture Map)

*   `app/modules/detection/`: 
    *   `detector.py`: Orquestador híbrido (YOLO + Kornia).
    *   `tracker.py`: Lógica de Kalman Filter.
*   `app/modules/verification/`:
    *   `rag_engine.py`: Interfaz con Neo4j y LLM.
    *   `legal_brain.py`: Lógica de decisión de compliance.
*   `app/modules/edition/`:
    *   `video_editor.py`: Renderizador basado en tensores (Kornia).
*   `app/api/v1/`: Rutas REST y Websockets (SSE).

---

## ⚠️ Notas de Rendimiento
*   **Kornia**: El sistema intentará usar CUDA automáticamente. Si ves logs de "Falling back to CPU", verifica tu instalación de PyTorch.
*   **Modelos**: La primera ejecución descargará varios GB de pesos (YOLO, Embeddings, YuNet). Asegúrate de tener buena conexión.
