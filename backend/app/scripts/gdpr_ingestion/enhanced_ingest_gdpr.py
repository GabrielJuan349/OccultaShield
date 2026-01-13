#!/usr/bin/env python3
"""
Enhanced GDPR Ingestion Pipeline
Integrates data from multiple sources:
1. Local JSON files (existing)
2. Kaggle GDPR Articles dataset
3. Kaggle GDPR-JSON dataset
4. GitHub coolharsh55/GDPRtEXT repository
"""

import os
import json
import asyncio
import requests
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from neo4j import AsyncGraphDatabase
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import tempfile
import shutil

# Load environment variables
load_dotenv()

# Constants
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
DATA_DIR = Path(__file__).parent / "json_data"
TEMP_DIR = Path(tempfile.gettempdir()) / "gdpr_ingestion"

# Dataset URLs
GDPRTEXT_REPO = "https://raw.githubusercontent.com/coolharsh55/GDPRtEXT/master"
KAGGLE_API_AVAILABLE = False

try:
    import kaggle
    KAGGLE_API_AVAILABLE = True

    # Check for kaggle.json in project directory first
    PROJECT_KAGGLE_DIR = Path(__file__).parent.parent.parent / ".kaggle"
    PROJECT_KAGGLE_CONFIG = PROJECT_KAGGLE_DIR / "kaggle.json"

    if PROJECT_KAGGLE_CONFIG.exists():
        # Set KAGGLE_CONFIG_DIR to use project-local credentials
        os.environ["KAGGLE_CONFIG_DIR"] = str(PROJECT_KAGGLE_DIR)
        print(f"✅ Using Kaggle credentials from: {PROJECT_KAGGLE_CONFIG}")
    elif Path.home().joinpath(".kaggle", "kaggle.json").exists():
        print(f"✅ Using Kaggle credentials from: ~/.kaggle/kaggle.json")
    else:
        print("⚠️  Kaggle credentials not found. Kaggle datasets will be skipped.")
        KAGGLE_API_AVAILABLE = False

except ImportError:
    print("⚠️  Kaggle API not available. Install with: pip install kaggle")

class GDPRStats:
    def __init__(self):
        self.chapters = 0
        self.articles = 0
        self.paragraphs = 0
        self.recitals = 0
        self.concepts = 0
        self.data_types = 0
        self.rights = 0
        self.fines = 0
        self.relationships = 0
        self.external_sources = 0

class EnhancedGDPRIngestion:
    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.stats = GDPRStats()
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

    async def close(self):
        await self.driver.close()
        # Clean temp directory
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR)

    async def run(self):
        """Execute the full enhanced ingestion pipeline."""
        print("🚀 Starting Enhanced GDPR Knowledge Graph Ingestion...")
        print("="*70)

        try:
            # Phase 1: Core data
            print("\n📦 PHASE 1: Loading core GDPR data...")
            await self._clean_database()
            await self._create_constraints()
            await self._load_local_data()

            # Phase 2: External sources
            print("\n🌐 PHASE 2: Loading external GDPR sources...")
            await self._load_gdprtext_repo()

            if KAGGLE_API_AVAILABLE:
                await self._load_kaggle_datasets()
            else:
                print("⚠️  Skipping Kaggle datasets (API not configured)")

            # Phase 3: Enrichment
            print("\n✨ PHASE 3: Enriching knowledge graph...")
            await self._create_relationships()
            await self._generate_embeddings()
            await self._create_fulltext_index()

            self._print_summary()

        except Exception as e:
            print(f"\n❌ Error during ingestion: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close()

    async def _clean_database(self):
        """Clean existing GDPR data."""
        print("🧹 Cleaning existing database...")
        async with self.driver.session() as session:
            # Only delete GDPR-related nodes to preserve other data
            await session.run("""
                MATCH (n) WHERE n:Article OR n:Chapter OR n:Concept OR
                              n:DataType OR n:DetectionType OR n:Right OR
                              n:Fine OR n:Recital OR n:Paragraph
                DETACH DELETE n
            """)
        print("✅ Database cleaned")

    async def _create_constraints(self):
        """Create constraints and indices."""
        print("🔒 Creating constraints...")

        constraints = [
            "CREATE CONSTRAINT article_number IF NOT EXISTS FOR (a:Article) REQUIRE a.number IS UNIQUE",
            "CREATE CONSTRAINT chapter_number IF NOT EXISTS FOR (c:Chapter) REQUIRE c.number IS UNIQUE",
            "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT datatype_id IF NOT EXISTS FOR (d:DataType) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT detection_type IF NOT EXISTS FOR (d:DetectionType) REQUIRE d.type IS UNIQUE",
            "CREATE CONSTRAINT right_id IF NOT EXISTS FOR (r:Right) REQUIRE r.id IS UNIQUE",
            "CREATE CONSTRAINT recital_number IF NOT EXISTS FOR (r:Recital) REQUIRE r.number IS UNIQUE"
        ]

        indexes = [
            "CREATE INDEX article_fine_tier IF NOT EXISTS FOR (a:Article) ON (a.fine_tier)",
            "CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name)",
            "CREATE INDEX datatype_special IF NOT EXISTS FOR (d:DataType) ON (d.is_special_category)",
            "CREATE INDEX article_source IF NOT EXISTS FOR (a:Article) ON (a.source)"
        ]

        async with self.driver.session() as session:
            for constraint in constraints:
                try:
                    await session.run(constraint)
                except Exception as e:
                    print(f"   Warning: {e}")
            for index in indexes:
                try:
                    await session.run(index)
                except Exception as e:
                    print(f"   Warning: {e}")

        print("✅ Constraints and indices created")

    async def _load_local_data(self):
        """Load data from local JSON files."""
        print("📜 Loading local GDPR data...")

        # Use existing ingestion logic from original script
        from ingest_gdpr import GDPRIngestionPipeline
        local_pipeline = GDPRIngestionPipeline()
        local_pipeline.driver = self.driver
        local_pipeline.embedder = self.embedder
        local_pipeline.stats = self.stats

        await local_pipeline._load_articles()
        await local_pipeline._load_concepts()
        await local_pipeline._load_data_types()
        await local_pipeline._load_rights()
        await local_pipeline._load_fines()
        await local_pipeline._load_detection_mappings()

        print("✅ Local data loaded")

    async def _load_gdprtext_repo(self):
        """Load GDPR text from coolharsh55/GDPRtEXT repository."""
        print("\n📥 Downloading GDPRtEXT repository data...")

        try:
            # Download GDPR articles in JSON format
            articles_url = f"{GDPRTEXT_REPO}/gdpr.json"
            response = requests.get(articles_url, timeout=30)

            if response.status_code == 200:
                gdpr_data = response.json()
                await self._process_gdprtext_data(gdpr_data)
                self.stats.external_sources += 1
                print("✅ GDPRtEXT data loaded")
            else:
                print(f"⚠️  Could not download GDPRtEXT: HTTP {response.status_code}")

        except Exception as e:
            print(f"⚠️  Error loading GDPRtEXT: {e}")

    async def _process_gdprtext_data(self, data: Dict[str, Any]):
        """Process and load GDPRtEXT JSON data into Neo4j."""
        print("   Processing GDPRtEXT articles...")

        async with self.driver.session() as session:
            # Process articles
            if "articles" in data:
                for article in data["articles"]:
                    article_num = article.get("number", article.get("id"))

                    await session.run("""
                        MERGE (a:Article {number: $number})
                        ON CREATE SET
                            a.title = $title,
                            a.content = $content,
                            a.source = 'GDPRtEXT'
                        ON MATCH SET
                            a.gdprtext_content = $content,
                            a.gdprtext_title = $title
                    """, {
                        "number": article_num,
                        "title": article.get("title", ""),
                        "content": article.get("text", article.get("content", ""))
                    })

            # Process recitals if available
            if "recitals" in data:
                for recital in data["recitals"]:
                    recital_num = recital.get("number", recital.get("id"))

                    await session.run("""
                        MERGE (r:Recital {number: $number})
                        SET r.text = $text,
                            r.source = 'GDPRtEXT'
                    """, {
                        "number": recital_num,
                        "text": recital.get("text", recital.get("content", ""))
                    })

    async def _load_kaggle_datasets(self):
        """Load GDPR datasets from Kaggle."""
        print("\n📥 Downloading Kaggle GDPR datasets...")

        try:
            # Dataset 1: GDPR Articles
            print("   Downloading: GDPR Articles...")
            self._download_kaggle_dataset("dataset1/gdpr-articles", "gdpr_articles")

            # Dataset 2: GDPR-JSON
            print("   Downloading: GDPR-JSON...")
            self._download_kaggle_dataset("dataset2/gdpr-json", "gdpr_json")

            # Process downloaded datasets
            await self._process_kaggle_files()
            self.stats.external_sources += 2

        except Exception as e:
            print(f"⚠️  Error loading Kaggle datasets: {e}")

    def _download_kaggle_dataset(self, dataset_name: str, output_name: str):
        """Download a dataset from Kaggle using API."""
        try:
            output_dir = TEMP_DIR / output_name
            output_dir.mkdir(parents=True, exist_ok=True)
            kaggle.api.dataset_download_files(dataset_name, path=str(output_dir), unzip=True)
            print(f"   ✅ Downloaded: {output_name}")
        except Exception as e:
            print(f"   ⚠️  Could not download {dataset_name}: {e}")

    async def _process_kaggle_files(self):
        """Process downloaded Kaggle files."""
        print("   Processing Kaggle files...")

        # Process GDPR Articles
        articles_dir = TEMP_DIR / "gdpr_articles"
        if articles_dir.exists():
            await self._process_kaggle_articles(articles_dir)

        # Process GDPR-JSON
        json_dir = TEMP_DIR / "gdpr_json"
        if json_dir.exists():
            await self._process_kaggle_json(json_dir)

    async def _process_kaggle_articles(self, directory: Path):
        """Process Kaggle GDPR Articles dataset."""
        for file_path in directory.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                async with self.driver.session() as session:
                    if isinstance(data, list):
                        for article in data:
                            await session.run("""
                                MERGE (a:Article {number: $number})
                                ON MATCH SET
                                    a.kaggle_content = $content,
                                    a.kaggle_title = $title
                            """, {
                                "number": article.get("article_number", article.get("number")),
                                "title": article.get("title", ""),
                                "content": article.get("content", article.get("text", ""))
                            })
            except Exception as e:
                print(f"   ⚠️  Error processing {file_path.name}: {e}")

    async def _process_kaggle_json(self, directory: Path):
        """Process Kaggle GDPR-JSON dataset."""
        for file_path in directory.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Process based on file structure
                if "chapters" in data:
                    await self._process_gdpr_chapters(data)
                elif "articles" in data:
                    await self._process_gdpr_articles_list(data["articles"])

            except Exception as e:
                print(f"   ⚠️  Error processing {file_path.name}: {e}")

    async def _process_gdpr_chapters(self, data: Dict[str, Any]):
        """Process GDPR data organized by chapters."""
        async with self.driver.session() as session:
            for chapter in data.get("chapters", []):
                for article in chapter.get("articles", []):
                    await session.run("""
                        MERGE (a:Article {number: $number})
                        ON MATCH SET
                            a.extended_content = $content
                    """, {
                        "number": article.get("number"),
                        "content": json.dumps(article, ensure_ascii=False)
                    })

    async def _process_gdpr_articles_list(self, articles: List[Dict[str, Any]]):
        """Process list of GDPR articles."""
        async with self.driver.session() as session:
            for article in articles:
                await session.run("""
                    MERGE (a:Article {number: $number})
                    ON MATCH SET
                        a.additional_data = $data
                """, {
                    "number": article.get("number", article.get("id")),
                    "data": json.dumps(article, ensure_ascii=False)
                })

    async def _create_relationships(self):
        """Create additional relationships in the graph."""
        print("🔗 Creating relationships...")

        async with self.driver.session() as session:
            # Articles referencing others
            await session.run("""
                MATCH (a:Article)
                WHERE a.full_text CONTAINS 'Article' OR a.content CONTAINS 'Article'
                WITH a, [x IN range(1, 99) WHERE
                    (a.full_text IS NOT NULL AND a.full_text CONTAINS ('Article ' + toString(x))) OR
                    (a.content IS NOT NULL AND a.content CONTAINS ('Article ' + toString(x)))
                ] AS refs
                UNWIND refs AS ref_num
                MATCH (ref:Article {number: ref_num})
                WHERE a.number <> ref_num
                MERGE (a)-[:REFERENCES]->(ref)
            """)

            # DataTypes protected by Article 9
            await session.run("""
                MATCH (d:DataType)
                WHERE d.is_special_category = true
                MATCH (a:Article {number: 9})
                MERGE (d)-[:PROTECTED_BY]->(a)
            """)

            # Connect Recitals to Articles
            await session.run("""
                MATCH (r:Recital), (a:Article)
                WHERE r.text CONTAINS ('Article ' + toString(a.number))
                MERGE (r)-[:EXPLAINS]->(a)
            """)

        print("✅ Relationships created")

    async def _generate_embeddings(self):
        """Generate embeddings for semantic search."""
        print("🧮 Generating embeddings...")

        async with self.driver.session() as session:
            # Articles
            result = await session.run("""
                MATCH (a:Article)
                WHERE a.embedding IS NULL
                RETURN a.number AS number, a.title AS title,
                       coalesce(a.full_text, a.content, a.gdprtext_content) AS text
            """)
            articles = await result.data()

            for article in articles:
                if article['text']:
                    text = f"{article['title']}. {article['text']}"
                    embedding = self.embedder.encode(text[:512]).tolist()  # Limit length

                    await session.run("""
                        MATCH (a:Article {number: $number})
                        SET a.embedding = $embedding
                    """, {"number": article["number"], "embedding": embedding})

            # Concepts
            result = await session.run("""
                MATCH (c:Concept)
                WHERE c.embedding IS NULL
                RETURN c.id AS id, c.name AS name, c.definition AS definition
            """)
            concepts = await result.data()

            for concept in concepts:
                text = f"{concept['name']}. {concept['definition']}"
                embedding = self.embedder.encode(text[:512]).tolist()

                await session.run("""
                    MATCH (c:Concept {id: $id})
                    SET c.embedding = $embedding
                """, {"id": concept["id"], "embedding": embedding})

        print(f"✅ Embeddings generated")

    async def _create_fulltext_index(self):
        """Create fulltext search indices."""
        print("🔍 Creating fulltext indices...")

        async with self.driver.session() as session:
            try:
                await session.run("""
                    CREATE FULLTEXT INDEX gdpr_articles_fulltext IF NOT EXISTS
                    FOR (a:Article) ON EACH [a.title, a.full_text, a.content, a.keywords]
                """)
                await session.run("""
                    CREATE FULLTEXT INDEX gdpr_concepts_fulltext IF NOT EXISTS
                    FOR (c:Concept) ON EACH [c.name, c.definition, c.synonyms]
                """)
                await session.run("""
                    CREATE FULLTEXT INDEX gdpr_recitals_fulltext IF NOT EXISTS
                    FOR (r:Recital) ON EACH [r.text]
                """)
            except Exception as e:
                print(f"   ⚠️  Some indices already exist: {e}")

        print("✅ Fulltext indices created")

    def _print_summary(self):
        """Print ingestion summary."""
        print("\n" + "="*70)
        print("📊 ENHANCED INGESTION SUMMARY")
        print("="*70)
        print(f"  📁 Chapters:          {self.stats.chapters}")
        print(f"  📜 Articles:          {self.stats.articles}")
        print(f"  💡 Concepts:          {self.stats.concepts}")
        print(f"  📊 Data Types:        {self.stats.data_types}")
        print(f"  ⚖️  Rights:            {self.stats.rights}")
        print(f"  💰 Fines:             {self.stats.fines}")
        print(f"  🌐 External Sources:  {self.stats.external_sources}")
        print("="*70)
        print("✅ ENHANCED INGESTION COMPLETED")
        print("\n💡 Knowledge graph ready for GDPR compliance verification!")

async def main():
    """Main entry point."""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║  Enhanced GDPR Knowledge Graph Ingestion                  ║
    ║  Sources: Local JSON + GDPRtEXT + Kaggle Datasets        ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    pipeline = EnhancedGDPRIngestion()
    await pipeline.run()

if __name__ == "__main__":
    asyncio.run(main())
