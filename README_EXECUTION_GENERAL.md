# 🛡️ OccultaShield - General Execution Guide

Complete guide to set up and run the OccultaShield GDPR video anonymization platform.

---

## 🏗️ Architecture Overview

OccultaShield is a high-precision video anonymization platform with a **Human-in-the-Loop** workflow:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OCCULTASHIELD PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │   DETECTION  │────▶│ VERIFICATION │────▶│   EDITION    │                │
│  │  YOLOv11-seg │     │ Gemma + Neo4j│     │    Kornia    │                │
│  │    + YuNet   │     │   GraphRAG   │     │  GPU Effects │                │
│  └──────────────┘     └──────────────┘     └──────────────┘                │
│         │                    │                    │                         │
│         ▼                    ▼                    ▼                         │
│  • Faces (YuNet)       • GDPR Compliance    • Blur / Pixelate             │
│  • Persons (YOLO)      • Witness/Judge AI   • Irreversible masks          │
│  • License Plates      • Vulnerability      • Metadata stripping          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| **OS** | Windows/Linux | WSL2 recommended on Windows |
| **Python** | 3.10+ | Managed via `uv` |
| **Node.js** | 20+ | Managed via `nvm` |
| **Bun** | 1.3+ | For frontend |
| **Docker** | Latest | For databases |
| **GPU** | NVIDIA (optional) | Recommended for YOLO/Kornia |

---

## ⚡ Quick Start (Automated)

Use the automated installation script:

```bash
# Make executable and run
chmod +x instalation.sh
./instalation.sh
```

The script will:
1. ✅ Install system dependencies (ffmpeg, docker)
2. ✅ Set up Bun, Node.js, and Angular CLI
3. ✅ Configure `.env` files interactively (or use defaults)
4. ✅ Install backend (uv) and frontend (bun) dependencies
5. ✅ Start Docker services (Neo4j + SurrealDB)
6. ✅ Optionally set up Hugging Face login for Gemma LLM
7. ✅ Optionally ingest GDPR knowledge graph

---

## 📦 Manual Setup

### 1. Start Databases

```bash
cd docker
docker compose up -d
```

This starts:
- **Neo4j**: `http://localhost:7474` (bolt: 7687)
- **SurrealDB**: `http://localhost:8000`

> SurrealDB schema is automatically imported via `--import-file`.

### 2. Configure Environment

Create `.env` files from examples:

```bash
# Backend
cp backend/app/.env.example backend/app/.env

# Frontend
cp frontend/.env.example frontend/.env

# Docker
cp docker/.env.example docker/.env
```

**Shared variables** (must match across all `.env` files):
- `SURREALDB_*` credentials
- `BETTERAUTH_SECRET`
- `NEO4J_PASSWORD`

### 3. Install Dependencies

```bash
# Backend
cd backend/app
uv sync
uv add kornia pandas

# Frontend
cd frontend
bun install
```

### 4. GDPR Knowledge Graph (Optional)

For full legal verification capabilities:

```bash
cd backend/app
uv run python scripts/gdpr_ingestion/enhanced_ingest_gdpr.py
```

### 5. Hugging Face Login (Optional)

Required for Gemma LLM (visual verification):

```bash
pip install huggingface_hub
huggingface-cli login
```

> Visit https://huggingface.co/google/gemma-3n-E4B-it to accept the license first.

### 6. Start Services

```bash
# Terminal 1: Backend
cd backend/app
uv run main.py

# Terminal 2: Frontend
cd frontend
bun run dev
```

Access the application at:
- **Frontend**: http://localhost:4200
- **Backend API**: http://localhost:8980
- **Neo4j Browser**: http://localhost:7474

---

## 🛡️ Admin Panel

Access the admin panel at `/admin`:

| Feature | Description |
|---------|-------------|
| **User Management** | Approve/reject registrations, manage roles |
| **Closed Beta Mode** | Require admin approval for new users |
| **Audit Log** | Track all administrative actions |
| **Dashboard Stats** | Users, videos, violations overview |

Admin credentials are configured in `frontend/.env`:
```env
ADMIN_EMAIL=admin@occultashield.local
ADMIN_PASSWORD=your_password
```

---

## 🧪 Testing the Pipeline

1. **Register** a new account (requires approval if Closed Beta is on)
2. **Admin Approval**: Go to `/admin/users` and approve the user
3. **Upload**: Upload a video at `/upload`
4. **Monitor**: Watch real-time progress via SSE
5. **Review**: Inspect detections in the review page
6. **Download**: Get the anonymized video

---

## 🧩 Module Overview

| Module | Location | Description |
|--------|----------|-------------|
| **Detection** | `backend/app/modules/detection/` | YOLOv11-seg + Kornia YuNet face detection |
| **Verification** | `backend/app/modules/verification/` | GDPR compliance via Neo4j + Gemma LLM |
| **Edition** | `backend/app/modules/edition/` | GPU-accelerated anonymization effects |

### Detection Module
- Hybrid architecture: Kornia FaceDetector (YuNet) + YOLO
- Segmentation masks for precise person boundaries
- Multi-object tracking with ID persistence

### Verification Module
- **Witness (GemmaClient)**: Visual description without legal judgment
- **Judge (ConsensusAgent)**: Legal decision based on GDPR rules
- **Neo4j GraphRAG**: GDPR article retrieval and context

### Edition Module
- GPU effects via Kornia (blur, pixelate)
- Noise injection for irreversibility
- FFmpeg metadata stripping for GDPR compliance

---

## 🔧 Environment Variables

### Backend (`backend/app/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVER_PORT` | API server port | `8980` |
| `CLIENT_URL` | CORS allowed origin | `http://localhost:4200` |
| `BETTERAUTH_SECRET` | Auth secret key | (generate) |
| `SURREALDB_*` | Database connection | `localhost:8000` |
| `NEO4J_*` | Neo4j connection | `localhost:7687` |
| `DETECTION_MODEL_PATH` | YOLO model | `yolo11n-seg.pt` |

### Frontend (`frontend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `BETTERAUTH_SECRET` | Must match backend | (generate) |
| `ADMIN_EMAIL` | Initial admin email | `admin@...` |
| `ADMIN_PASSWORD` | Initial admin password | (set) |
| `SMTP_*` | Email service config | (optional) |

---

## 🔍 Troubleshooting

### First Run Takes Long
YOLO models download automatically on first use (~50MB for yolo11n-seg.pt).

### "Model not loaded" Error
```bash
huggingface-cli login
```
Then accept the Gemma license at HuggingFace.

### SSE Connection Issues
Check backend logs for `video_processor` activity. Ensure correct `CLIENT_URL` in backend `.env`.

### GPU Not Detected
```bash
python -c "import torch; print(torch.cuda.is_available())"
```
If `False`, install CUDA-compatible PyTorch.

### Database Connection Failed
```bash
# Check Docker services
docker compose -f docker/docker-compose.yml ps
```

---

## 📚 Related Documentation

| Document | Location | Content |
|----------|----------|---------|
| Backend Setup | `backend/README.md` | Detailed backend configuration |
| Frontend Setup | `frontend/README.md` | Angular/Bun configuration |
| Auth Setup | `frontend/BETTER_AUTH_SETUP.md` | Better-Auth + admin API |
| GDPR Setup | `backend/app/README_GDPR_SETUP.md` | Neo4j knowledge graph |
| Detection Models | `backend/app/modules/detection/README_MODELS.md` | YOLO model details |
| Verification Module | `backend/app/modules/verification/README.md` | Full verification docs |
| Edition Module | `backend/app/modules/edition/README.md` | Anonymization effects |

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Angular v21 (Zoneless, Signals, SSR) |
| **Admin API** | Node.js Express (SSR server) |
| **Backend** | FastAPI / Python |
| **Detection** | YOLOv11-seg, Kornia YuNet |
| **Verification** | Neo4j, LangGraph, Gemma 3n LLM |
| **Edition** | Kornia (GPU), OpenCV (CPU fallback) |
| **Auth** | Better-Auth |
| **Databases** | SurrealDB, Neo4j |
| **Email** | Nodemailer |
| **Package Managers** | uv (Python), Bun (JS) |
