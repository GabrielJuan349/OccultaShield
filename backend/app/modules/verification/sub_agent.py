from typing import Dict, Any, List
from modules.verification.graph_client import GraphClient
from modules.verification.gemma_client import GemmaClient

class SubAgent:
    """
    Agent responsible for verifying a single detection.
    Orchestrates the retrieval of context and the LLM analysis.
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
