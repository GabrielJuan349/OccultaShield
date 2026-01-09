# 🛡️ OccultaShield General Execution Guide

This guide provides a comprehensive overview of how to set up and run the entire OccultaShield ecosystem, including the **Angular v21 (Zoneless)** frontend, the **FastAPI (YOLOv11 Precision)** backend, and the necessary databases.

---

## 🏗️ Architecture Overview

OccultaShield is a high-precision video anonymization platform designed for GDPR compliance. It uses a **"Human-in-the-Loop"** workflow:
1.  **AI Analysis (YOLOv11-seg)**: Detects subjects and silhouettes with polygonal precision.
2.  **Legal Reasoning (Neo4j RAG)**: Validates detections against GDPR articles.
3.  **Human Review**: Users confirm or modify anonymization actions.
4.  **GPU-Accelerated Editing (Kornia)**: Applies precise masks to the final video.

---

## 📋 Prerequisites

### System Requirements
*   **OS**: Windows/Linux (Windows used for development).
*   **Python**: 3.10+
*   **Node.js**: 20+ (with Bun recommended).
*   **GPU**: NVIDIA GPU (Optional, but highly recommended for YOLOv11 and Kornia).

### Global Dependencies
*   **SurrealDB**: Application state and tracking history.
*   **Neo4j**: GDPR knowledge base and Article RAG.

---

## 🚀 Quick Start (Step-by-Step)

### 1. Database Setup
Ensure both databases are running:
*   **SurrealDB**: `surreal start --user root --pass root memory`
*   **Neo4j**: Start your instance and ensure APOC/GDS are enabled.

### 2. Backend Initialization
```bash
cd backend
# Install dependencies
pip install kornia scipy pypdf ultralytics opencv-python
# Ingest GDPR data (Neo4j)
python app/modules/verification/ingest_gdpr.py path/to/gdpr.pdf
# Start Server
cd app
uvicorn main:app --host 0.0.0.0 --port 8900 --reload
```

### 3. Frontend Initialization
```bash
cd frontend
# Install dependencies
bun install
# Start App
bun run dev
```

---

## 🧪 Testing the "Precision Mode" Pipeline

1.  **Upload**: Go to `http://localhost:4200` and upload a video.
2.  **Monitor**: Watch the "Processing" page. The backend will use **YOLOv11** for instance segmentation and **Kalman Filters** to stabilize tracking.
3.  **Review**: In the "Review" page, you will see precise silhouettes. Choose your anonymization effect (Blur, Pixelate, or Mask).
4.  **Download**: Once processing is complete, download the anonymized video. The system automatically handles **Dynamic Fading** for subjects that are too small to be identifiable (Ground Truth check).

---

## 🛠️ Components Summary

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Frontend** | Angular v21 (Signals) | Modern UI with real-time SSE updates. |
| **Backend** | FastAPI / Python | Orchestration and AI pipeline. |
| **Detection** | YOLOv11-seg | Silhouette-level instance segmentation. |
| **Tracking** | Kalman Filter | Smooth object tracking for shaky/drone shots. |
| **Verification** | Neo4j / LLM | Legal compliance analysis (GDPR). |
| **Database** | SurrealDB | Tracking history and execution state. |

---

## 🔍 Troubleshooting
*   **First Run Delay**: The backend will download `yolo11n-seg.pt` (approx 10MB) on the first upload.
*   **Memory Issues**: If not using a GPU, processing will fallback to CPU (OpenCV), which is significantly slower.
*   **SSE Sync**: If the UI hangs, check if the Backend terminal shows active logs for `video_processor`.
