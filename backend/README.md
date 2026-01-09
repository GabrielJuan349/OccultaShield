<div align="center">

# 🛡️ OccultaShield Backend

### Sistema de Alta Precisión para Verificación GDPR y Anonimización de Videos (YOLOv11)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.124.0+-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.6.0+-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![SurrealDB](https://img.shields.io/badge/SurrealDB-1.0+-FF00A0?style=for-the-badge)](https://surrealdb.com/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-008CC1?style=for-the-badge&logo=neo4j)](https://neo4j.com/)

**Motor de privacidad quirúrgico que combina Segmentación de Instancias YOLOv11, Rastreo Kalman, Grafos de Conocimiento Legal y LLMs Multimodales.**

</div>

---

## 📖 Visión General

**OccultaShield Backend** representa la evolución del anonimizado de video. A diferencia de las soluciones tradicionales que aplican cajas negras toscas, este sistema detecta **siluetas exactas** y analiza el contexto legal mediante un "Cerebro Legal" basado en **GraphRAG**.

---

## 🛠️ Arquitectura del Sistema

### Diagrama de Procesamiento "Precision"

```mermaid
graph TD
    A[Video Upload] --> B[Capture Manager]
    B --> C[YOLOv11-seg Module]
    C --> |Polygon Masks| D[Kalman Object Tracker]
    D --> |Tracked Objects| E[Verificator (GraphRAG)]
    E --> F{RGPD Violation?}
    F -->|Yes| G[Precise Anonymization]
    F -->|No| H[Safe Content]
    G & H --> I[Edition Module (Kornia GPU)]
    I --> J[Final Anonymized Video]
```

### Tecnologías Clave:
*   **YOLOv11-seg**: Segmentación de instancias para capturar siluetas exactas.
*   **Filtro de Kalman**: Estabilización avanzada para que las máscaras no oscilen ni tengan lag.
*   **GraphRAG**: Búsqueda híbrida en Neo4j (99 artículos del RGPD) para justificar cada decisión.
*   **Kornia**: Procesamiento de filtros (Blur/Pixelate) directamente en la GPU usando tensores de PyTorch.

---

## 🚀 Guía de Ejecución

### 1. Requisitos e Instalación
```bash
# Python 3.11+ recomendado
pip install kornia scipy pypdf ultralytics opencv-python fastapi uvicorn
```

### 2. Configuración de Bases de Datos
*   **SurrealDB**: `surreal start --user root --pass root memory`
*   **Neo4j**: Instancia con APOC/GDS habilitado (`bolt://localhost:7687`).

### 3. Variables de Entorno (`.env`)
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=Occultashield_neo4j
SURREAL_URL=http://localhost:8000
DETECTION_MODEL_PATH=yolo11n-seg.pt
MULTIMODAL_MODEL_ID=google/gemma-3n-E4B-it
```

### 4. Inicialización e Ingesta
Carga el reglamento RGPD antes de procesar:
```bash
python app/modules/verification/ingest_gdpr.py path/to/gdpr.pdf
```

### 5. Iniciar Servidor
```bash
cd app
uvicorn main:app --host 0.0.0.0 --port 8900 --reload
```

---

## 🧪 Pipeline "OccultaShield Precision"

### FASE 1: Detección y Rastreo
- El sistema utiliza `yolo11n-seg.pt` para obtener polígonos.
- El **Tracker** calcula la velocidad del objeto para predecir su posición futura (Kalman), eliminando el parpadeo de máscaras.

### FASE 2: Verificación Legal
- No todo se anonimiza. La IA consulta el grafo en Neo4j y utiliza un **LLM Multimodal** para decidir si la exposición supone una violación (Ej: Niños en primer plano vs multitud lejana).

### FASE 3: Anonimizado Quirúrgico
- **Máscaras de Silueta**: El desenfoque se aplica exactamente sobre la persona, sin ensuciar el fondo.
- **Fading Dinámico**: Si el sujeto ocupa menos del 0.1% del área del video, el efecto desaparece suavemente para no arruinar la estética si no hay riesgo de identificación.

---

## 📂 Estructura del Proyecto
- `app/modules/detection`: YOLOv11 + Kalman Tracker.
- `app/modules/verification`: Neo4j GraphRAG + Consensus Agents.
- `app/modules/edition`: Kornia Tensor Effects.
- `app/services/video_processor`: Orquestación del pipeline SSE.

---

## 🔍 Detalles Técnicos Importantes
1.  **Modelos Pesados**: El sistema carga Gemma/Llama en VRAM. Se recomienda una GPU con 12GB+ de memoria.
2.  **SSE Streaming**: El progreso se emite por el endpoint `/progress` para alimentar la reactividad del frontend.
3.  **SurrealDB Multi-modelo**: Almacena tanto JSON de bboxes como relaciones entre detecciones y verificaciones legales.
