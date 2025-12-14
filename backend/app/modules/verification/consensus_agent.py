from typing import List, Dict, Any

class ConsensusAgent:
    """
    Agent responsible for aggregating and validating verification results.
    """
    def aggregate(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate results from one or multiple sub-agents.
        For Phase 1, we primarily validate the single agent's output.
        """
        if not results:
            return {
                "is_violation": False,
                "confidence": 0.0,
                "reasoning": "No results to aggregate"
            }
            
        # Strategy: Majority vote or highest confidence
        # For a single result, just return it sanitized
        if len(results) == 1:
            return self._validate(results[0])
            
        # Example aggregation logic (placeholder for multi-agent expansion)
        violations = [r for r in results if r.get("is_violation", False)]
        if len(violations) > len(results) / 2:
            # Majority detected violation
            best_violation = max(violations, key=lambda x: x.get("confidence", 0))
            return self._validate(best_violation)
            
        # Majority says NO violation
        clean_results = [r for r in results if not r.get("is_violation", False)]
        best_clean = max(clean_results, key=lambda x: x.get("confidence", 0)) if clean_results else results[0]
        return self._validate(best_clean)

    def _validate(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure result has all required fields."""
        defaults = {
            "is_violation": False,
            "severity": "none",
            "confidence": 0.0,
            "description": "",
            "recommended_action": "none",
            "violated_articles": []
        }
        
        for key, default_val in defaults.items():
            if key not in result:
                result[key] = default_val
                
        return result
