from typing import List, Dict, Any, Optional
import logging
from .graph_db import GraphDB

logger = logging.getLogger(__name__)

# =============================================================================
# CONTEXTOS VULNERABLES: Requieren protección adicional según GDPR Art. 9
# =============================================================================
VULNERABLE_CONTEXTS = {
    # Contexto médico/salud (Art. 9.1 - datos de salud)
    "medical": ["hospital", "medical_setting", "clinic", "healthcare", "patient",
                "hospital_gown", "medical", "doctor", "surgery", "emergency_room"],

    # Menores de edad (protección especial - Recital 38 GDPR)
    "minor": ["child", "minor", "kid", "teenager", "school", "playground",
              "underage", "infant", "baby", "toddler"],

    # Contexto religioso/filosófico (Art. 9.1 - creencias)
    "religious": ["religious_symbol", "church", "mosque", "synagogue", "temple",
                  "religious", "prayer", "worship", "religious_clothing"],

    # Contexto político (Art. 9.1 - opiniones políticas)
    "political": ["protest", "demonstration", "political", "rally", "activist",
                  "protest_sign", "manifestation", "political_gathering"],

    # Desnudez/intimidad (dignidad personal)
    "intimate": ["swimwear", "minimal", "underwear", "nude", "nudity",
                 "changing_room", "bathroom", "intimate", "private_moment"],

    # Étnicos/raciales (Art. 9.1 - origen étnico)
    "ethnic": ["ethnic_clothing", "traditional_dress", "cultural_marker",
               "racial_identifier"],
}

# =============================================================================
# CONTEXTOS NORMALES: Solo requieren censura facial estándar
# =============================================================================
NORMAL_CONTEXTS = {
    "public_space": ["street", "sidewalk", "park", "plaza", "public_space",
                     "general_public_space", "outdoor", "urban"],
    "workplace": ["office", "workplace", "meeting", "conference", "business"],
    "commercial": ["shop", "store", "mall", "restaurant", "cafe", "hotel"],
    "recreational": ["beach", "pool", "gym", "sports", "recreational",
                     "leisure", "entertainment", "concert"],
    "transport": ["airport", "station", "bus", "train", "car", "traffic"],
}


class ConsensusAgent:
    """
    Temporal Consensus Agent for GDPR verification.

    ARQUITECTURA "TESTIGO VS JUEZ":
    - El GemmaClient actúa como TESTIGO: describe objetivamente lo que ve
    - El ConsensusAgent actúa como JUEZ: toma decisiones legales basadas en:
      1. Las descripciones del Testigo
      2. El contexto legal de Neo4j (Knowledge Graph GDPR)
      3. Las reglas de contexto vulnerable vs. normal

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

    # =========================================================================
    # NUEVO MÉTODO: EL "JUEZ" - Decisión legal basada en contexto
    # =========================================================================

    async def aggregate_and_decide(
        self,
        track_id: str,
        frame_results: List[Dict[str, Any]],
        detection_type: str = "person"
    ) -> Dict[str, Any]:
        """
        MODO JUEZ: Recibe descripciones visuales del Testigo y emite veredicto legal.

        Este método implementa la "Regla de Oro":
        - Persona en contexto NORMAL (calle, oficina, playa) → is_violation: False
          (Solo se censura la cara, que tiene su propio track)
        - Persona en contexto VULNERABLE (hospital, protesta, menor) → is_violation: True
          (Se debe censurar el cuerpo entero + difuminado)

        Args:
            track_id: ID del track de seguimiento
            frame_results: Lista de descripciones visuales del Testigo (GemmaClient)
            detection_type: Tipo de detección (default: "person")

        Returns:
            Dict con veredicto legal: is_violation, severity, reasoning, articles, etc.
        """
        if not frame_results:
            return self._no_data_verdict(track_id)

        # Para tipos que no son "person", usar método clásico
        if detection_type != "person":
            return self.aggregate(frame_results)

        # =====================================================================
        # PASO 1: Consolidar descripciones visuales de todos los frames
        # =====================================================================
        logger.info(f"⚖️  [JUEZ] Analizando track {track_id} con {len(frame_results)} frames")

        consolidated = self._consolidate_visual_descriptions(frame_results)
        all_tags = consolidated["all_tags"]
        all_environments = consolidated["all_environments"]
        all_context_indicators = consolidated["all_context_indicators"]
        full_summary = consolidated["full_summary"]
        age_groups = consolidated["age_groups"]

        logger.info(f"⚖️  [JUEZ] Tags consolidados: {all_tags}")
        logger.info(f"⚖️  [JUEZ] Entornos detectados: {all_environments}")

        # =====================================================================
        # PASO 2: Consultar Neo4j para contexto legal GDPR
        # =====================================================================
        legal_context = await self._query_legal_context(list(all_tags))
        logger.info(f"⚖️  [JUEZ] Contexto legal Neo4j: {len(legal_context)} artículos relevantes")

        # =====================================================================
        # PASO 3: Aplicar "Regla de Oro" - Contexto vulnerable vs. normal
        # =====================================================================
        vulnerability_analysis = self._analyze_vulnerability(
            tags=all_tags,
            environments=all_environments,
            context_indicators=all_context_indicators,
            age_groups=age_groups
        )

        is_vulnerable = vulnerability_analysis["is_vulnerable"]
        vulnerability_type = vulnerability_analysis["vulnerability_type"]
        vulnerability_reason = vulnerability_analysis["reason"]

        logger.info(f"⚖️  [JUEZ] ¿Contexto vulnerable?: {is_vulnerable} ({vulnerability_type})")

        # =====================================================================
        # PASO 4: Emitir veredicto legal
        # =====================================================================

        if is_vulnerable:
            # CONTEXTO VULNERABLE → Violación GDPR
            violated_articles = self._get_articles_for_vulnerability(vulnerability_type, legal_context)

            verdict = {
                "is_violation": True,
                "severity": "high" if vulnerability_type in ("medical", "minor", "intimate") else "medium",
                "confidence": vulnerability_analysis["confidence"],
                "violated_articles": violated_articles,
                "vulnerability_type": vulnerability_type,
                "reasoning": (
                    f"⚠️ VIOLACIÓN GDPR DETECTADA: {vulnerability_reason}. "
                    f"Contexto: {full_summary[:200]}... "
                    f"Artículos aplicables: {', '.join(violated_articles)}. "
                    f"Se recomienda censura completa del cuerpo."
                ),
                "recommended_action": "blur",
                "detection_type": "person",
                "track_id": track_id,
                "frames_analyzed": len(frame_results),
                "legal_context_summary": self._summarize_legal_context(legal_context),
                "mode": "judge_decision"
            }

            logger.info(f"⚖️  [JUEZ] VEREDICTO: VIOLACIÓN - {vulnerability_reason}")

        else:
            # CONTEXTO NORMAL → No violación (solo censura facial separada)
            verdict = {
                "is_violation": False,
                "severity": "none",
                "confidence": vulnerability_analysis["confidence"],
                "violated_articles": [],
                "vulnerability_type": None,
                "reasoning": (
                    f"✅ Sin violación de contexto: Persona en entorno normal ({', '.join(all_environments)}). "
                    f"La cara se censurará en su propio track (face detection). "
                    f"No se requiere censura adicional del cuerpo."
                ),
                "recommended_action": "none",  # La cara tiene su propio track
                "detection_type": "person",
                "track_id": track_id,
                "frames_analyzed": len(frame_results),
                "legal_context_summary": "",
                "mode": "judge_decision"
            }

            logger.info(f"⚖️  [JUEZ] VEREDICTO: SIN VIOLACIÓN - contexto normal")

        return verdict

    def _consolidate_visual_descriptions(self, frame_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Consolida las descripciones visuales de múltiples frames."""
        all_tags = set()
        all_environments = set()
        all_context_indicators = set()
        summaries = []
        age_groups = set()

        for result in frame_results:
            # Tags
            tags = result.get("tags", [])
            if isinstance(tags, list):
                all_tags.update(tags)

            # Environment
            env = result.get("environment", "")
            if env:
                all_environments.add(env)

            # Context indicators
            indicators = result.get("context_indicators", [])
            if isinstance(indicators, list):
                all_context_indicators.update(indicators)

            # Summary
            summary = result.get("visual_summary", "")
            if summary:
                summaries.append(summary)

            # Age group
            age = result.get("age_group", "")
            if age:
                age_groups.add(age)

        return {
            "all_tags": all_tags,
            "all_environments": all_environments,
            "all_context_indicators": all_context_indicators,
            "full_summary": " | ".join(summaries),
            "age_groups": age_groups
        }

    def _analyze_vulnerability(
        self,
        tags: set,
        environments: set,
        context_indicators: set,
        age_groups: set
    ) -> Dict[str, Any]:
        """
        Analiza si el contexto es vulnerable según las categorías GDPR.

        REGLA DE ORO:
        - Contexto vulnerable → is_vulnerable: True
        - Contexto normal → is_vulnerable: False
        """
        all_indicators = tags | environments | context_indicators
        all_indicators_lower = {str(i).lower() for i in all_indicators}

        # Verificar cada tipo de vulnerabilidad
        for vuln_type, keywords in VULNERABLE_CONTEXTS.items():
            matching = all_indicators_lower & set(keywords)
            if matching:
                # Caso especial: menores
                if vuln_type == "minor" or "child" in age_groups or "teenager" in age_groups:
                    return {
                        "is_vulnerable": True,
                        "vulnerability_type": "minor",
                        "reason": f"Menor de edad detectado. Protección especial requerida (Recital 38 GDPR).",
                        "confidence": 0.95,
                        "matching_keywords": list(matching)
                    }

                return {
                    "is_vulnerable": True,
                    "vulnerability_type": vuln_type,
                    "reason": self._get_vulnerability_reason(vuln_type, matching),
                    "confidence": 0.85 if len(matching) >= 2 else 0.75,
                    "matching_keywords": list(matching)
                }

        # Verificar explícitamente si es contexto normal
        for normal_type, keywords in NORMAL_CONTEXTS.items():
            matching = all_indicators_lower & set(keywords)
            if matching:
                return {
                    "is_vulnerable": False,
                    "vulnerability_type": None,
                    "reason": f"Contexto normal: {normal_type} ({', '.join(matching)})",
                    "confidence": 0.80,
                    "matching_keywords": list(matching)
                }

        # Por defecto: contexto desconocido → tratarlo como normal (principio de proporcionalidad)
        return {
            "is_vulnerable": False,
            "vulnerability_type": None,
            "reason": "Contexto no clasificado - se asume normal por proporcionalidad",
            "confidence": 0.60,
            "matching_keywords": []
        }

    def _get_vulnerability_reason(self, vuln_type: str, matching: set) -> str:
        """Genera una explicación legible para cada tipo de vulnerabilidad."""
        reasons = {
            "medical": f"Contexto médico/sanitario detectado ({', '.join(matching)}). Art. 9.1 GDPR - Datos de salud.",
            "minor": f"Menor de edad detectado ({', '.join(matching)}). Protección especial según Recital 38 GDPR.",
            "religious": f"Contexto religioso/filosófico detectado ({', '.join(matching)}). Art. 9.1 GDPR.",
            "political": f"Contexto político detectado ({', '.join(matching)}). Art. 9.1 GDPR - Opiniones políticas.",
            "intimate": f"Contexto de intimidad detectado ({', '.join(matching)}). Dignidad personal y Art. 9.1 GDPR.",
            "ethnic": f"Posibles indicadores étnicos/raciales detectados ({', '.join(matching)}). Art. 9.1 GDPR.",
        }
        return reasons.get(vuln_type, f"Vulnerabilidad detectada: {vuln_type}")

    def _get_articles_for_vulnerability(
        self,
        vulnerability_type: str,
        legal_context: List[Dict]
    ) -> List[str]:
        """Obtiene los artículos GDPR aplicables según el tipo de vulnerabilidad."""
        base_articles = {
            "medical": ["9", "6"],      # Datos de salud
            "minor": ["8", "6"],        # Consentimiento de menores
            "religious": ["9", "6"],    # Creencias religiosas
            "political": ["9", "6"],    # Opiniones políticas
            "intimate": ["9", "6", "5"], # Dignidad, minimización
            "ethnic": ["9", "6"],       # Origen étnico
        }

        articles = set(base_articles.get(vulnerability_type, ["6"]))

        # Añadir artículos del contexto legal de Neo4j si los hay
        for ctx in legal_context:
            article_num = ctx.get("article_number", "")
            if article_num:
                articles.add(str(article_num))

        return sorted(list(articles))

    async def _query_legal_context(self, tags: List[str]) -> List[Dict[str, Any]]:
        """Consulta Neo4j para obtener contexto legal GDPR basado en los tags."""
        try:
            graph_db = self._get_graph_db()

            # Usar hybrid_search que combina vector + keyword search
            context_strings = graph_db.hybrid_search(
                query=f"GDPR regulations for {', '.join(tags)}",
                detected_objects=tags,
                k=5
            )

            # Convertir strings a dicts estructurados
            legal_context = []
            for ctx in context_strings:
                # Extraer número de artículo si está presente
                article_num = ""
                if "Article" in ctx:
                    import re
                    match = re.search(r'Article\s*(\d+)', ctx)
                    if match:
                        article_num = match.group(1)

                legal_context.append({
                    "content": ctx,
                    "article_number": article_num
                })

            return legal_context

        except Exception as e:
            logger.warning(f"⚠️ Error consultando Neo4j: {e}. Usando fallback.")
            return []

    def _summarize_legal_context(self, legal_context: List[Dict]) -> str:
        """Genera un resumen del contexto legal para el veredicto."""
        if not legal_context:
            return "No se encontró contexto legal específico en Neo4j."

        summaries = []
        for ctx in legal_context[:3]:  # Max 3 artículos
            content = ctx.get("content", "")[:200]
            summaries.append(content)

        return " | ".join(summaries)

    def _no_data_verdict(self, track_id: str) -> Dict[str, Any]:
        """Veredicto cuando no hay datos para analizar."""
        return {
            "is_violation": False,
            "severity": "none",
            "confidence": 0.0,
            "reasoning": f"Sin datos para analizar en track {track_id}",
            "recommended_action": "none",
            "frames_analyzed": 0,
            "mode": "judge_decision"
        }
    
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
