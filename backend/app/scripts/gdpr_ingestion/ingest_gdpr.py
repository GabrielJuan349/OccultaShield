import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any
from neo4j import GraphDatabase, AsyncGraphDatabase
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
DATA_DIR = Path(__file__).parent / "json_data"

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

class GDPRIngestionPipeline:
    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.stats = GDPRStats()
        
    async def close(self):
        await self.driver.close()
        
    async def run(self):
        """Execute the full ingestion pipeline."""
        print("🚀 Starting GDPR Knowledge Graph Ingestion...")
        
        try:
            await self._clean_database()
            await self._create_constraints()
            await self._load_articles()
            await self._load_concepts()
            await self._load_data_types()
            await self._load_rights()
            await self._load_fines()
            await self._load_detection_mappings()
            await self._create_relationships()
            await self._generate_embeddings()
            await self._create_fulltext_index()
            self._print_summary()
            
        except Exception as e:
            print(f"❌ Error during ingestion: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close()
            
    async def _clean_database(self):
        """Clean existing data."""
        print("\n🧹 Cleaning existing database...")
        async with self.driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        print("✅ Database cleaned")

    async def _create_constraints(self):
        """Create constraints and indices."""
        print("\n🔒 Creating constraints...")
        
        constraints = [
            "CREATE CONSTRAINT article_number IF NOT EXISTS FOR (a:Article) REQUIRE a.number IS UNIQUE",
            "CREATE CONSTRAINT chapter_number IF NOT EXISTS FOR (c:Chapter) REQUIRE c.number IS UNIQUE",
            "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT datatype_id IF NOT EXISTS FOR (d:DataType) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT detection_type IF NOT EXISTS FOR (d:DetectionType) REQUIRE d.type IS UNIQUE",
            "CREATE CONSTRAINT right_id IF NOT EXISTS FOR (r:Right) REQUIRE r.id IS UNIQUE"
        ]
        
        indexes = [
            "CREATE INDEX article_fine_tier IF NOT EXISTS FOR (a:Article) ON (a.fine_tier)",
            "CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name)",
            "CREATE INDEX datatype_special IF NOT EXISTS FOR (d:DataType) ON (d.is_special_category)",
        ]
        
        async with self.driver.session() as session:
            for constraint in constraints:
                await session.run(constraint)
            for index in indexes:
                await session.run(index)
        
        print("✅ Constraints and indices created")

    async def _load_articles(self):
        """Load GDPR articles."""
        print("\n📜 Loading GDPR articles...")
        
        with open(DATA_DIR / "gdpr_articles.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        async with self.driver.session() as session:
            for chapter in data["chapters"]:
                # Create Chapter
                await session.run("""
                    MERGE (c:Chapter {number: $number})
                    SET c.title = $title
                """, {
                    "number": chapter["number"],
                    "title": chapter["title"]
                })
                self.stats.chapters += 1
                
                for article in chapter["articles"]:
                    full_content = self._build_article_content(article)
                    
                    # Create Article
                    await session.run("""
                        MATCH (ch:Chapter {number: $chapter_number})
                        MERGE (a:Article {number: $number})
                        SET a.title = $title,
                            a.content = $content,
                            a.full_text = $full_text,
                            a.fine_tier = $fine_tier,
                            a.keywords = $keywords
                        MERGE (ch)-[:CONTAINS]->(a)
                    """, {
                        "chapter_number": chapter["number"],
                        "number": article["number"],
                        "title": article["title"],
                        "content": article["paragraphs"][0]["text"] if article["paragraphs"] else "",
                        "full_text": full_content,
                        "fine_tier": article.get("fine_tier"),
                        "keywords": article.get("keywords", [])
                    })
                    self.stats.articles += 1
                    
                    # Create Paragraphs
                    for para in article["paragraphs"]:
                        para_text = para["text"]
                        if "points" in para:
                            points_text = "\n".join([
                                f"({p['letter']}) {p['text']}" 
                                for p in para["points"]
                            ])
                            para_text += "\n" + points_text
                        
                        await session.run("""
                            MATCH (a:Article {number: $article_number})
                            MERGE (p:Paragraph {article: $article_number, number: $number})
                            SET p.text = $text
                            MERGE (a)-[:HAS_PARAGRAPH]->(p)
                        """, {
                            "article_number": article["number"],
                            "number": para["number"],
                            "text": para_text
                        })
                        self.stats.paragraphs += 1
                    
                    # Create relationships with Recitals (Mocking Recitals as stubs if they don't exist yet)
                    for recital_num in article.get("related_recitals", []):
                        await session.run("""
                            MATCH (a:Article {number: $article_number})
                            MERGE (r:Recital {number: $recital_number})
                            MERGE (a)-[:EXPLAINED_BY]->(r)
                        """, {
                            "article_number": article["number"],
                            "recital_number": recital_num
                        })
                        self.stats.recitals += 1 # Counting refs here as mock load
                        self.stats.relationships += 1
        
        print(f"✅ Loaded articles from {self.stats.chapters} chapters")

    def _build_article_content(self, article: dict) -> str:
        parts = [f"Article {article['number']} - {article['title']}"]
        for para in article["paragraphs"]:
            parts.append(f"\n{para['number']}. {para['text']}")
            if "points" in para:
                for point in para["points"]:
                    parts.append(f"   ({point['letter']}) {point['text']}")
        return "\n".join(parts)

    async def _load_concepts(self):
        print("\n💡 Loading concepts...")
        with open(DATA_DIR / "gdpr_concepts.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            
        async with self.driver.session() as session:
            for concept in data["concepts"]:
                await session.run("""
                    MERGE (c:Concept {id: $id})
                    SET c.name = $name,
                        c.definition = $definition,
                        c.synonyms = $synonyms,
                        c.article_reference = $article_reference
                """, {
                    "id": concept["id"],
                    "name": concept["name"],
                    "definition": concept["definition"],
                    "synonyms": concept.get("synonyms", []),
                    "article_reference": concept.get("article_reference", "")
                })
                self.stats.concepts += 1
                
                for article_num in concept.get("related_articles", []):
                    await session.run("""
                        MATCH (c:Concept {id: $concept_id})
                        MATCH (a:Article {number: $article_number})
                        MERGE (a)-[:DEFINES]->(c)
                    """, {
                        "concept_id": concept["id"],
                        "article_number": article_num
                    })
                    self.stats.relationships += 1
                    
                if "parent_concept" in concept:
                    await session.run("""
                        MATCH (c:Concept {id: $concept_id})
                        MATCH (parent:Concept {id: $parent_id})
                        MERGE (c)-[:SUBTYPE_OF]->(parent)
                    """, {
                        "concept_id": concept["id"],
                        "parent_id": concept["parent_concept"]
                    })

    async def _load_data_types(self):
        print("\n📊 Loading data types...")
        with open(DATA_DIR / "gdpr_concepts.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        async with self.driver.session() as session:
            for dt in data["data_types"]:
                await session.run("""
                    MERGE (d:DataType {id: $id})
                    SET d.name = $name,
                        d.definition = $definition,
                        d.examples = $examples,
                        d.is_special_category = $is_special_category,
                        d.article_reference = $article_reference,
                        d.detection_types = $detection_types
                """, {
                    "id": dt["id"],
                    "name": dt["name"],
                    "definition": dt["definition"],
                    "examples": dt.get("examples", []),
                    "is_special_category": dt.get("is_special_category", False),
                    "article_reference": dt.get("article_reference", ""),
                    "detection_types": dt.get("detection_types", [])
                })
                self.stats.data_types += 1

    async def _load_rights(self):
        print("\n⚖️ Loading rights...")
        with open(DATA_DIR / "gdpr_concepts.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        async with self.driver.session() as session:
            for right in data["rights"]:
                await session.run("""
                    MERGE (r:Right {id: $id})
                    SET r.name = $name,
                        r.description = $description,
                        r.article_number = $article_number
                """, {
                    "id": right["id"],
                    "name": right["name"],
                    "description": right["description"],
                    "article_number": right["article"]
                })
                self.stats.rights += 1
                
                await session.run("""
                    MATCH (r:Right {id: $right_id})
                    MATCH (a:Article {number: $article_number})
                    MERGE (a)-[:GRANTS]->(r)
                """, {
                    "right_id": right["id"],
                    "article_number": right["article"]
                })

    async def _load_fines(self):
        print("\n💰 Loading fines...")
        with open(DATA_DIR / "gdpr_concepts.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        async with self.driver.session() as session:
            for fine in data["fines"]:
                await session.run("""
                    MERGE (f:Fine {tier: $tier})
                    SET f.max_amount = $max_amount,
                        f.description = $description
                """, {
                    "tier": fine["tier"],
                    "max_amount": fine["max_amount"],
                    "description": fine["description"]
                })
                self.stats.fines += 1
                
                for article_num in fine["applies_to_articles"]:
                    await session.run("""
                        MATCH (f:Fine {tier: $tier})
                        MATCH (a:Article {number: $article_number})
                        MERGE (f)-[:APPLIES_TO]->(a)
                    """, {
                        "tier": fine["tier"],
                        "article_number": article_num
                    })

    async def _load_detection_mappings(self):
        print("\n🎯 Loading detection mappings...")
        with open(DATA_DIR / "detection_gdpr_mapping.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            
        async with self.driver.session() as session:
            for mapping in data["detection_mappings"]:
                impl = mapping["gdpr_implications"]
                
                await session.run("""
                    MERGE (d:DetectionType {type: $type})
                    SET d.data_type = $data_type,
                        d.is_special_category = $is_special_category,
                        d.severity = $severity,
                        d.requires_explicit_consent = $requires_explicit_consent,
                        d.reasoning_template = $reasoning_template,
                        d.recommended_actions = $recommended_actions,
                        d.fine_tier = $fine_tier
                """, {
                    "type": mapping["detection_type"],
                    "data_type": impl["data_type"],
                    "is_special_category": impl["is_special_category"],
                    "severity": impl["severity"],
                    "requires_explicit_consent": impl["requires_explicit_consent"],
                    "reasoning_template": impl["reasoning_template"],
                    "recommended_actions": impl["recommended_actions"],
                    "fine_tier": impl["fine_tier"]
                })
                
                for article_num in impl["primary_articles"]:
                    await session.run("""
                        MATCH (d:DetectionType {type: $type})
                        MATCH (a:Article {number: $article_number})
                        MERGE (d)-[:VIOLATES]->(a)
                    """, {
                        "type": mapping["detection_type"],
                        "article_number": article_num
                    })

    async def _create_relationships(self):
        print("\n🔗 Creating additional relationships...")
        async with self.driver.session() as session:
            # Articles referencing others (basic check)
            await session.run("""
                MATCH (a:Article)
                WHERE a.full_text CONTAINS 'Article'
                WITH a, [x IN range(1, 99) WHERE a.full_text CONTAINS ('Article ' + toString(x))] AS refs
                UNWIND refs AS ref_num
                MATCH (ref:Article {number: ref_num})
                WHERE a.number <> ref_num
                MERGE (a)-[:REFERENCES]->(ref)
            """)
            
            # DataTypes -> Protected By Article 9
            await session.run("""
                MATCH (d:DataType)
                WHERE d.is_special_category = true
                MATCH (a:Article {number: 9})
                MERGE (d)-[:PROTECTED_BY]->(a)
            """)

    async def _generate_embeddings(self):
        print("\n🧮 Generating embeddings...")
        
        async with self.driver.session() as session:
            # Articles
            result = await session.run("MATCH (a:Article) RETURN a.number AS number, a.title AS title, a.full_text AS text")
            articles = await result.data()
            
            for article in articles:
                text = f"{article['title']}. {article['text']}"
                embedding = self.embedder.encode(text).tolist()
                
                await session.run("""
                    MATCH (a:Article {number: $number})
                    SET a.embedding = $embedding
                """, {"number": article["number"], "embedding": embedding})
            
            # Concepts
            result = await session.run("MATCH (c:Concept) RETURN c.id AS id, c.name AS name, c.definition AS definition")
            concepts = await result.data()
            
            for concept in concepts:
                text = f"{concept['name']}. {concept['definition']}"
                embedding = self.embedder.encode(text).tolist()
                
                await session.run("""
                    MATCH (c:Concept {id: $id})
                    SET c.embedding = $embedding
                """, {"id": concept["id"], "embedding": embedding})
                
        print(f"✅ Embeddings generated for {len(articles)} articles and {len(concepts)} concepts")

    async def _create_fulltext_index(self):
        print("\n🔍 Creating fulltext indices...")
        async with self.driver.session() as session:
            await session.run("""
                CREATE FULLTEXT INDEX gdpr_articles_fulltext IF NOT EXISTS
                FOR (a:Article) ON EACH [a.title, a.full_text, a.keywords]
            """)
            await session.run("""
                CREATE FULLTEXT INDEX gdpr_concepts_fulltext IF NOT EXISTS
                FOR (c:Concept) ON EACH [c.name, c.definition, c.synonyms]
            """)
        print("✅ Fulltext indices created")

    def _print_summary(self):
        print("\n" + "="*60)
        print("📊 INGESTION SUMMARY")
        print("="*60)
        print(f"  📁 Chapters:       {self.stats.chapters}")
        print(f"  📜 Articles:       {self.stats.articles}")
        print(f"  💡 Concepts:       {self.stats.concepts}")
        print(f"  📊 Data Types:     {self.stats.data_types}")
        print("="*60)
        print("✅ INGESTION COMPLETED")

async def main():
    pipeline = GDPRIngestionPipeline()
    await pipeline.run()

if __name__ == "__main__":
    asyncio.run(main())
