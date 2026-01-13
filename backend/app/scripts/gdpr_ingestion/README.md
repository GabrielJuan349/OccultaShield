# Enhanced GDPR Knowledge Graph Ingestion

Este script mejorado integra datos GDPR de múltiples fuentes para crear un knowledge graph completo en Neo4j.

## Fuentes de Datos

1. **Local JSON files** (incluidos en el proyecto)
   - `gdpr_articles.json` - Artículos del RGPD
   - `gdpr_concepts.json` - Conceptos, tipos de datos, derechos y multas
   - `detection_gdpr_mapping.json` - Mapeo de detecciones a artículos GDPR

2. **GitHub: coolharsh55/GDPRtEXT**
   - Repositorio oficial con textos completos del RGPD en formato JSON
   - URL: https://github.com/coolharsh55/GDPRtEXT
   - Se descarga automáticamente durante la ingesta

3. **Kaggle Datasets** (opcionales)
   - GDPR Articles dataset
   - GDPR-JSON dataset
   - Requiere configuración de Kaggle API (ver abajo)

## Requisitos

### Python Dependencies

```bash
pip install neo4j sentence-transformers requests kaggle python-dotenv
```

### Neo4j Database

Asegúrate de tener Neo4j corriendo:

```bash
# Con Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/Occultashield_neo4j \
  neo4j:latest

# O iniciarlo localmente
neo4j start
```

### Variables de Entorno

Crea un archivo `.env` en el directorio `backend/app` con:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=Occultashield_neo4j
```

## Configuración de Kaggle (Opcional)

Si quieres incluir los datasets de Kaggle:

1. **Crear cuenta en Kaggle**: https://www.kaggle.com
2. **Obtener API credentials**:
   - Ve a: https://www.kaggle.com/settings
   - Scroll hasta "API" section
   - Click "Create New API Token"
   - Se descargará `kaggle.json`

3. **Instalar las credenciales**:
   ```bash
   mkdir -p ~/.kaggle
   cp kaggle.json ~/.kaggle/
   chmod 600 ~/.kaggle/kaggle.json
   ```

4. **Instalar Kaggle API**:
   ```bash
   pip install kaggle
   ```

## Ejecución

### Método 1: Script Mejorado (Recomendado)

```bash
cd /home/gjuan/OccultaShield/backend/app
python scripts/gdpr_ingestion/enhanced_ingest_gdpr.py
```

Este script:
- ✅ Carga datos locales JSON
- ✅ Descarga y procesa GDPRtEXT de GitHub
- ✅ (Opcional) Descarga datasets de Kaggle
- ✅ Crea embeddings para búsqueda semántica
- ✅ Establece relaciones entre nodos
- ✅ Crea índices fulltext

### Método 2: Script Original (Solo datos locales)

```bash
cd /home/gjuan/OccultaShield/backend/app
python scripts/gdpr_ingestion/ingest_gdpr.py
```

## Verificación

Después de la ingesta, verifica el knowledge graph:

```bash
# Conectar a Neo4j Browser: http://localhost:7474

# Verificar artículos
MATCH (a:Article) RETURN count(a) as total_articles

# Ver estructura del grafo
CALL db.schema.visualization()

# Buscar artículo específico
MATCH (a:Article {number: 6})
RETURN a.title, a.content

# Encontrar artículos relacionados con un tipo de detección
MATCH (d:DetectionType {type: "face"})-[:VIOLATES]->(a:Article)
RETURN a.number, a.title

# Buscar artículos con embeddings
MATCH (a:Article)
WHERE a.embedding IS NOT NULL
RETURN count(a) as articles_with_embeddings
```

## Estructura del Knowledge Graph

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
- Verifica que Neo4j esté corriendo: `neo4j status`
- Comprueba las credenciales en `.env`
- Verifica el puerto: `netstat -an | grep 7687`

### Error: "Kaggle API not available"
- Es opcional. El script continuará sin datasets de Kaggle
- Para usar Kaggle, sigue los pasos de configuración arriba

### Error: "Could not download GDPRtEXT"
- Verifica conexión a Internet
- Comprueba que GitHub no esté bloqueado
- El script continuará con datos locales

### Embeddings muy lentos
- Primera ejecución descarga el modelo `all-MiniLM-L6-v2` (~80MB)
- Siguientes ejecuciones serán más rápidas
- Considera usar GPU si está disponible

## Logs de Ejemplo

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

## Próximos Pasos

Después de la ingesta:

1. **Verificar los datos en Neo4j Browser**: http://localhost:7474
2. **Ejecutar el backend**: El módulo de verificación usará automáticamente el knowledge graph
3. **Probar con un video**: Sube un video y verifica que las violaciones GDPR se detecten correctamente

## Referencias

- **GDPRtEXT**: https://github.com/coolharsh55/GDPRtEXT
- **GDPR Official**: https://gdpr-info.eu/
- **Neo4j Docs**: https://neo4j.com/docs/
- **Sentence Transformers**: https://www.sbert.net/
