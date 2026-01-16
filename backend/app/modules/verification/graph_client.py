"""Neo4j Graph Database Client for GDPR Knowledge Retrieval.

This module provides an async client for querying the GDPR knowledge graph
stored in Neo4j. It implements caching to reduce database load for
frequently accessed contexts.

Features:
    - Async Neo4j driver support
    - Context caching with configurable TTL
    - Semantic search via vector embeddings
    - GDPR article and fine information retrieval

Example:
    >>> client = GraphClient()
    >>> context = await client.get_context_for_detection("face")
    >>> await client.close()
"""

import os
import time
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, AsyncGraphDatabase
from db.neo4j_queries import GDPRQueries

CACHE_TTL_SECONDS = 300  # 5 minutes


class GraphClient:
    """Async Neo4j client with context caching for GDPR queries.

    Singleton client that manages connections to Neo4j and provides
    cached access to GDPR-related information based on detection types.

    Attributes:
        driver: AsyncGraphDatabase driver instance.
        _context_cache: In-memory cache for context queries.
        _cache_timestamps: Timestamps for cache invalidation.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GraphClient, cls).__new__(cls)
            cls._instance._init_driver()
            cls._instance._context_cache = {}
            cls._instance._cache_timestamps = {}
        return cls._instance
    
    def _init_driver(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        try:
            self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        except Exception as e:
            print(f"Failed to init Neo4j driver: {e}")
            self.driver = None
            
    async def close(self):
        if self.driver:
            await self.driver.close()
    
    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache_timestamps:
            return False
        return (time.time() - self._cache_timestamps[key]) < CACHE_TTL_SECONDS
    
    def clear_cache(self):
        self._context_cache = {}
        self._cache_timestamps = {}
            
    async def get_context_for_detection(self, detection_type: str) -> List[Dict[str, Any]]:
        # Verificar cache primero
        cache_key = f"context:{detection_type}"
        if cache_key in self._context_cache and self._is_cache_valid(cache_key):
            return self._context_cache[cache_key]
        
        if not self.driver:
            # Fallback mock context if DB is not up
            result = [{
                "article_number": "6",
                "title": "Lawfulness of processing",
                "content": "Processing shall be lawful only if..."
            }]
            self._context_cache[cache_key] = result
            self._cache_timestamps[cache_key] = time.time()
            return result
            
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    GDPRQueries.GET_ARTICLES_FOR_DETECTION,
                    {"detection_type": detection_type}
                )
                records = await result.data()
                
                self._context_cache[cache_key] = records
                self._cache_timestamps[cache_key] = time.time()
                
                return records
        except Exception as e:
            print(f"Neo4j Error: {e}")
            return []
            
    async def semantic_search(self, embedding: List[float], threshold: float = 0.7, limit: int = 5) -> List[Dict[str, Any]]:
        if not self.driver: return []
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
        if not self.driver: return None
        async with self.driver.session() as session:
            result = await session.run(
                GDPRQueries.GET_FINE_INFO,
                {"article_number": article_number}
            )
            record = await result.single()
            return record.data() if record else None

    async def get_explanation_graph(self, detection_type: str) -> Dict[str, Any]:
        if not self.driver: return {}
        async with self.driver.session() as session:
            result = await session.run(
                GDPRQueries.GET_EXPLANATION_GRAPH,
                {"detection_type": detection_type}
            )
            record = await result.single()
            return record.data() if record else {}
