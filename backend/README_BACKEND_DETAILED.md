# Documentación Detallada del Backend (OccultaShield)

**Versión del Proyecto:** 1.2
**Fecha de Actualización:** 21/12/2025
**Core:** Python 3.11+ / FastAPI / PyTorch

---

## 1. Arquitectura Profunda: El Pipeline de Privacidad

El backend no es una API monolítica, sino un orquestador de micro-servicios lógicos (Módulos) que se ejecutan secuencialmente o en paralelo sobre un stream de video.

### 1.1 Diagrama de Flujo de Datos

```mermaid
graph TD
    A[Video Upload] --> B[Capture Manager]
    B --> C[YOLO Detection Module]
    C --> |Detections + BBox| D[Object Tracker]
    D --> |Tracked Objects (ID)| E[Verificator (GraphRAG)]
    E --> F{Is GDPR Violation?}
    F -->|Yes| G[Mark for Anonymization]
    F -->|No| H[Mark as Safe]
    G & H --> I[Edition Module (Blurring)]
    I --> J[Final Video]
```

---

## 2. Disección de Módulos (`app/modules`)

### 2.1 Módulo de Detección (`modules/detection`)
Este módulo convierte píxeles en datos estructurados.

*   **`detector.py` (El Ojo):**
    *   Carga modelos **Ultralytics YOLO** (`yolov10m.pt` por defecto, optimizado para velocidad/precisión).
    *   **Preprocesamiento:** Redimensiona frames a 640x640 (o input del modelo).
    *   **Inferencia:** Ejecuta el modelo en GPU (`cuda`) si está disponible.
    *   **Clases:** Mapea las clases de COCO (0=persona, 2=coche) a clases de interés GDPR (`person`, `license_plate`). *Nota: Se recomienda re-entrenar un modelo específico para matrículas.*
*   **`tracker.py` (La Memoria Visual):**
    *   Resuelve el problema de "parpadeo" (un objeto detectado en el frame 1, perdido en el 2, reaparece en el 3).
    *   Asigna un **Track ID** único a cada objeto. Esto es CRÍTICO para el módulo de verificación: no queremos verificar a la misma persona 30 veces por segundo. Solo verificamos una vez por "aparición".
*   **`capture_manager.py`:**
    *   Decide inteligentemente cuándo guardar un "snapshot" de un objeto para enviarlo al LLM. No guarda todos los frames, solo el de mejor calidad/puntuación de confianza cada N segundos.

### 2.2 Módulo de Verificación (`modules/verification`) - "El Cerebro Legal"
Aquí reside la innovación principal: **GraphRAG (Retrieval-Augmented Generation con Grafos)**.

*   **Ingestión (`ingest_gdpr.py`):**
    *   **Proceso:** Carga el PDF del GDPR -> Chunking (Divide texto) -> Embeddings (HuggingFace) -> Vector Store (Neo4j).
    *   **Estructura de Grafo:** Crea nodos `GDPRArticle` conectados semánticamente. Esto permite búsquedas como "derecho al olvido" y encontrar el Artículo 17 aunque no se mencione explícitamente esa frase.
*   **Motor de Razonamiento (`graph_rag.py`):**
    *   **Clase `GDPRVerificationGraph`:** Implementa un flujo **LangGraph**:
        1.  **Retrieve Context:** Búsqueda Híbrida (Vectores + Keywords Cypher) en Neo4j para encontrar artículos relevantes a los objetos detectados (ej. si detecta "niño", busca artículos sobre "menores").
        2.  **Multimodal LLM:** Envía la imagen (Crop del objeto) + Artículos GDPR recuperados al modelo (Gemma/Llama).
        3.  **Prompt Engineering:** El prompt (hardcoded en `graph_rag.py`) instruye al modelo para actuar como un "Analista GDPR", evaluando severidad y violaciones específicas.
*   **Agentes (`consensus_agent.py`):**
    *   Actualmente implementa una lógica de validación simple, pero está diseñado para **Votación Mayoritaria**.
    *   Futuro: Tres agentes (uno conservador, uno permisivo, uno legalista) analizan la imagen. El `ConsensusAgent` agrega sus votos para reducir falsos positivos.

---

## 3. Base de Datos e Persistencia

### 3.1 Neo4j (Conocimiento Vectorial)
Se utiliza exclusivamente para el RAG. Almacena:
*   Documentos legales fragmentados.
*   Índices vectoriales para búsqueda semántica.
*   *No almacena datos de usuario ni videos.*

### 3.2 SurrealDB (Datos de Aplicación)
Se utiliza para todo lo demás:
*   **Tabla `user`:** Credenciales (gestionadas por Better-Auth).
*   **Tabla `session`:** Tokens de sesión.
*   **Tabla `video`:** Metadatos (path, duración, estado, usuario propietario).
*   **Tabla `detection`:** Resultados brutos de YOLO.
*   **Tabla `violation`:** Resultados refinados del Verificador (linked to detections).

---

## 4. Detalles Técnicos Críticos y "Gotchas"

1.  **Gestión de Dependencias (requirements.txt):**
    *   El archivo actual contiene rutas absolutas (`file:///C:/...`). Esto **romperá** el despliegue en cualquier otra máquina.
    *   *Acción Requerida:* Ejecutar `pip freeze > requirements.txt` en un entorno limpio o limpiar manualmente el archivo dejando solo nombres de paquetes (`fastapi==0.109.0`, etc.).
2.  **Cuello de Botella en GPU:**
    *   Correr YOLO y Gemma (LLM) simultáneamente en la misma GPU de consumo (ej. RTX 3060/4060) causará OOM (Out Of Memory).
    *   *Solución:* Descargar el modelo LLM a CPU (muy lento) o usar una API externa (OpenAI/Anthropic) si no hay VRAM suficiente (24GB+ recomendado para local puro).
3.  **Latencia del Event Loop:**
    *   `detector.process_video` y `graph_rag.run` son operaciones intensivas bloqueantes.
    *   Si no se ejecutan en un `ThreadPoolExecutor` o `ProcessPoolExecutor`, bloquearán el heartbeat de FastAPI, causando que el frontend desconecte el SSE por timeout.
4.  **Inicialización de Modelos:**
    *   `GDPRVerificationGraph` es un Singleton. Carga el modelo LLM al arrancar la primera vez. Esto significa que la primera petición de verificación tardará ~30-60 segundos en iniciar mientras carga pesos en memoria.
