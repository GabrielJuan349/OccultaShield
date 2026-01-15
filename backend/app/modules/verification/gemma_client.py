import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from config.config_loader import get_config

logger = logging.getLogger(__name__)

# Try importing transformers, but handle gracefully if not installed yet
try:
    import torch
    from transformers import AutoProcessor, AutoModelForCausalLM
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    class torch:
        def cuda(self): return False
        is_available = lambda: False
        float16 = None
        float32 = None

# =============================================================================
# VARIABLES Y PROMPTS
# =============================================================================

GDPR_ARTICLES = {
    "face": ["9", "6"],
    "fingerprint": ["9", "6"],
    "license_plate": ["6", "17"],
    "person": ["6", "13"],
    "id_document": ["9", "6", "32"],
    "credit_card": ["6", "32"],
    "signature": ["6"],
}

SENSITIVE_CONTENT_CLASSIFICATION_PROMPT = """
Analyze this image crop and determine if it contains any of the following sensitive content:

1. **Fingerprint**: A finger showing visible ridge patterns (the lines/whorls on fingertips)
2. **ID Document**: Any official identification document (passport, national ID, driver's license, residence permit)
3. **Credit Card**: A bank card, credit card, or debit card showing numbers or chip
4. **Signature**: A handwritten signature or autograph
5. **Hand with biometric features**: A hand that could be used for palm print recognition

IMPORTANT RULES:
- A regular hand holding something is NOT a fingerprint unless ridge patterns are clearly visible
- A blank card or generic plastic is NOT a credit card unless it has numbers/chip visible
- Random text is NOT a signature unless it's clearly a handwritten personal signature

Respond with a JSON object:
{
  "detected_type": "fingerprint|id_document|credit_card|signature|hand_biometric|none",
  "confidence": 0.0 to 1.0,
  "reasoning": "Brief explanation of why this classification was made"
}

If no sensitive content is detected, return:
{
  "detected_type": "none",
  "confidence": 0.9,
  "reasoning": "No sensitive personal data detected in this crop"
}
"""

# =============================================================================
# PROMPT: DESCRIPCIÓN VISUAL OBJETIVA (EL "TESTIGO")
# =============================================================================
VISUAL_DESCRIPTION_PROMPT = """
You are a VISUAL WITNESS. Your job is to DESCRIBE what you see, NOT to make legal judgments.

Analyze this image of a person and provide an OBJECTIVE VISUAL DESCRIPTION.

Respond with a JSON object containing:
{
  "visual_summary": "Detailed description of the person: clothing, posture, apparent activity, and environment",
  "tags": ["list", "of", "relevant", "keywords"],
  "environment": "Description of the setting/background (e.g., beach, hospital, office, street, protest)",
  "clothing_level": "formal|casual|athletic|swimwear|medical|minimal|uniform|religious",
  "visible_biometrics": {
    "face_visible": true/false,
    "tattoos_visible": true/false,
    "scars_visible": true/false,
    "distinctive_marks": "description if any"
  },
  "context_indicators": ["list", "of", "contextual", "clues"],
  "age_group": "child|teenager|adult|elderly|unknown",
  "confidence": 0.0 to 1.0
}

IMPORTANT GUIDELINES:
- Be OBJECTIVE and FACTUAL - describe ONLY what you can see
- DO NOT judge if this is a "violation" or not - that's not your job
- Include relevant tags like: "swimsuit", "hospital_gown", "uniform", "child", "protest_sign", "religious_symbol", "beach", "medical_setting", "office"
- For environment, be specific: "indoor_hospital", "outdoor_beach", "indoor_office", "street_protest"
- For context_indicators, list anything that helps understand the situation

Example response:
{
  "visual_summary": "Adult male in swimming trunks walking on sandy beach, carrying a towel",
  "tags": ["adult", "male", "swimwear", "beach", "outdoor", "recreational"],
  "environment": "outdoor_beach",
  "clothing_level": "swimwear",
  "visible_biometrics": {
    "face_visible": true,
    "tattoos_visible": false,
    "scars_visible": false,
    "distinctive_marks": "none"
  },
  "context_indicators": ["recreational_activity", "public_space", "leisure"],
  "age_group": "adult",
  "confidence": 0.9
}
"""

class GemmaClient:
    """
    Cliente LLM mejorado con:
    - Clasificación de contenido sensible (huellas, documentos, etc.)
    - Análisis de violaciones GDPR
    - Soporte para procesamiento de imágenes con visión
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GemmaClient, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, 'config'):
            return
            
        self.config = get_config()
        self.model_id = self.config.verification.get("llm_model", "google/gemma-3-4b-it")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.processor = None
        self._classification_cache = {}
        
    def _load_model(self):
        """Carga el modelo LLM bajo demanda"""
        if self.model is not None:
            return
            
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("Transformers not available. Using mock mode.")
            self.model = "mock"
            return
            
        try:
            logger.info(f"Loading Gemma model: {self.model_id} on {self.device}")
            self.processor = AutoProcessor.from_pretrained(self.model_id)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id, 
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None
            )
            logger.info("LLM model loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load LLM model: {e}. Using mock responses.")
            self.model = "mock"
            
    async def classify_sensitive_content(self, image_path: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Clasifica si una imagen contiene contenido sensible no detectable por YOLO.
        """
        if use_cache and image_path in self._classification_cache:
            return self._classification_cache[image_path]
        
        if self.model is None:
            self._load_model()
            
        if self.model == "mock":
            result = self._classify_mock(image_path)
        else:
            result = await self._classify_with_llm(image_path)
            
        if use_cache:
            self._classification_cache[image_path] = result
            
        return result
        
    def _classify_mock(self, image_path: str) -> Dict[str, Any]:
        path_lower = image_path.lower()
        if "finger" in path_lower or "huella" in path_lower:
            return {"detected_type": "fingerprint", "confidence": 0.85, "reasoning": "Mock: Filename suggests fingerprint"}
        elif "dni" in path_lower or "passport" in path_lower or "documento" in path_lower:
             return {"detected_type": "id_document", "confidence": 0.85, "reasoning": "Mock: Filename suggests ID"}
        elif "card" in path_lower or "tarjeta" in path_lower or "visa" in path_lower:
             return {"detected_type": "credit_card", "confidence": 0.85, "reasoning": "Mock: Filename suggests credit card"}
        elif "firma" in path_lower or "signature" in path_lower:
             return {"detected_type": "signature", "confidence": 0.80, "reasoning": "Mock: Filename suggests signature"}
             
        return {"detected_type": "none", "confidence": 0.7, "reasoning": "Mock: No sensitive content detected"}

    async def _classify_with_llm(self, image_path: str) -> Dict[str, Any]:
        try:
            from PIL import Image
            image = Image.open(image_path).convert("RGB")
            
            inputs = self.processor(
                text=SENSITIVE_CONTENT_CLASSIFICATION_PROMPT,
                images=image,
                return_tensors="pt"
            ).to(self.device)
            
            outputs = self.model.generate(**inputs, max_new_tokens=200, do_sample=False)
            response = self.processor.decode(outputs[0], skip_special_tokens=True)
            
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                return json.loads(response[json_start:json_end])
            
            return {"detected_type": "none", "confidence": 0.5, "reasoning": "Could not parse LLM response"}
        except Exception as e:
            logger.error(f"LLM classification error: {e}")
            return {"detected_type": "none", "confidence": 0.3, "reasoning": f"Error: {str(e)}"}

    async def analyze_image(self, image_path: str, context: List[Dict[str, Any]], detection_type: str) -> Dict[str, Any]:
        """
        Analiza una imagen. Para "person" actúa como TESTIGO (solo describe).
        Para otros tipos (face, license_plate, etc.) devuelve decisión directa.

        Args:
            image_path: Ruta a la imagen a analizar
            context: Contexto GDPR de Neo4j (no usado para persona - el Juez lo usará)
            detection_type: Tipo de detección (person, face, license_plate, etc.)

        Returns:
            Para "person": Descripción visual objetiva (sin is_violation)
            Para otros: Decisión de violación directa
        """
        # Si el tipo es "unknown" o "hand", intentar clasificar con LLM
        if detection_type in ("unknown", "hand", "hand_crop"):
            classification = await self.classify_sensitive_content(image_path)
            if classification["detected_type"] != "none":
                detection_type = classification["detected_type"]
                logger.info(f"LLM classified {image_path} as {detection_type}")

        # =================================================================
        # PARA "PERSON": Actuar como TESTIGO (solo descripción visual)
        # La decisión legal la tomará el ConsensusAgent (el "Juez")
        # =================================================================
        if detection_type == "person":
            logger.info(f"🔍 [TESTIGO] Generando descripción visual para: {image_path}")
            visual_description = await self._describe_person_visually(image_path)
            visual_description["detection_type"] = "person"
            visual_description["mode"] = "witness"  # Marca que es descripción, no decisión
            return visual_description

        # =================================================================
        # PARA OTROS TIPOS: Decisión directa (face, license_plate, etc.)
        # Estos son siempre violaciones claras sin ambigüedad contextual
        # =================================================================
        return self._determine_violation(detection_type, context)

    async def _describe_person_visually(self, image_path: str) -> Dict[str, Any]:
        """
        MODO TESTIGO: Genera una descripción visual OBJETIVA de una persona.
        NO emite juicios legales. Solo describe lo que ve.
        """
        if self.model is None:
            self._load_model()

        if self.model == "mock":
            return self._mock_visual_description(image_path)

        try:
            from PIL import Image
            image = Image.open(image_path).convert("RGB")

            inputs = self.processor(
                text=VISUAL_DESCRIPTION_PROMPT,
                images=image,
                return_tensors="pt"
            ).to(self.device)

            outputs = self.model.generate(**inputs, max_new_tokens=500, do_sample=False)
            response = self.processor.decode(outputs[0], skip_special_tokens=True)

            # Extraer JSON de la respuesta
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                logger.info(f"🔍 [TESTIGO] Descripción: {result.get('visual_summary', 'N/A')[:100]}...")
                return result

            return self._fallback_visual_description()

        except Exception as e:
            logger.error(f"Error en descripción visual: {e}")
            return self._fallback_visual_description()

    def _mock_visual_description(self, image_path: str) -> Dict[str, Any]:
        """Mock para pruebas cuando el modelo LLM no está disponible."""
        path_lower = image_path.lower()

        # Detectar contexto por nombre de archivo (solo para demo/testing)
        if any(kw in path_lower for kw in ["beach", "playa", "swim", "bikini", "bañador"]):
            return {
                "visual_summary": "Persona en traje de baño en ambiente de playa",
                "tags": ["swimwear", "beach", "outdoor", "recreational", "adult"],
                "environment": "outdoor_beach",
                "clothing_level": "swimwear",
                "visible_biometrics": {"face_visible": True, "tattoos_visible": False, "scars_visible": False, "distinctive_marks": "none"},
                "context_indicators": ["recreational_activity", "public_space", "leisure"],
                "age_group": "adult",
                "confidence": 0.85
            }
        elif any(kw in path_lower for kw in ["hospital", "medical", "doctor", "patient", "clinic"]):
            return {
                "visual_summary": "Persona en bata médica en entorno hospitalario",
                "tags": ["hospital_gown", "medical_setting", "indoor", "healthcare", "patient"],
                "environment": "indoor_hospital",
                "clothing_level": "medical",
                "visible_biometrics": {"face_visible": True, "tattoos_visible": False, "scars_visible": False, "distinctive_marks": "none"},
                "context_indicators": ["medical_context", "healthcare", "vulnerable_situation"],
                "age_group": "adult",
                "confidence": 0.85
            }
        elif any(kw in path_lower for kw in ["protest", "manifestacion", "demonstration"]):
            return {
                "visual_summary": "Persona participando en manifestación pública",
                "tags": ["protest", "outdoor", "political", "crowd", "demonstration"],
                "environment": "street_protest",
                "clothing_level": "casual",
                "visible_biometrics": {"face_visible": True, "tattoos_visible": False, "scars_visible": False, "distinctive_marks": "none"},
                "context_indicators": ["political_activity", "public_gathering", "expression_of_opinion"],
                "age_group": "adult",
                "confidence": 0.80
            }
        elif any(kw in path_lower for kw in ["child", "niño", "kid", "menor", "school"]):
            return {
                "visual_summary": "Menor de edad en entorno cotidiano",
                "tags": ["child", "minor", "casual", "everyday"],
                "environment": "general_public_space",
                "clothing_level": "casual",
                "visible_biometrics": {"face_visible": True, "tattoos_visible": False, "scars_visible": False, "distinctive_marks": "none"},
                "context_indicators": ["minor_present", "protection_required"],
                "age_group": "child",
                "confidence": 0.85
            }

        # Default: persona en contexto normal
        return {
            "visual_summary": "Persona adulta en ropa casual en espacio público",
            "tags": ["adult", "casual", "outdoor", "public_space"],
            "environment": "general_public_space",
            "clothing_level": "casual",
            "visible_biometrics": {"face_visible": True, "tattoos_visible": False, "scars_visible": False, "distinctive_marks": "none"},
            "context_indicators": ["everyday_activity", "public_space"],
            "age_group": "adult",
            "confidence": 0.75
        }

    def _fallback_visual_description(self) -> Dict[str, Any]:
        """Descripción por defecto cuando falla el análisis."""
        return {
            "visual_summary": "Persona detectada - descripción no disponible",
            "tags": ["person", "unknown_context"],
            "environment": "unknown",
            "clothing_level": "unknown",
            "visible_biometrics": {"face_visible": False, "tattoos_visible": False, "scars_visible": False, "distinctive_marks": "unknown"},
            "context_indicators": ["analysis_failed"],
            "age_group": "unknown",
            "confidence": 0.3
        }

    def _determine_violation(self, detection_type: str, context: List[Dict]) -> Dict[str, Any]:
        """
        Determina si hay violación basándose en el tipo de detección (reglas GDPR).
        NOTA: Este método YA NO se usa para "person" - solo para face, license_plate, etc.
        """
        always_violation = {"face", "fingerprint", "id_document", "credit_card", "hand_biometric"}
        likely_violation = {"license_plate", "signature"}

        is_violation = False
        severity = "none"
        confidence = 0.0
        reasoning = ""
        recommended_action = "none"

        if detection_type in always_violation:
            is_violation = True
            severity = "high"
            confidence = 0.95
            recommended_action = "blur" if detection_type in ("id_document", "face", "hand_biometric") else "pixelate"
            reasoning = f"Detección de {detection_type}: Dato biométrico/sensible según Art. 9 GDPR."

        elif detection_type in likely_violation:
            is_violation = True
            severity = "high"
            confidence = 0.90
            recommended_action = "pixelate" if detection_type == "license_plate" else "blur"
            reasoning = f"Detección de {detection_type}: Identificador personal."
        else:
            is_violation = False
            confidence = 0.5
            reasoning = f"Tipo '{detection_type}' no clasificado como dato sensible GDPR."

        return {
            "is_violation": is_violation,
            "severity": severity,
            "violated_articles": GDPR_ARTICLES.get(detection_type, ["6"]),
            "reasoning": reasoning,
            "confidence": confidence,
            "detection_type": detection_type,
            "recommended_action": recommended_action
        }
