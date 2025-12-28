import os
from typing import Optional, List, Dict, Any
from langchain_neo4j import Neo4jGraph, Neo4jVector, GraphCypherQAChain
from langchain_community.embeddings import HuggingFaceEmbeddings
from dotenv import load_dotenv

load_dotenv()


class GraphDB:
    """
    Hybrid Neo4j connection manager supporting:
    - Neo4jGraph: For direct Cypher queries
    - Neo4jVector: For semantic/vector similarity search
    - GraphCypherQAChain: For natural language to Cypher translation
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GraphDB, cls).__new__(cls)
            cls._instance.graph = None
            cls._instance.vector_store = None
            cls._instance.embeddings = None
            cls._instance._initialized = False
        return cls._instance

    def connect(self) -> "GraphDB":
        """Initialize connections to Neo4j (graph + vector store)."""
        if self._initialized:
            return self
            
        self.url = os.environ["NEO4J_URI"]
        self.username = os.environ["NEO4J_USER"]
        self.password = os.environ["NEO4J_PASSWORD"]
        
        # 1. Connect to Neo4jGraph (for Cypher queries)
        try:
            self.graph = Neo4jGraph(
                url=self.url,
                username=self.username,
                password=self.password
            )
            print("✅ Connected to Neo4jGraph")
        except Exception as e:
            print(f"❌ Error connecting to Neo4jGraph: {e}")
            raise e
        
        # 2. Initialize embeddings model (local, no API key needed)
        try:

            embedding_model = os.getenv("EMBEDDING_MODEL")
            if not embedding_model:
                raise ValueError("EMBEDDING_MODEL not set in .env")
                
            self.embeddings = HuggingFaceEmbeddings(
                model_name=embedding_model,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            print(f"✅ Loaded embedding model: {embedding_model}")
        except Exception as e:
            print(f"⚠️ Warning: Could not load embeddings: {e}")
            self.embeddings = None
        
        # 3. Connect to existing Neo4jVector store (if embeddings are available)
        if self.embeddings:
            try:
                self.vector_store = Neo4jVector.from_existing_graph(
                    embedding=self.embeddings,
                    url=self.url,
                    username=self.username,
                    password=self.password,
                    index_name="gdpr_vector_index",
                    node_label="GDPRArticle",
                    text_node_properties=["content", "title"],
                    embedding_node_property="embedding"
                )
                print("✅ Connected to Neo4jVector store")
            except Exception as e:
                print(f"⚠️ Vector store not initialized (run ingest first): {e}")
                self.vector_store = None
        
        self._initialized = True
        return self

    def query(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a raw Cypher query."""
        if not self.graph:
            raise RuntimeError("Graph not connected. Call connect() first.")
        return self.graph.query(cypher, params or {})

    def vector_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform semantic similarity search using embeddings.
        Returns documents most similar to the query.
        """
        if not self.vector_store:
            print("⚠️ Vector store not available. Falling back to keyword search.")
            return []
        
        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
            return [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score
                }
                for doc, score in results
            ]
        except Exception as e:
            print(f"❌ Vector search error: {e}")
            return []

    def hybrid_search(self, query: str, detected_objects: List[str], k: int = 5) -> List[str]:
        """
        Hybrid search combining:
        1. Vector similarity search (semantic)
        2. Cypher keyword search (structured)
        
        Returns deduplicated, ranked context strings.
        """
        context = []
        seen_titles = set()
        
        # --- PART 1: Vector/Semantic Search ---
        if self.vector_store:
            # Build a natural language query from detected objects
            semantic_query = f"GDPR regulations about {', '.join(detected_objects)} personal data privacy protection"
            vector_results = self.vector_search(semantic_query, k=k)
            
            for result in vector_results:
                title = result.get("metadata", {}).get("title", "Unknown")
                if title not in seen_titles:
                    seen_titles.add(title)
                    content = result["content"]
                    score = result.get("score", 0)
                    context.append(f"**{title}** [Relevance: {score:.2f}]\n{content}")
        
        # --- PART 2: Cypher Keyword Search (fallback/supplement) ---
        keyword_mapping = {
            "face": ["biometric", "facial", "special categories", "consent"],
            "person": ["personal data", "data subject", "processing"],
            "license_plate": ["vehicle", "identification", "personal data"],
            "text": ["sensitive", "processing", "personal data"],
        }
        
        search_terms = []
        for obj in detected_objects:
            search_terms.append(obj.lower())
            if obj.lower() in keyword_mapping:
                search_terms.extend(keyword_mapping[obj.lower()])
        
        for term in set(search_terms):
            cypher = """
            MATCH (a:GDPRArticle)
            WHERE toLower(a.content) CONTAINS toLower($term) 
               OR toLower(a.title) CONTAINS toLower($term)
            RETURN DISTINCT a.title as title, a.content as content
            LIMIT 2
            """
            try:
                results = self.query(cypher, {"term": term})
                for r in results:
                    title = r.get("title", "Unknown")
                    if title not in seen_titles:
                        seen_titles.add(title)
                        context.append(f"**{title}**\n{r['content']}")
            except Exception as e:
                print(f"⚠️ Cypher search error for '{term}': {e}")
        
        # --- Fallback if nothing found ---
        if not context:
            context = [
                "**GDPR Article 5 - Principles**\nPersonal data shall be processed lawfully, fairly and transparently.",
                "**GDPR Article 6 - Lawfulness**\nProcessing is lawful only with consent or legal basis.",
                "**GDPR Article 9 - Special Categories**\nBiometric data processing is prohibited unless exceptions apply.",
            ]
        
        return context[:k]  # Limit total results

    def close(self):
        """Close all connections."""
        if self.graph:
            try:
                self.graph._driver.close()
            except:
                pass
            self.graph = None
        self.vector_store = None
        self._initialized = False
        print("Neo4j connections closed.")
