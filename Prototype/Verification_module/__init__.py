from typing import Dict, List, Any
from .graph_rag import GDPRVerificationGraph

def verify_video_content(image_path: str, detected_objects: List[str]) -> Dict[str, Any]:
    """
    Main entry point for the Verification Module.
    Uses GraphRAG to verify GDPR compliance of a video frame.
    """
    verifier = GDPRVerificationGraph()
    result = verifier.run(image_path, detected_objects)
    return result
