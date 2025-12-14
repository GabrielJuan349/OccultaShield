import asyncio
from typing import List, Dict, Any
from modules.verification.sub_agent import SubAgent
from modules.verification.consensus_agent import ConsensusAgent

class ParallelProcessor:
    """
    Orchestrates the parallel execution of SubAgents.
    """
    def __init__(self, max_workers: int = 3):
        self.semaphore = asyncio.Semaphore(max_workers)
        self.consensus_agent = ConsensusAgent()
        
    async def process_batch(self, image_path: str, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a batch of detections for a single image.
        """
        tasks = []
        for detection in detections:
            tasks.append(self._process_single(image_path, detection))
            
        results = await asyncio.gather(*tasks)
        return results
        
    async def _process_single(self, image_path: str, detection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single detection with concurrency control.
        """
        async with self.semaphore:
            # In a full agentic system, we might spawn a new agent per task
            # Here we reuse a stateless agent or instantiate per task
            agent = SubAgent(agent_id=f"agent-{detection.get('detection_type')}")
            result = await agent.verify(image_path, detection)
            
            # Here we could have multiple agents verifying the SAME detection and consensus
            # For Phase 1, it's 1 agent per detection.
            
            validated = self.consensus_agent.aggregate([result])
            return validated
