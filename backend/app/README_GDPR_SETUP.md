# 🔒 GDPR Knowledge Graph Setup

Quick setup of the GDPR Knowledge Graph for OccultaShield's **"TESTIGO VS JUEZ"** verification system.

---

## ⚡ Quick Start (All in one)

```bash
cd backend/app
./setup_gdpr.sh
```

This script:
1. ✅ Verifies UV and Neo4j availability
2. ✅ Offers to start Neo4j with Docker if not running
3. ✅ Automatically configures the `.env` file
4. ✅ Runs enhanced ingestion using the UV environment
5. ✅ Loads data from multiple sources

---

## 🧠 Verification Architecture

OccultaShield uses a **"TESTIGO VS JUEZ"** (Witness vs Judge) architecture for GDPR compliance verification:

```
┌─────────────────────────────────────────────────────────────────┐
│                    VERIFICATION SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                    SUB-AGENTS (TESTIGOS)                 │  │
│   │                                                          │  │
│   │   ┌──────────────┐        ┌──────────────┐              │  │
│   │   │ GemmaClient  │        │ GraphClient  │              │  │
│   │   │              │        │              │              │  │
│   │   │ Visual       │        │ Neo4j Query  │              │  │
│   │   │ Description  │        │ Legal Context│              │  │
│   │   │ (LLM)        │        │ (Knowledge)  │              │  │
│   │   └──────────────┘        └──────────────┘              │  │
│   │                                                          │  │
│   └─────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                 CONSENSUS AGENT (JUEZ)                   │  │
│   │                                                          │  │
│   │   • Consolidates visual descriptions from all frames     │  │
│   │   • Analyzes vulnerability context (tags, environment)   │  │
│   │   • Queries Neo4j for applicable GDPR articles           │  │
│   │   • Emits legal verdict with reasoning                   │  │
│   │                                                          │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Context Classification

### Vulnerable Contexts (GDPR Violation)

| Context | Description | Severity |
|---------|-------------|----------|
| `medical` | Hospital, medical equipment, gowns | High |
| `minor` | Children detected | High |
| `religious` | Religious symbols, locations | Medium |
| `political` | Protests, political gatherings | Medium |
| `intimate` | Private/intimate settings | High |
| `ethnic` | Ethnic indicators | Medium |

### Normal Contexts (No Body Violation)

| Context | Description | Face Only |
|---------|-------------|-----------|
| `public_space` | Streets, parks, beaches | Yes |
| `workplace` | Offices, factories | Yes |
| `commercial` | Shops, malls | Yes |
| `recreational` | Sports, leisure | Yes |
| `transport` | Vehicles, stations | Yes |

**Rule**: In normal contexts, only faces are censored (separate track). Body censorship is not required.

---

## 📦 Data Sources

### 1. Local JSON (Always Loaded)
```
scripts/gdpr_ingestion/json_data/
├── gdpr_articles.json         # 99 GDPR articles
├── gdpr_concepts.json         # Concepts, rights, fines
└── detection_gdpr_mapping.json # Detection → Article mappings
```

### 2. GitHub GDPRtEXT (Automatic)
- **URL**: https://github.com/coolharsh55/GDPRtEXT
- **Content**: Official GDPR texts, explanatory recitals
- **Downloaded automatically** during ingestion

### 3. Kaggle Datasets (Optional)
If Kaggle API is configured:
- GDPR Articles dataset
- GDPR-JSON dataset
- Additional metadata enrichment

---

## 🐳 Neo4j Setup

### Option 1: Docker (Recommended)
```bash
docker run -d \
  --name neo4j-gdpr \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/Occultashield_neo4j \
  neo4j:latest
```

### Option 2: Neo4j Desktop
1. Download from https://neo4j.com/download/
2. Create new project
3. Set password to `Occultashield_neo4j`

**Access:**
- Web UI: http://localhost:7474
- Bolt: bolt://localhost:7687
- Credentials: `neo4j / Occultashield_neo4j`

---

## 🔑 Kaggle Setup (Optional)

```bash
# 1. Get API token from https://www.kaggle.com/settings → API → Create Token
# 2. Place kaggle.json in project:

mkdir -p backend/app/.kaggle
# Copy your kaggle.json there
chmod 600 backend/app/.kaggle/kaggle.json
```

**Search Priority:**
1. 🥇 `backend/app/.kaggle/kaggle.json` (project-local)
2. 🥈 `~/.kaggle/kaggle.json` (user home)

Without Kaggle, the system works with local data + GDPRtEXT.

---

## 📖 Knowledge Graph Structure

```cypher
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

### DetectionType → Article Mappings

| Detection Type | GDPR Articles |
|----------------|---------------|
| `face` | 6, 9 |
| `fingerprint` | 6, 9 |
| `license_plate` | 6, 17 |
| `person` | 6, 13 |
| `id_document` | 6, 9, 32 |
| `credit_card` | 6, 32 |
| `signature` | 6 |

---

## 🚀 Usage in Backend

### GraphClient (with Caching)

```python
from modules.verification.graph_client import GraphClient

graph_client = GraphClient()

# Get GDPR context for a detection type (cached for 5 minutes)
context = await graph_client.get_context_for_detection("face")
# Returns: Articles 6, 9 with full text

# Semantic search with embeddings
results = await graph_client.semantic_search(
    query="biometric data processing",
    limit=5
)
```

### GemmaClient (Visual Description)

```python
from modules.verification.gemma_client import GemmaClient

gemma_client = GemmaClient()

# Visual description (TESTIGO role)
description = await gemma_client.describe_image(image_path)
# Returns: tags, environment, clothing_level, visible_biometrics

# Sensitive content classification
classification = await gemma_client.classify_sensitive_content(image_path)
# Detects: fingerprint, id_document, credit_card, signature
```

### ConsensusAgent (Legal Verdict)

```python
from modules.verification.consensus_agent import ConsensusAgent

consensus = ConsensusAgent()

# Analyze all frames for a track
verdict = await consensus.evaluate_track(
    track_id="person_001",
    frame_results=frame_descriptions,  # From SubAgents
    detection_type="person"
)

# verdict contains:
# - is_violation: bool
# - severity: "high" | "medium" | "none"
# - violated_articles: ["6", "9"]
# - vulnerability_type: "medical" | null
# - reasoning: "Human-readable explanation"
# - recommended_action: "blur" | "none"
```

---

## 🔄 Complete Flow

```
1. User uploads video with people
   ↓
2. HybridDetectorManager detects persons, faces, plates
   ↓
3. ObjectTracker assigns track_ids with Kalman Filter
   ↓
4. ParallelProcessor groups frames by track_id
   ↓
5. SubAgents analyze each frame:
   ├── GemmaClient → Visual description (tags, environment)
   └── GraphClient → Legal context from Neo4j
   ↓
6. ConsensusAgent (JUEZ) evaluates:
   ├── Consolidate all frame descriptions
   ├── Analyze vulnerability context
   ├── Query Neo4j for applicable articles
   └── Emit verdict: violation / no_violation
   ↓
7. Results stored in SurrealDB
   ↓
8. Human reviews and confirms
   ↓
9. VideoAnonymizer applies effects
```

---

## 📊 Verification Queries

### After Ingestion
```cypher
-- Count all entities
MATCH (a:Article) RETURN count(a) as articles
-- Should return ~99

-- Verify detection mappings
MATCH (d:DetectionType)-[:VIOLATES]->(a:Article)
RETURN d.type, collect(a.number) as articles

-- Check embeddings exist
MATCH (a:Article)
WHERE a.embedding IS NOT NULL
RETURN count(a) as articles_with_embeddings

-- Article 6 (legal basis)
MATCH (a:Article {number: 6})
RETURN a.title, a.content
```

---

## 🐛 Troubleshooting

### "Neo4j not detected"
```bash
docker start neo4j-gdpr  # If exists
# Or create new:
docker run -d --name neo4j-gdpr -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/Occultashield_neo4j neo4j:latest
```

### "Could not download GDPRtEXT"
- Check Internet connection
- GitHub may be temporarily unavailable
- The script continues with local data only

### "UV not found"
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### "Graph context empty"
```bash
# Verify Neo4j is in .env
cat .env | grep NEO4J

# Should contain:
# NEO4J_URI=bolt://localhost:7687
# NEO4J_PASSWORD=Occultashield_neo4j

# Restart backend
uv run uvicorn main:app --host 0.0.0.0 --port 8900 --reload
```

### "Embeddings not working"
```bash
# Ensure sentence-transformers is installed
uv run python -c "from sentence_transformers import SentenceTransformer; print('OK')"

# Re-run ingestion to regenerate embeddings
./setup_gdpr.sh
```

---

## 📝 Example Logs

```
╔═══════════════════════════════════════════════════════════╗
║  Enhanced GDPR Knowledge Graph Setup                      ║
║  Using UV environment (no pip install needed!)            ║
╚═══════════════════════════════════════════════════════════╝

🔍 Checking UV...
✅ uv 0.9.24

🔍 Checking Neo4j...
✅ Neo4j is running on port 7687

🚀 Starting Enhanced GDPR Knowledge Graph Ingestion...
======================================================================

📦 PHASE 1: Loading core GDPR data...
✅ Database cleaned
✅ Constraints and indices created
✅ Local data loaded: 99 articles

🌐 PHASE 2: Loading external GDPR sources...
✅ GDPRtEXT data loaded
✅ Kaggle datasets loaded

✨ PHASE 3: Enriching knowledge graph...
✅ Relationships created
✅ Embeddings generated (all-MiniLM-L6-v2)
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
```

---

## 🎓 References

- **GDPRtEXT**: https://github.com/coolharsh55/GDPRtEXT
- **GDPR Official**: https://gdpr-info.eu/
- **Neo4j**: https://neo4j.com/docs/
- **Sentence Transformers**: https://www.sbert.net/
- **Kaggle API**: https://github.com/Kaggle/kaggle-api
