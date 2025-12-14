"""
Consultas Neo4j para el Verification Module.

Estas consultas son usadas por los Sub-Agents para obtener
contexto GDPR relevante para cada detección.
"""

class GDPRQueries:
    """Consultas predefinidas para el Knowledge Graph GDPR."""
    
    # Obtener artículos relevantes para un tipo de detección
    GET_ARTICLES_FOR_DETECTION = """
    MATCH (d:DetectionType {type: $detection_type})-[:VIOLATES]->(a:Article)
    OPTIONAL MATCH (a)-[:EXPLAINED_BY]->(r:Recital)
    OPTIONAL MATCH (a)-[:DEFINES]->(c:Concept)
    RETURN 
        a.number AS article_number,
        a.title AS title,
        a.full_text AS content,
        a.fine_tier AS fine_tier,
        d.severity AS severity,
        d.reasoning_template AS reasoning_template,
        d.requires_explicit_consent AS requires_consent,
        d.recommended_actions AS recommended_actions,
        collect(DISTINCT r.number) AS related_recitals,
        collect(DISTINCT c.name) AS related_concepts
    ORDER BY a.number
    """
    
    # Búsqueda semántica por similitud de embeddings
    # Requiere que los embeddings ya estén generados
    SEMANTIC_SEARCH = """
    MATCH (a:Article)
    WHERE a.embedding IS NOT NULL
    WITH a, gds.similarity.cosine(a.embedding, $query_embedding) AS similarity
    WHERE similarity > $threshold
    RETURN 
        a.number AS article_number,
        a.title AS title,
        a.content AS content,
        a.fine_tier AS fine_tier,
        similarity
    ORDER BY similarity DESC
    LIMIT $limit
    """
    
    # Búsqueda fulltext como fallback
    FULLTEXT_SEARCH = """
    CALL db.index.fulltext.queryNodes('gdpr_articles_fulltext', $query)
    YIELD node, score
    WHERE score > 0.3
    MATCH (node)-[:EXPLAINED_BY]->(r:Recital)
    RETURN 
        node.number AS article_number,
        node.title AS title,
        node.content AS content,
        node.fine_tier AS fine_tier,
        collect(DISTINCT r.number) AS recitals,
        score
    ORDER BY score DESC
    LIMIT $limit
    """
    
    # Obtener información de multa
    GET_FINE_INFO = """
    MATCH (f:Fine)-[:APPLIES_TO]->(a:Article {number: $article_number})
    RETURN 
        f.tier AS tier,
        f.max_amount AS max_amount,
        f.description AS description
    """
    
    # Obtener contexto completo para un artículo (para explicabilidad)
    GET_FULL_ARTICLE_CONTEXT = """
    MATCH (a:Article {number: $article_number})
    OPTIONAL MATCH (ch:Chapter)-[:CONTAINS]->(a)
    OPTIONAL MATCH (a)-[:EXPLAINED_BY]->(r:Recital)
    OPTIONAL MATCH (a)-[:DEFINES]->(c:Concept)
    OPTIONAL MATCH (a)-[:GRANTS]->(right:Right)
    OPTIONAL MATCH (a)-[:REFERENCES]->(ref:Article)
    OPTIONAL MATCH (f:Fine)-[:APPLIES_TO]->(a)
    RETURN 
        a.number AS article_number,
        a.title AS title,
        a.full_text AS full_text,
        ch.title AS chapter,
        collect(DISTINCT {number: r.number, content: r.content}) AS recitals,
        collect(DISTINCT {name: c.name, definition: c.definition}) AS concepts,
        collect(DISTINCT {name: right.name, description: right.description}) AS rights,
        collect(DISTINCT ref.number) AS references,
        f.max_amount AS fine_max
    """
    
    # Obtener artículos para categorías especiales de datos
    GET_SPECIAL_CATEGORY_ARTICLES = """
    MATCH (d:DataType {is_special_category: true})-[:PROTECTED_BY]->(a:Article)
    OPTIONAL MATCH (d)-[:REQUIRES]->(c:Concept)
    RETURN 
        d.name AS data_type,
        d.definition AS definition,
        a.number AS article_number,
        a.title AS article_title,
        c.name AS required_concept
    """
    
    # Obtener grafo de relaciones para explicabilidad
    GET_EXPLANATION_GRAPH = """
    MATCH path = (d:DetectionType {type: $detection_type})
        -[:VIOLATES]->(a:Article)
        -[:EXPLAINED_BY]->(r:Recital)
    WITH d, a, collect(r) AS recitals
    OPTIONAL MATCH (a)-[:DEFINES]->(c:Concept)
    OPTIONAL MATCH (f:Fine)-[:APPLIES_TO]->(a)
    RETURN 
        d.type AS detection,
        d.severity AS severity,
        a.number AS article,
        a.title AS article_title,
        [r IN recitals | r.number] AS recitals,
        collect(c.name) AS concepts,
        f.tier AS fine_tier,
        f.max_amount AS fine_max
    """
