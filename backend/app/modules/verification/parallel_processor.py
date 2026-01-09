import asyncio
from typing import List, Dict, Any
from collections import defaultdict
from .sub_agent import SubAgent
from .consensus_agent import ConsensusAgent
from ...services.progress_manager import progress_manager

class ParallelProcessor:
    """
    Orchestrates the parallel execution of SubAgents with Temporal Consensus.
    
    Temporal Consensus Mode:
    - Groups verification requests by track_id
    - Processes all frames for a track in parallel
    - Aggregates results via ConsensusAgent (union-of-evidence)
    """
    def __init__(self, max_workers: int = 4):
        self.semaphore = asyncio.Semaphore(max_workers)
        self.consensus_agent = ConsensusAgent()
        
    async def process_batch(self, video_id: str, image_path: str, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a batch of detections for a single image.
        """
        requests = [{"image_path": image_path, "detection": d} for d in detections]
        return await self.process_requests(video_id, requests)

    async def process_requests(self, video_id: str, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process verification requests with Temporal Consensus.
        Groups by track_id, processes frames in parallel, then aggregates.
        """
        if not requests:
            return []
        
        # --- Group requests by track_id for consensus ---
        track_requests: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for req in requests:
            track_id = req["detection"].get("track_id")
            track_requests[track_id].append(req)
        
        total_tracks = len(track_requests)
        completed_tracks = 0
        final_results = []
        
        for track_id, track_reqs in track_requests.items():
            # Process all frames for this track in parallel
            frame_tasks = []
            for req in track_reqs:
                frame_tasks.append(self._process_single(req["image_path"], req["detection"]))
            
            frame_results = await asyncio.gather(*frame_tasks)
            
            # Aggregate via ConsensusAgent (Temporal Consensus)
            consensus_result = self.consensus_agent.aggregate(list(frame_results))
            consensus_result["frames_analyzed"] = len(frame_results)
            consensus_result["track_id"] = track_id
            consensus_result["detection_id"] = track_reqs[0]["detection"].get("id")
            
            final_results.append(consensus_result)
            
            completed_tracks += 1
            await progress_manager.report_verification(
                video_id, 
                str(track_id), 
                "consensus_verified", 
                completed_tracks, 
                total_tracks
            )
        
        return final_results
        
    async def _process_single(self, image_path: str, detection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single detection with concurrency control.
        """
        async with self.semaphore:
            agent = SubAgent(agent_id=f"agent-{detection.get('detection_type', 'unknown')}")
            try:
                result = await agent.verify(image_path, detection)
                result["frame"] = detection.get("frame")
                result["timestamp"] = detection.get("timestamp")
                return result
            except Exception as e:
                return {
                    "is_violation": False, 
                    "error": str(e), 
                    "confidence": 0, 
                    "detection_id": detection.get("id"),
                    "frame": detection.get("frame")
                }
