import os
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, AsyncGraphDatabase
from db.neo4j_queries import GDPRQueries

class GraphClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GraphClient, cls).__new__(cls)
            cls._instance._init_driver()
        return cls._instance
    
    def _init_driver(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        
    async def close(self):
        if self.driver:
            await self.driver.close()
            
    async def get_context_for_detection(self, detection_type: str) -> List[Dict[str, Any]]:
        """
        Retrieve relevant GDPR context for a specific detection type.
        """
        async with self.driver.session() as session:
            result = await session.run(
                GDPRQueries.GET_ARTICLES_FOR_DETECTION,
                {"detection_type": detection_type}
            )
            records = await result.data()
            return records
            
    async def semantic_search(self, embedding: List[float], threshold: float = 0.7, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Perform semantic search using vector embeddings.
        """
        async with self.driver.session() as session:
            result = await session.run(
                GDPRQueries.SEMANTIC_SEARCH,
                {
                    "query_embedding": embedding,
                    "threshold": threshold,
                    "limit": limit
                }
            )
            return await result.data()
            
    async def get_fine_info(self, article_number: int) -> Optional[Dict[str, Any]]:
        """
        Get fine information for a specific article.
        """
        async with self.driver.session() as session:
            result = await session.run(
                GDPRQueries.GET_FINE_INFO,
                {"article_number": article_number}
            )
            record = await result.single()
            return record.data() if record else None

    async def get_explanation_graph(self, detection_type: str) -> Dict[str, Any]:
        """
        Get graph data for explainability.
        """
        async with self.driver.session() as session:
            result = await session.run(
                GDPRQueries.GET_EXPLANATION_GRAPH,
                {"detection_type": detection_type}
            )
            record = await result.single()
            return record.data() if record else {}
