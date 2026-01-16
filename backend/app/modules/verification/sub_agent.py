"""Sub-Agent for Individual Detection Verification.

This module implements a sub-agent in the multi-agent verification system.
Each sub-agent is responsible for verifying a single detection by:
1. Retrieving relevant GDPR context from the knowledge graph
2. Analyzing the captured image using Gemma LLM
3. Returning a structured verification result

Example:
    >>> agent = SubAgent(agent_id="agent_1")
    >>> result = await agent.verify(image_path, detection_dict)
"""

from typing import Dict, Any, List
from modules.verification.graph_client import GraphClient
from modules.verification.gemma_client import GemmaClient


class SubAgent:
    """Verification agent for a single GDPR-sensitive detection.

    Orchestrates the retrieval of legal context from Neo4j and
    performs visual analysis using Gemma LLM to determine if
    a detection constitutes a GDPR violation.

    Attributes:
        agent_id: Unique identifier for this agent instance.
        graph_client: Client for GDPR knowledge graph queries.
        gemma_client: Client for Gemma LLM visual analysis.
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.graph_client = GraphClient()
        self.gemma_client = GemmaClient()
        
    async def verify(self, image_path: str, detection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the verification process for a detection.
        """
        detection_type = detection.get("detection_type", "unknown")
        
        # 1. Retrieve Context from Knowledge Graph
        # We get articles relevant to this detection type
        context = await self.graph_client.get_context_for_detection(detection_type)
        
        # Optional: Semantic search if we had a textual description of the scene context
        # semantic_context = await self.graph_client.semantic_search(...)
        
        # 2. Analyze with Gemma
        # We pass the image and the retrieved GDPR context
        analysis_result = await self.gemma_client.analyze_image(
            image_path=image_path,
            context=context,
            detection_type=detection_type
        )
        
        # 3. Augment result
        analysis_result["agent_id"] = self.agent_id
        analysis_result["detection_id"] = detection.get("id")
        
        return analysis_result
