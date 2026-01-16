<div align="center">

# 🛡️ OccultaShield Backend

### AI-Powered Video Anonymization Engine with Legal Graphs

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Kornia](https://img.shields.io/badge/Kornia-Enabled-orange?style=for-the-badge)](https://kornia.readthedocs.io/)
[![SurrealDB](https://img.shields.io/badge/SurrealDB-2.0-FF00A0?style=for-the-badge)](https://surrealdb.com/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-008CC1?style=for-the-badge&logo=neo4j)](https://neo4j.com/)

**Surgical privacy technology combining YOLOv11, Kornia (YuNet), Kalman Tracking, and Knowledge Graphs (GraphRAG)**

</div>

---

## 📖 Detailed Description

The OccultaShield backend is the intensive processing core of the system. Designed to run on servers with GPU acceleration, this module orchestrates a complex pipeline of computer vision and legal reasoning.

### Engine Capabilities:
1.  **Intelligent Hybrid Detection**: 
    *   Uses **YOLOv11-seg** (Instance Segmentation) to obtain precise contours of pedestrians and vehicles, avoiding rectangular "black boxes" that hide irrelevant information.
    *   Integrates **Kornia FaceDetector (YuNet)** for high-fidelity face detection, capable of detecting faces as small as 10x10 pixels in dense crowds.
2.  **Temporal Tracking (MOT)**:
    *   Implements **SORT/DeepSORT** algorithms with Kalman filters to maintain identity coherence (ID) for each subject throughout the video, preventing masks from "flickering".
3.  **Legal Verification (Brain)**:
    *   It doesn't just hide; it **asks**. A RAG (Retrieval-Augmented Generation) engine queries a vector database in Neo4j with GDPR regulations to justify whether a detection is a violation.
4.  **GPU Tensor Editing**:
    *   Final rendering doesn't use classic ffmpeg for effects. It uses **direct tensor operations** on VRAM (via Kornia), applying Gaussian blurs or cryptographically secure pixelation.

---

## 🛠️ Updated Technology Stack

*   **FastAPI**: High-performance asynchronous REST API with native `asyncio` support.
*   **Package Manager**: `uv` (Rust-based) for instant dependency management.
*   **Vision**: `ultralytics` (YOLO) + `kornia` (PyTorch Vision).
*   **Data**: `SurrealDB` (Logs, Auth, Metadata) + `Neo4j` (Graph Knowledge).
*   **LLM**: Integration with Ollama/HuggingFace for legal reasoning (`verification` module).

---

## 🚀 Installation and Execution Guide

### 1. System Requirements
*   **OS**: Linux (Ubuntu 22.04+ recommended).
*   **Python**: 3.11 or higher.
*   **GPU**: NVIDIA Pascal or higher (with drivers 535+ and CUDA 12) for optimal performance.

### 2. Installation with `uv`
```bash
cd backend
# Create virtual environment and install dependencies (including torch and kornia)
uv sync
```

### 3. Environment Configuration (`.env`)
It is critical to properly configure environment variables for connecting to models and databases.

```bash
cd app
cp .env.example .env
nano .env
```
**Key Variables:**
*   `DETECTION_MODEL_PATH`: Path to YOLO model (e.g., `yolo11n-seg.pt`).
*   `NEO4J_URI` / `NEO4J_PASSWORD`: Legal Graph credentials.
*   `SURREALDB_URL`: SurrealDB connection URL (usually `ws://localhost:8000/rpc`).

### 4. Data Initialization
Before processing, load the initial legal knowledge:
```bash
# Activate the environment
source .venv/bin/activate
# Ingest the GDPR PDF into Neo4j
python app/modules/verification/ingest_gdpr.py path/to/gdpr.pdf
```

### 5. Start the Server
```bash
# Development mode with hot reload
cd app
uvicorn main:app --host 0.0.0.0 --port 8980 --reload
```
*   **Swagger API Docs**: `http://localhost:8980/docs`
*   **Health Endpoint**: `http://localhost:8980/api/v1/health`

---

## 📂 Module Organization (Architecture Map)

*   `app/modules/detection/`: 
    *   `detector.py`: Hybrid orchestrator (YOLO + Kornia).
    *   `tracker.py`: Kalman Filter logic.
*   `app/modules/verification/`:
    *   `rag_engine.py`: Interface with Neo4j and LLM.
    *   `legal_brain.py`: Compliance decision logic.
*   `app/modules/edition/`:
    *   `video_editor.py`: Tensor-based renderer (Kornia).
*   `app/api/v1/`: REST Routes and Websockets (SSE).

---

## ⚠️ Performance Notes
*   **Kornia**: The system will automatically try to use CUDA. If you see "Falling back to CPU" logs, verify your PyTorch installation.
*   **Models**: The first run will download several GB of weights (YOLO, Embeddings, YuNet). Ensure you have a good connection.
