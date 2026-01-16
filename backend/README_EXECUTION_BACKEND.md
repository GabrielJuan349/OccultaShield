# 🚀 Backend Execution and Testing Guide (OccultaShield)

This guide details the steps required to start the backend, configure the databases, and perform a complete test of the **"Human-in-the-Loop"** pipeline with the new **Hybrid Detection System** and **Temporal Consensus Verification**.

---

## 📋 Prerequisites

### 1. Package Manager (UV)
OccultaShield uses **uv** as the Python package manager:
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
cd backend/app
uv sync
```

### 2. Databases
You need two databases running locally:

*   **SurrealDB** (Application persistence):
    ```bash
    # Quick in-memory testing
    surreal start --log debug --user root --pass root memory
    
    # Or with file persistence
    surreal start --log debug --user root --pass root file:./db_files/data.db
    ```
    *   Default endpoint: `http://localhost:8000`

*   **Neo4j** (GDPR Knowledge Graph):
    ```bash
    docker run -d \
      --name neo4j-gdpr \
      -p 7474:7474 -p 7687:7687 \
      -e NEO4J_AUTH=neo4j/Occultashield_neo4j \
      neo4j:latest
    ```
    *   Default endpoint: `bolt://localhost:7687`
    *   Web UI: `http://localhost:7474`
    *   Credentials: `neo4j / Occultashield_neo4j`

---

## 🛠️ Initial Configuration

### 1. GDPR Data Ingestion (Neo4j)
Before processing videos, load the "legal brain":
```bash
cd backend/app
./setup_gdpr.sh
```

This script loads:
- **99 GDPR articles** with full text
- **Semantic embeddings** for intelligent search
- **Detection → Article mappings** for automatic legal context
- **GDPRtEXT** official repository data
- **Kaggle datasets** (optional, if API configured)

### 2. Environment Variables
Create or update the `backend/app/.env` file:
```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=Occultashield_neo4j

# SurrealDB Configuration
SURREAL_URL=http://localhost:8000
SURREAL_USER=root
SURREAL_PASS=root
SURREAL_NAMESPACE=occultashield
SURREAL_DATABASE=main

# Detection Configuration
DETECTION_MODEL_PATH=yolo11n-seg.pt
```

---

## 🏃 Server Execution

Start the FastAPI server:
```bash
cd backend/app
uv run uvicorn main:app --host 0.0.0.0 --port 8900 --reload
```

---

## 🧪 Steps to Test the Complete Pipeline

### PHASE 1: Upload and Detection (AI)

1.  **Upload Video**: Use Swagger (`http://localhost:8900/docs`)
    *   `POST /api/v1/video/upload`
    *   Body: `file` (your video)
    *   Response: `video_id` (e.g., `vid_123`)
    *   **Note**: Models auto-download on first run (`yolo11n-seg.pt`)

2.  **Monitor Progress (SSE)**:
    ```
    http://localhost:8900/api/v1/process/vid_123/progress
    ```
    *   You'll see `phase_change` events: `detecting → verifying → ready_for_review`

### Detection Features:

| Feature | Description |
|---------|-------------|
| **GPU Auto-Detection** | `GPUManager` selects optimal batch size |
| **Batch Processing** | Up to 128 frames/batch on DGX Spark |
| **Kalman Tracking** | Stable tracking with velocity prediction |
| **Kornia Faces** | GPU-accelerated face detection (YuNet) |
| **Segmentation** | Precise silhouettes with YOLOv11-seg |

---

### PHASE 2: AI Verification (Temporal Consensus)

The system uses a **"TESTIGO VS JUEZ"** (Witness vs Judge) architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                    VERIFICATION PIPELINE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐               │
│   │ Frame 1  │     │ Frame 2  │     │ Frame N  │               │
│   └────┬─────┘     └────┬─────┘     └────┬─────┘               │
│        │                │                │                      │
│        ▼                ▼                ▼                      │
│   ┌──────────────────────────────────────────────┐             │
│   │          PARALLEL PROCESSOR                   │             │
│   │     (max_workers=4, by track_id)             │             │
│   └──────────────────────────────────────────────┘             │
│        │                                                        │
│        ▼                                                        │
│   ┌──────────────────────────────────────────────┐             │
│   │              SUB-AGENTS (TESTIGOS)            │             │
│   │    • GemmaClient: Visual description          │             │
│   │    • GraphClient: Neo4j legal context         │             │
│   └──────────────────────────────────────────────┘             │
│        │                                                        │
│        ▼                                                        │
│   ┌──────────────────────────────────────────────┐             │
│   │           CONSENSUS AGENT (JUEZ)              │             │
│   │    • Consolidates visual descriptions         │             │
│   │    • Analyzes vulnerability context           │             │
│   │    • Emits legal verdict                      │             │
│   └──────────────────────────────────────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Context Classification:**

| Vulnerable Contexts | Normal Contexts |
|---------------------|-----------------|
| `medical` | `public_space` |
| `minor` | `workplace` |
| `religious` | `commercial` |
| `political` | `recreational` |
| `intimate` | `transport` |
| `ethnic` | |

**Union-of-Evidence Rule**: ANY positive frame = violation confirmed

---

### PHASE 3: Review (Human-in-the-Loop)

1.  **Get Vulnerabilities**:
    ```
    GET /api/v1/video/vid_123/violations
    ```
    Response includes:
    - Detection bounding boxes with segmentation masks
    - Legal verdict from ConsensusAgent
    - Applicable GDPR articles
    - Recommended action (`blur`, `pixelate`, `none`)

2.  **Submit Decisions**:
    ```
    POST /api/v1/video/vid_123/decisions
    ```
    Body:
    ```json
    [
      {
        "verification_id": "ver_001",
        "action": "blur"
      },
      {
        "verification_id": "ver_002", 
        "action": "pixelate"
      }
    ]
    ```

---

### PHASE 4: Precision Anonymization (Edition)

The `VideoAnonymizer` class applies effects using **Kornia GPU acceleration**:

| Effect | Description | GPU Support |
|--------|-------------|-------------|
| `blur` | Gaussian blur on silhouette | ✅ Kornia |
| `pixelate` | Mosaic effect with noise cache | ✅ Kornia |
| `mask` | Solid color overlay | ✅ Kornia |
| `no_modify` | Skip this detection | N/A |

**Features:**
- **Batch Processing**: 8 frames default, adjustable
- **Noise Cache**: Consistent pixelation per track_id
- **Discernibility Threshold**: Auto-fade for distant subjects (<0.1% area)

---

### PHASE 5: Download

```
GET /api/v1/video/vid_123/download
```

The processed video will have:
- Precise silhouette anonymization
- Temporal consistency (no flickering)
- GDPR-compliant blur/pixelation

---

## 🔍 Component Verification

### SurrealDB Tables
```surql
SELECT * FROM video;           -- Video metadata
SELECT * FROM detection;       -- All detections
SELECT * FROM gdpr_verification;  -- AI verdicts
SELECT * FROM audit_log;       -- Processing history
```

### Neo4j Queries
```cypher
-- Count articles
MATCH (a:Article) RETURN count(a)

-- Detection → Article mappings
MATCH (d:DetectionType)-[:VIOLATES]->(a:Article)
RETURN d.type, collect(a.number) as articles

-- Semantic search
CALL db.index.fulltext.queryNodes("article_content", "biometric")
YIELD node RETURN node.number, node.title
```

---

## 📊 Performance Benchmarks

| Component | Metric | DGX Spark | Standard GPU |
|-----------|--------|-----------|--------------|
| Detection | FPS | ~25-30 | ~15-20 |
| Batch Size | Frames | 128 | 16-32 |
| Verification | Workers | 4 parallel | 2 parallel |
| Edition | Batch | 8 frames | 4 frames |

---

## 🐛 Troubleshooting

### "CUDA not available"
```bash
# Check CUDA installation
python -c "import torch; print(torch.cuda.is_available())"

# System will fallback to CPU automatically
```

### "Neo4j connection failed"
```bash
docker start neo4j-gdpr
# Or check if port 7687 is available
```

### "Model download failed"
```bash
# Manual download
cd backend/app
uv run python -c "from ultralytics import YOLO; YOLO('yolo11n-seg.pt')"
```

---

## 📝 Example Logs

```
🚀 [GPU] DGX Spark mode: 128GB VRAM, batch_size=128
✓ YOLO person detector loaded: yolo11n-seg.pt
✓ Kornia FaceDetector (YuNet) loaded

[DETECTOR] Batch 94 frames in 3.73s (25.2 FPS): 12 persons, 5 faces, 3 plates
[TRACKER] Frame 94: 12 detections, 8 active tracks

⚖️  [JUEZ] Analyzing track person_001 with 45 frames
⚖️  [JUEZ] Tags consolidated: {'adult', 'beach', 'swimwear', 'outdoor'}
⚖️  [JUEZ] VERDICT: NO VIOLATION - normal context

✅ Video processing complete: vid_123
```

---

## 📚 References

- **FastAPI**: https://fastapi.tiangolo.com/
- **Ultralytics YOLO**: https://docs.ultralytics.com/
- **Kornia**: https://kornia.readthedocs.io/
- **Neo4j**: https://neo4j.com/docs/
- **SurrealDB**: https://surrealdb.com/docs/
