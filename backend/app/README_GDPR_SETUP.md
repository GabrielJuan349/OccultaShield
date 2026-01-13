# 🔒 GDPR Knowledge Graph Setup

Configuración rápida del Knowledge Graph GDPR para OccultaShield.

## ⚡ Quick Start (Todo en uno)

```bash
cd /home/gjuan/OccultaShield/backend/app
./setup_gdpr.sh
```

Este script:
1. ✅ Verifica que UV y Neo4j estén disponibles
2. ✅ Ofrece iniciar Neo4j con Docker si no está corriendo
3. ✅ Configura el archivo `.env` automáticamente
4. ✅ Ejecuta la ingesta mejorada usando el entorno UV (no necesita pip install)
5. ✅ Carga datos desde:
   - JSON locales (artículos, conceptos, mappings)
   - **GitHub GDPRtEXT** (oficial, descarga automática)
   - **Kaggle datasets** (opcional, si tienes API configurada)

## 📦 Dependencias

**Ya incluidas en pyproject.toml:**
- ✅ `neo4j` - Driver para Neo4j
- ✅ `sentence-transformers` - Embeddings semánticos
- ✅ `kaggle` - API de Kaggle (opcional)
- ✅ `python-dotenv` - Variables de entorno

**No necesitas instalar nada manualmente**, UV ya tiene todo.

## 🐳 Solo Neo4j (si no lo tienes)

```bash
docker run -d \
  --name neo4j-gdpr \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/Occultashield_neo4j \
  neo4j:latest
```

**UI Web:** http://localhost:7474
**Credenciales:** neo4j / Occultashield_neo4j

## 🔑 Kaggle Setup (Opcional)

Para incluir datasets de Kaggle (opcional, pero recomendado):

```bash
# 1. Obtener token de https://www.kaggle.com/settings → API → Create Token
# 2. Ya existe en el proyecto! Verifica que esté en:
#    backend/app/.kaggle/kaggle.json

# Si no existe, créalo:
mkdir -p .kaggle
# Luego copia tu kaggle.json allí
chmod 600 .kaggle/kaggle.json
```

**Prioridad de búsqueda:**
1. 🥇 `backend/app/.kaggle/kaggle.json` (local al proyecto)
2. 🥈 `~/.kaggle/kaggle.json` (home del usuario)

Sin Kaggle el sistema funciona igual, solo con datos locales + GDPRtEXT.

## 🎯 Fuentes de Datos

### 1. JSON Locales (Siempre)
- `scripts/gdpr_ingestion/json_data/gdpr_articles.json` - 99 artículos GDPR
- `scripts/gdpr_ingestion/json_data/gdpr_concepts.json` - Conceptos, derechos, multas
- `scripts/gdpr_ingestion/json_data/detection_gdpr_mapping.json` - Mapeo detecciones → artículos

### 2. GitHub GDPRtEXT (Siempre)
Repositorio oficial: https://github.com/coolharsh55/GDPRtEXT
- Textos completos del RGPD en JSON
- Recitals explicativos
- Descarga automática durante ingesta

### 3. Kaggle Datasets (Opcional)
Si tienes Kaggle configurado:
- GDPR Articles dataset
- GDPR-JSON dataset
- Enriquece con más metadatos

## 📊 Verificación

Después de la ingesta, verifica en Neo4j:

```bash
# Abrir Neo4j Browser
open http://localhost:7474

# Queries de prueba
MATCH (a:Article) RETURN count(a)
# Debe retornar ~99 artículos

MATCH (d:DetectionType)-[:VIOLATES]->(a:Article)
RETURN d.type, collect(a.number) as articles
# Ver qué artículos viola cada tipo de detección

MATCH (a:Article)
WHERE a.embedding IS NOT NULL
RETURN count(a)
# Verificar embeddings para búsqueda semántica

# Buscar artículo 6 (base legal)
MATCH (a:Article {number: 6})
RETURN a.title, a.content
```

## 🚀 Uso en el Backend

El módulo de verificación usa automáticamente el Knowledge Graph:

```python
# modules/verification/graph_client.py
context = await graph_client.get_context_for_detection("face")
# Retorna artículos GDPR relevantes para detección de rostros

# modules/verification/gemma_client.py
analysis = await gemma_client.analyze_image(
    image_path=image_path,
    context=context,  # Contexto GDPR del knowledge graph
    detection_type="face"
)
# Analiza con IA usando contexto GDPR
```

## 🔄 Flujo Completo

```
1. Usuario sube video con rostros
   ↓
2. Detector encuentra rostros (YOLOv10)
   ↓
3. SubAgent consulta Knowledge Graph:
   graph_client.get_context_for_detection("face")
   → Retorna: Artículos 6, 9, 10, 13, etc.
   ↓
4. Gemma analiza imagen con contexto GDPR
   ↓
5. ConsensusAgent agrega resultados
   ↓
6. Sistema reporta violaciones al usuario
```

## 📖 Estructura del Knowledge Graph

```
(Chapter)-[:CONTAINS]->(Article)
(Article)-[:HAS_PARAGRAPH]->(Paragraph)
(Article)-[:DEFINES]->(Concept)
(Article)-[:GRANTS]->(Right)
(Article)-[:EXPLAINED_BY]->(Recital)
(Article)-[:REFERENCES]->(Article)
(DetectionType)-[:VIOLATES]->(Article)
(DataType)-[:PROTECTED_BY]->(Article)
(Fine)-[:APPLIES_TO]->(Article)
```

## 🐛 Troubleshooting

### "Neo4j not detected"
```bash
# Iniciar con Docker
docker start neo4j-gdpr  # Si ya existe
# O crear nuevo
docker run -d --name neo4j-gdpr -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/Occultashield_neo4j neo4j:latest
```

### "Could not download GDPRtEXT"
- Verifica conexión a Internet
- GitHub puede estar temporalmente no disponible
- El script continuará con datos locales

### "UV not found"
```bash
# Instalar UV
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Backend no usa el Knowledge Graph
```bash
# Verificar que Neo4j está en .env
cat .env | grep NEO4J

# Debe contener:
# NEO4J_URI=bolt://localhost:7687
# NEO4J_PASSWORD=Occultashield_neo4j

# Reiniciar backend
# CTRL+C y volver a iniciar con:
uv run uvicorn main:app --host 0.0.0.0 --port 8980 --reload
```

## 📝 Logs de Ejemplo

```
╔═══════════════════════════════════════════════════════════╗
║  Enhanced GDPR Knowledge Graph Setup                      ║
║  Using UV environment (no pip install needed!)            ║
╚═══════════════════════════════════════════════════════════╝

🔍 Checking UV...
✅ uv 0.9.24

🔍 Checking Neo4j...
✅ Neo4j is running on port 7687

🔍 Checking environment configuration...
✅ .env file found
✅ Neo4j configuration present

🔍 Checking optional Kaggle API...
✅ Kaggle API available in UV environment
✅ Kaggle credentials configured

═══════════════════════════════════════════════════════════
📋 Configuration Summary
═══════════════════════════════════════════════════════════

Data sources that will be loaded:
  ✅ Local JSON files (articles, concepts, mappings)
  ✅ GitHub GDPRtEXT repository (official GDPR texts)
  ✅ Kaggle datasets (optional enhancement)

Knowledge graph will include:
  • 99 GDPR Articles with full text
  • Chapters, Paragraphs, Recitals
  • Concepts, Data Types, Rights
  • Detection → Article mappings
  • Fine tiers and amounts
  • Semantic embeddings for search
  • Fulltext indices

═══════════════════════════════════════════════════════════

Ready to run Enhanced GDPR Ingestion? (y/n) y

🚀 Running Enhanced GDPR Ingestion with UV...

🚀 Starting Enhanced GDPR Knowledge Graph Ingestion...
======================================================================

📦 PHASE 1: Loading core GDPR data...
🧹 Cleaning existing database...
✅ Database cleaned
🔒 Creating constraints...
✅ Constraints and indices created
📜 Loading local GDPR data...
✅ Local data loaded

🌐 PHASE 2: Loading external GDPR sources...
📥 Downloading GDPRtEXT repository data...
   Processing GDPRtEXT articles...
✅ GDPRtEXT data loaded
📥 Downloading Kaggle GDPR datasets...
   ✅ Downloaded: gdpr_articles
   ✅ Downloaded: gdpr_json
   Processing Kaggle files...

✨ PHASE 3: Enriching knowledge graph...
🔗 Creating relationships...
✅ Relationships created
🧮 Generating embeddings...
✅ Embeddings generated
🔍 Creating fulltext indices...
✅ Fulltext indices created

======================================================================
📊 ENHANCED INGESTION SUMMARY
======================================================================
  📁 Chapters:          11
  📜 Articles:          99
  💡 Concepts:          45
  📊 Data Types:        12
  ⚖️  Rights:            8
  💰 Fines:             2
  🌐 External Sources:  3
======================================================================
✅ ENHANCED INGESTION COMPLETED

💡 Knowledge graph ready for GDPR compliance verification!

═══════════════════════════════════════════════════════════

✅ GDPR Knowledge Graph Setup Complete!

🎉 Next steps:

1. Verify the data in Neo4j Browser:
   http://localhost:7474
   User: neo4j
   Password: Occultashield_neo4j

2. Test queries:
   MATCH (a:Article) RETURN count(a)  # Should return ~99
   MATCH (d:DetectionType)-[:VIOLATES]->(a:Article) RETURN d.type, a.number

3. Start the backend server (if not running):
   uv run uvicorn main:app --host 0.0.0.0 --port 8980 --reload

4. Test video processing:
   Upload a video with faces to verify GDPR compliance checking

═══════════════════════════════════════════════════════════
```

## 🎓 Referencias

- **GDPRtEXT**: https://github.com/coolharsh55/GDPRtEXT
- **GDPR Official**: https://gdpr-info.eu/
- **Neo4j**: https://neo4j.com/docs/
- **Sentence Transformers**: https://www.sbert.net/
- **Kaggle API**: https://github.com/Kaggle/kaggle-api
