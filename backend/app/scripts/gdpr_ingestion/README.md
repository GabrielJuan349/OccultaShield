# Enhanced GDPR Knowledge Graph Ingestion

This enhanced script integrates GDPR data from multiple sources to create a complete knowledge graph in Neo4j.

## Data Sources

1. **Local JSON files** (included in the project)
   - `gdpr_articles.json` - GDPR Articles
   - `gdpr_concepts.json` - Concepts, data types, rights and fines
   - `detection_gdpr_mapping.json` - Detection to GDPR articles mapping

2. **GitHub: coolharsh55/GDPRtEXT**
   - Official repository with complete GDPR texts in JSON format
   - URL: https://github.com/coolharsh55/GDPRtEXT
   - Downloaded automatically during ingestion

3. **Kaggle Datasets** (optional)
   - GDPR Articles dataset
   - GDPR-JSON dataset
   - Requires Kaggle API configuration (see below)

## Requirements

### Python Dependencies

```bash
pip install neo4j sentence-transformers requests kaggle python-dotenv
```

### Neo4j Database

Make sure Neo4j is running:

```bash
# With Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/Occultashield_neo4j \
  neo4j:latest

# Or start it locally
neo4j start
```

### Environment Variables

Create a `.env` file in the `backend/app` directory with:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=Occultashield_neo4j
```

## Kaggle Configuration (Optional)

If you want to include Kaggle datasets:

1. **Create a Kaggle account**: https://www.kaggle.com
2. **Get API credentials**:
   - Go to: https://www.kaggle.com/settings
   - Scroll to "API" section
   - Click "Create New API Token"
   - `kaggle.json` will be downloaded

3. **Install credentials**:
   ```bash
   mkdir -p ~/.kaggle
   cp kaggle.json ~/.kaggle/
   chmod 600 ~/.kaggle/kaggle.json
   ```

4. **Install Kaggle API**:
   ```bash
   pip install kaggle
   ```

## Execution

### Method 1: Enhanced Script (Recommended)

```bash
cd /home/gjuan/OccultaShield/backend/app
python scripts/gdpr_ingestion/enhanced_ingest_gdpr.py
```

This script:
- ✅ Loads local JSON data
- ✅ Downloads and processes GDPRtEXT from GitHub
- ✅ (Optional) Downloads Kaggle datasets
- ✅ Creates embeddings for semantic search
- ✅ Establishes relationships between nodes
- ✅ Creates fulltext indices

### Method 2: Original Script (Local data only)

```bash
cd /home/gjuan/OccultaShield/backend/app
python scripts/gdpr_ingestion/ingest_gdpr.py
```

## Verification

After ingestion, verify the knowledge graph:

```bash
# Connect to Neo4j Browser: http://localhost:7474

# Verify articles
MATCH (a:Article) RETURN count(a) as total_articles

# See graph structure
CALL db.schema.visualization()

# Search for specific article
MATCH (a:Article {number: 6})
RETURN a.title, a.content

# Find articles related to a detection type
MATCH (d:DetectionType {type: "face"})-[:VIOLATES]->(a:Article)
RETURN a.number, a.title

# Search for articles with embeddings
MATCH (a:Article)
WHERE a.embedding IS NOT NULL
RETURN count(a) as articles_with_embeddings
```

## Knowledge Graph Structure

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

## Troubleshooting

### Error: "Failed to init Neo4j driver"
- Verify Neo4j is running: `neo4j status`
- Check credentials in `.env`
- Verify port: `netstat -an | grep 7687`

### Error: "Kaggle API not available"
- It's optional. The script will continue without Kaggle datasets
- To use Kaggle, follow the configuration steps above

### Error: "Could not download GDPRtEXT"
- Check Internet connection
- Verify GitHub is not blocked
- The script will continue with local data

### Very slow embeddings
- First execution downloads the `all-MiniLM-L6-v2` model (~80MB)
- Subsequent executions will be faster
- Consider using GPU if available

## Example Logs

```
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
   Downloading: GDPR Articles...
   ✅ Downloaded: gdpr_articles
   Downloading: GDPR-JSON...
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
```

## Next Steps

After ingestion:

1. **Verify data in Neo4j Browser**: http://localhost:7474
2. **Run the backend**: The verification module will automatically use the knowledge graph
3. **Test with a video**: Upload a video and verify that GDPR violations are detected correctly

## References

- **GDPRtEXT**: https://github.com/coolharsh55/GDPRtEXT
- **GDPR Official**: https://gdpr-info.eu/
- **Neo4j Docs**: https://neo4j.com/docs/
- **Sentence Transformers**: https://www.sbert.net/
