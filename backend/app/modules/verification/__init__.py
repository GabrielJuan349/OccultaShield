from typing import List, Dict, Any
from modules.verification.parallel_processor import ParallelProcessor
import asyncio

processor = ParallelProcessor()

async def verify_image_detections(image_path: str, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Verify a list of detections for a single image against GDPR rules.
    
    Args:
        image_path: Path to the image file.
        detections: List of detection dictionaries (must contain 'detection_type').
        
    Returns:
        List of verification results corresponding to the detections.
    """
    return await processor.process_batch(image_path, detections)

# Legacy wrapper if needed by other modules, or main entry point
async def verify_video_content(video_id: str, frame_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Verify content for a video (placeholder for batch video processing).
    
    Args:
        video_id: ID of the video
        frame_data: List of objects containing 'image_path' and 'detections'
        
    Returns:
        Aggregated results
    """
    results = []
    for frame in frame_data:
        frame_results = await verify_image_detections(
            frame["image_path"], 
            frame["detections"]
        )
        results.extend(frame_results)
    return results
