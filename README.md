# 🛡️ OccultaShield

[![Angular](https://img.shields.io/badge/Angular-v21-dd0031?style=flat-square&logo=angular)](https://angular.dev) 
[![FastAPI](https://img.shields.io/badge/FastAPI-v0.111+-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![AI](https://img.shields.io/badge/AI-YOLOv11--seg-FFAC45?style=flat-square&logo=ultralytics)](https://ultralytics.com)
[![Privacy](https://img.shields.io/badge/GDPR-Compliant-blue?style=flat-square)](https://gdpr-info.eu)
[![License](https://img.shields.io/badge/License-MPL_2.0-orange?style=flat-square)](LICENSE)

**OccultaShield** is a state-of-the-art AI application designed to prevent GDPR and European privacy law violations in video content. By combining instance segmentation, legal RAG (Retrieval-Augmented Generation), and a "Human-in-the-Loop" workflow, it provides a surgical approach to video anonymization.

*This project is a Bachelor's Thesis in Computer Engineering (Computing specialization) at the **Autonomous University of Barcelona (UAB)**.*

---

## ✨ Key Features

- **🚀 YOLOv11 Precision Mode**: Uses instance segmentation (`yolo11-seg`) to detect silhouettes with polygonal accuracy, moving beyond rough bounding boxes.
- **⚖️ Legal RAG Brain**: Integrated with a **Neo4j** knowledge graph containing the full GDPR text, providing automated legal justification for every detection.
- **🎯 Intelligent Tracking**: Implements **Kalman Filters** and camera motion compensation to ensure privacy masks stay locked on subjects, even in complex drone or handheld shots.
- **🛡️ Dynamic Discernibility**: Automatically desvanece (fades) anonymization effects for subjects that are too small to be identifiable, maintaining cinematic quality while ensuring compliance.
- **🤝 Human-in-the-Loop**: A streamlined review interface where human operators can validate or override AI decisions before final rendering.
- **🛡️ Admin Control Center**: A dedicated panel for user management, role assignment, and system-wide settings.
- **🚪 Closed Beta Approval**: Integrated registration workflow where new users require manual administrator approval, coupled with automated email notifications.
- **📜 Audit Log**: Comprehensive tracking of all administrative actions (approvals, rejections, settings changes) for full accountability.

---

## 🏗️ Architecture

OccultaShield is built on a high-performance modern stack:

### Frontend
- **Framework**: Angular v21 (Zoneless + Signals strategy).
- **Admin API**: Centralized server-side logic within the Angular SSR (Express) server for user management and secure operations.
- **UX**: Premium Dark Mode with Glassmorphism aesthetics and real-time Toast notifications.

### Backend
- **Core**: FastAPI (Python) for asynchronous orchestration of AI tasks.
- **AI/CV**: Ultralytics YOLOv11, Kornia (GPU-accelerated filters), and OpenCV.
- **Knowledge Graph**: Neo4j (Vector Index + Cypher) for GDPR reasoning.
- **Persistence**: SurrealDB for multi-model storage (Relations + JSON).
- **Notifications**: Integrated Nodemailer for transactional system emails.

---

## 🚀 Getting Started

To get the full system running, follow the specific guides for each module:

1.  **[General Execution Guide](README_EXECUTION_GENERAL.md)** - Start here for the big picture.
2.  **[Backend Guide](backend/README_EXECUTION_BACKEND.md)** - Details on AI models, Neo4j, and GPU setup.
3.  **[Frontend Guide](frontend/README_EXECUTION_FRONTEND.md)** - Details on Angular v21 signals and dev server.

### Quick Command Summary
```bash
# 1. Start Databases
surreal start --user root --pass root memory # SurrealDB
neo4j console # Neo4j

# 2. Run Backend
cd backend && pip install -r requirements.txt
python app/modules/verification/ingest_gdpr.py data/gdpr.pdf
cd app && uvicorn main:app --port 8900

# 3. Run Frontend
cd frontend && bun install
bun run dev
```

---

## 📂 Project Structure

```bash
OccultaShield/
├── backend/            # FastAPI + AI Modules (Detection, Edition, RAG)
│   ├── app/            # Source code
│   └── README_EXECUTION_BACKEND.md
├── frontend/           # Angular v21 Application
│   ├── src/            # Components, Signals, Services
│   └── README_EXECUTION_FRONTEND.md
├── README_EXECUTION_GENERAL.md  # Unified setup instructions
└── README.md           # You are here
```

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the **Mozilla Public License Version 2.0**. See `LICENSE` for more information.

---

## 🎓 Acknowledgments

- **UAB (Autonomous University of Barcelona)** for the academic support.
- **Ultralytics** for the YOLOv11 framework.
- **Kornia Team** for the GPU-accelerated vision operations.
