import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

# Try importing transformers, but handle gracefully if not installed yet
try:
    import torch
    from transformers import AutoProcessor, AutoModelForConditionalGeneration
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from config.config_loader import get_config

logger = logging.getLogger(__name__)

class GemmaClient:
    _instance = None
    _model = None
    _processor = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GemmaClient, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Prevent re-init
        if hasattr(self, 'config'):
            return
            
        self.config = get_config()
        self.model_id = self.config.verification.get("llm_model", "google/gemma-3-4b-it")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()
        
    def _load_model(self):
        if not TRANSFORMERS_AVAILABLE:
            logger.error("Transformers library not available. Verification will fail.")
            return

        try:
            logger.info(f"Loading Gemma model: {self.model_id} on {self.device}")
            # Placeholder for actual loading logic - adjusted for multimodal if needed
            # Assuming a multimodal capable model class or similar
            # self._processor = AutoProcessor.from_pretrained(self.model_id)
            # self._model = AutoModelForConditionalGeneration.from_pretrained(
            #     self.model_id, 
            #     torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            #     device_map=self.device
            # )
            pass 
        except Exception as e:
            logger.error(f"Failed to load Gemma model: {e}")

    async def analyze_image(self, image_path: str, context: List[Dict[str, Any]], detection_type: str) -> Dict[str, Any]:
        """
        Analyze an image with provided GDPR context using Gemma.
        """
        if not TRANSFORMERS_AVAILABLE:
            return self._mock_response(detection_type)

        prompt = self._build_prompt(context, detection_type)
        
        # Here would be the actual inference calls:
        # inputs = self._processor(text=prompt, images=image, return_tensors="pt").to(self.device)
        # generated_ids = self._model.generate(**inputs, max_new_tokens=512)
        # response_text = self._processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        # Mocking response for now as we don't have the model weights
        return self._mock_response(detection_type)

    def _build_prompt(self, context: List[Dict[str, Any]], detection_type: str) -> str:
        context_str = "\n".join([
            f"- Article {item['article_number']} ({item.get('title', '')}): {item.get('content', '')[:200]}..."
            for item in context
        ])
        
        return f"""You are a GDPR Compliance Expert.
        
        TASK: Analyze the provided image trace for a '{detection_type}' detection.
        
        RELEVANT GDPR CONTEXT:
        {context_str}
        
        INSTRUCTIONS:
        1. Determine if this specific detection constitutes a GDPR violation.
        2. Assign a severity level (none, low, medium, high, critical).
        3. Recommend an action (blur, pixelate, mask, no_action).
        
        OUTPUT FORMAT: JSON only.
        {{
            "is_violation": boolean,
            "severity": "string",
            "violated_articles": ["string"],
            "reasoning": "string",
            "recommended_action": "string",
            "confidence": float
        }}
        """

    def _mock_response(self, detection_type: str) -> Dict[str, Any]:
        """Mock response for development/testing without GPU."""
        is_violation = True
        severity = "medium"
        
        if detection_type == "face":
            severity = "high"
        elif detection_type == "license_plate":
            severity = "high"
        elif detection_type == "person":
             severity = "medium"
             
        return {
            "is_violation": is_violation,
            "severity": severity,
            "violated_articles": ["6", "9"] if detection_type == "face" else ["6"],
            "detected_personal_data": ["biometric_data"] if detection_type == "face" else ["personal_data"],
            "description": f"Detected {detection_type} which constitutes personal data.",
            "recommended_action": "blur",
            "confidence": 0.95,
            "legal_basis_required": "consent"
        }
