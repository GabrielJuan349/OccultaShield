from typing import List, Dict, Any, TypedDict, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from .graph_db import GraphDB
import json
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForCausalLM
import os
from dotenv import load_dotenv

load_dotenv()

# Define the state of our graph
class VerificationState(TypedDict):
    image_path: str
    detected_objects: List[str]
    retrieved_context: List[str]
    verification_result: Dict[str, Any]


class GDPRVerificationGraph:
    """
    GraphRAG system for GDPR compliance verification using Neo4j and a multimodal LLM.
    Uses LangGraph for workflow orchestration and Hugging Face Transformers for inference.
    """
    
    _instance: Optional["GDPRVerificationGraph"] = None
    _model_loaded: bool = False

    def __new__(cls):
        """Singleton pattern to avoid reloading the model multiple times."""
        if cls._instance is None:
            cls._instance = super(GDPRVerificationGraph, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Skip re-initialization if already done
        if GDPRVerificationGraph._model_loaded:
            return
            
        print("Initializing GDPR Verification Graph...")
        self.graph_db = GraphDB().connect()
        
        # --- Hugging Face Transformers Configuration ---
        # Model ID - change this to the exact model you want to use
        # Options: "google/gemma-3-4b-it", "meta-llama/Llama-3.2-11B-Vision-Instruct", etc.
        self.model_id = os.getenv("MULTIMODAL_MODEL_ID", "google/gemma-3n-E4B-it")
        
        # Detect device (GPU strongly recommended for vision models)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        
        if self.device == "cpu":
            print("⚠️ WARNING: Running on CPU will be very slow for vision models. Consider using a GPU.")
        
        try:
            print(f"Loading model: {self.model_id}...")
            
            # Load processor (handles both text and images)
            self.processor = AutoProcessor.from_pretrained(
                self.model_id, 
                trust_remote_code=True
            )
            
            # Load model with optimizations
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                device_map="auto" if self.device == "cuda" else None,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            if self.device == "cpu":
                self.model = self.model.to(self.device)
                
            print("✅ Model loaded successfully.")
            GDPRVerificationGraph._model_loaded = True
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            print("The system will continue but verification will fail.")
            self.model = None
            self.processor = None

        self.workflow = self._build_workflow()

    def _retrieve_gdpr_context(self, state: VerificationState) -> Dict[str, List[str]]:
        """
        HYBRID RETRIEVAL: Combines vector similarity search with Cypher keyword search.
        
        This approach ensures:
        1. Semantic matches (via embeddings) for conceptually related articles
        2. Exact keyword matches for specific terms
        3. Deduplication and ranking of results
        """
        print("--- STEP 1: HYBRID GDPR CONTEXT RETRIEVAL ---")
        objects = state["detected_objects"]
        
        # Use the hybrid_search method from GraphDB
        context = self.graph_db.hybrid_search(
            query=f"GDPR violations related to {', '.join(objects)}",
            detected_objects=objects,
            k=6  # Get up to 6 relevant articles
        )
        
        print(f"  ✅ Retrieved {len(context)} relevant GDPR articles via hybrid search.")
        return {"retrieved_context": context}

    def _verify_vulnerability(self, state: VerificationState) -> Dict[str, Dict[str, Any]]:
        """
        Use Hugging Face Transformers multimodal LLM to verify GDPR violations.
        Analyzes the image with the retrieved legal context.
        """
        print("--- STEP 2: VERIFYING VULNERABILITY WITH LLM ---")
        
        if not self.model or not self.processor:
            error_msg = "Model not loaded. Cannot perform verification."
            print(f"  ❌ {error_msg}")
            return {"verification_result": {"error": error_msg, "is_violation": None}}

        image_path = state["image_path"]
        context = "\n\n".join(state["retrieved_context"])
        objects = ", ".join(state["detected_objects"])

        try:
            # 1. Load and prepare image
            print(f"  Loading image: {image_path}")
            image = Image.open(image_path).convert("RGB")
            
            # 2. Build the prompt
            prompt_text = f"""You are an expert GDPR Compliance Analyst AI.

## TASK
Analyze the provided image for potential GDPR (General Data Protection Regulation) violations.

## DETECTED ELEMENTS
The following elements were detected in the image: [{objects}]

## RELEVANT GDPR ARTICLES
{context}

## INSTRUCTIONS
1. Examine the image carefully
2. Determine if any detected elements constitute personal data that should be protected
3. Check if exposing this data would violate any of the referenced GDPR articles
4. Consider: Are faces visible? License plates readable? Any identifiable information shown?

## REQUIRED OUTPUT FORMAT
Return ONLY a valid JSON object with this exact structure:
{{
    "is_violation": true or false,
    "violated_articles": ["Article X", "Article Y"],
    "detected_personal_data": ["type1", "type2"],
    "description": "Detailed explanation of the violation or why there is no violation",
    "severity": "Critical" or "High" or "Medium" or "Low" or "None",
    "recommended_action": "What should be done to comply with GDPR",
    "confidence": 0.0 to 1.0
}}"""

            # 3. Prepare inputs for the model
            # Format depends on the specific model's chat template
            messages = [
                {"role": "user", "content": [
                    {"type": "image"},
                    {"type": "text", "text": prompt_text}
                ]}
            ]
            
            # Apply chat template
            text = self.processor.apply_chat_template(
                messages, 
                add_generation_prompt=True,
                tokenize=False
            )
            
            # Process inputs (image + text)
            inputs = self.processor(
                text=[text],
                images=[image],
                return_tensors="pt",
                padding=True
            ).to(self.device)

            # 4. Generate response
            print("  🔄 Generating LLM response...")
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=1024,
                    do_sample=False,  # Deterministic for consistent JSON
                    temperature=None,
                    top_p=None,
                    pad_token_id=self.processor.tokenizer.eos_token_id
                )
            
            # Decode response (remove prompt tokens)
            generated_ids_trimmed = [
                out_ids[len(in_ids):] 
                for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = self.processor.batch_decode(
                generated_ids_trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            )[0]

            print("  ✅ LLM response received.")

            # 5. Parse JSON from response
            result_json = self._extract_json(output_text)
            
            # Add metadata
            result_json["_metadata"] = {
                "model_used": self.model_id,
                "image_analyzed": image_path,
                "objects_detected": objects.split(", ")
            }
            
            return {"verification_result": result_json}

        except FileNotFoundError:
            error_msg = f"Image file not found: {image_path}"
            print(f"  ❌ {error_msg}")
            return {"verification_result": {"error": error_msg, "is_violation": None}}
        except Exception as e:
            error_msg = f"Verification failed: {str(e)}"
            print(f"  ❌ {error_msg}")
            return {"verification_result": {"error": error_msg, "is_violation": None}}

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Extract and parse JSON from LLM output.
        Handles cases where the model adds extra text around the JSON.
        """
        # Try direct parsing first
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        
        # Find JSON object boundaries
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            try:
                json_str = text[start:end + 1]
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Fallback: return raw text with error flag
        return {
            "error": "Could not parse JSON from LLM response",
            "raw_response": text[:500],  # Truncate for safety
            "is_violation": None
        }

    def _build_workflow(self) -> Any:
        """Build the LangGraph workflow for GDPR verification."""
        workflow = StateGraph(VerificationState)

        # Add nodes
        workflow.add_node("retrieve_context", self._retrieve_gdpr_context)
        workflow.add_node("verify_vulnerability", self._verify_vulnerability)

        # Define flow
        workflow.set_entry_point("retrieve_context")
        workflow.add_edge("retrieve_context", "verify_vulnerability")
        workflow.add_edge("verify_vulnerability", END)

        return workflow.compile()

    def run(self, image_path: str, detected_objects: List[str]) -> Dict[str, Any]:
        """
        Execute the GDPR verification workflow.
        
        Args:
            image_path: Path to the image file to analyze
            detected_objects: List of objects detected in the image (e.g., ["face", "license_plate"])
        
        Returns:
            Dictionary containing verification results
        """
        print(f"\n{'='*60}")
        print("GDPR VERIFICATION WORKFLOW STARTED")
        print(f"{'='*60}")
        print(f"Image: {image_path}")
        print(f"Detected objects: {detected_objects}")
        print(f"{'='*60}\n")
        
        initial_state: VerificationState = {
            "image_path": image_path,
            "detected_objects": detected_objects,
            "retrieved_context": [],
            "verification_result": {}
        }
        
        result = self.workflow.invoke(initial_state)
        
        print(f"\n{'='*60}")
        print("VERIFICATION COMPLETE")
        print(f"{'='*60}\n")
        
        return result["verification_result"]


# Convenience function for external use
def verify_gdpr_compliance(image_path: str, detected_objects: List[str]) -> Dict[str, Any]:
    """
    Verify GDPR compliance for an image.
    
    Args:
        image_path: Path to the image to analyze
        detected_objects: List of detected object types
        
    Returns:
        Verification result dictionary
    """
    verifier = GDPRVerificationGraph()
    return verifier.run(image_path, detected_objects)
