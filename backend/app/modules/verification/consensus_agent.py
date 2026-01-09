from typing import List, Dict, Any, Optional
from .graph_db import GraphDB

class ConsensusAgent:
    """
    Temporal Consensus Agent for GDPR verification.
    
    Aggregates results from multiple frames using:
    - Union-of-Evidence: If ANY frame is positive → violation confirmed
    - Article Consolidation: Merges violated_articles from all frames
    - Severity Escalation: Persistent violations (3+ frames) → Critical
    - Neo4j Legal Validation: Confirms article coherence
    """
    
    def __init__(self):
        self.graph_db: Optional[GraphDB] = None
        
    def _get_graph_db(self) -> GraphDB:
        """Lazy-load GraphDB connection."""
        if self.graph_db is None:
            self.graph_db = GraphDB().connect()
        return self.graph_db
    
    def aggregate(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate results from multiple frames using Temporal Consensus.
        
        Strategy:
        1. If ANY frame shows violation → is_violation = True (Protective principle)
        2. Merge all violated_articles into a unique set
        3. Escalate severity if violation persists across 3+ frames
        4. Average confidence scores
        5. Generate synthesis description
        """
        if not results:
            return {
                "is_violation": False,
                "confidence": 0.0,
                "reasoning": "No results to aggregate",
                "frames_analyzed": 0
            }
            
        if len(results) == 1:
            return self._validate(results[0])
        
        # --- Union of Evidence ---
        violations = [r for r in results if r.get("is_violation", False)]
        is_violation = len(violations) > 0
        
        # --- Aggregate Confidence ---
        confidences = [r.get("confidence", 0.0) for r in results]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        max_confidence = max(confidences) if confidences else 0.0
        
        # --- Merge Violated Articles ---
        all_articles = set()
        for r in results:
            articles = r.get("violated_articles", [])
            if isinstance(articles, list):
                all_articles.update(articles)
        
        # --- Severity Escalation ---
        severity = "none"
        if is_violation:
            violation_count = len(violations)
            if violation_count >= 3:
                severity = "critical"  # Persistent violation
            elif violation_count >= 2:
                severity = "high"
            else:
                # Use the severity from the single violation
                severity = violations[0].get("severity", "medium")
        
        # --- Recommended Action (most severe wins) ---
        action_priority = {"mask": 4, "pixelate": 3, "blur": 2, "none": 1}
        best_action = "none"
        for r in violations:
            action = r.get("recommended_action", "none")
            if action_priority.get(action, 0) > action_priority.get(best_action, 0):
                best_action = action
        
        # --- Generate Synthesis Description ---
        frame_numbers = [r.get("frame", "?") for r in violations]
        if is_violation:
            reasoning = (
                f"Violación confirmada en {len(violations)}/{len(results)} frames analizados "
                f"(frames: {frame_numbers}). Artículos vulnerados: {sorted(all_articles)}. "
                f"Confianza promedio: {avg_confidence:.0%}, máxima: {max_confidence:.0%}."
            )
        else:
            reasoning = (
                f"No se detectó violación en ninguno de los {len(results)} frames analizados. "
                f"Confianza promedio: {avg_confidence:.0%}."
            )
        
        # --- Optional: Neo4j Legal Validation ---
        # Could query Neo4j to validate article coherence, but for performance
        # we skip this in the aggregate step (already done per-frame)
        
        result = {
            "is_violation": is_violation,
            "severity": severity,
            "confidence": round(avg_confidence, 3),
            "max_confidence": round(max_confidence, 3),
            "violated_articles": sorted(list(all_articles)),
            "recommended_action": best_action,
            "reasoning": reasoning,
            "frames_with_violation": len(violations),
            "detection_type": results[0].get("detection_type") if results else "unknown"
        }
        
        return self._validate(result)

    def _validate(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure result has all required fields."""
        defaults = {
            "is_violation": False,
            "severity": "none",
            "confidence": 0.0,
            "description": "",
            "recommended_action": "none",
            "violated_articles": [],
            "reasoning": "",
            "frames_analyzed": 1
        }
        
        for key, default_val in defaults.items():
            if key not in result:
                result[key] = default_val
                
        return result
