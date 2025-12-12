import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_neo4j import Neo4jVector, Neo4jGraph
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()


def ingest_gdpr_pdf(pdf_path: str, clear_existing: bool = False):
    """
    Reads the GDPR PDF and ingests it into Neo4j with vector embeddings.
    
    This creates:
    1. GDPRArticle nodes with content
    2. Vector embeddings for semantic search
    3. A vector index for similarity queries
    
    Args:
        pdf_path: Path to the GDPR PDF file
        clear_existing: If True, deletes existing GDPRArticle nodes first
    """
    print(f"\n{'='*60}")
    print("GDPR DOCUMENT INGESTION")
    print(f"{'='*60}")
    print(f"PDF: {pdf_path}")
    
    # Connection details
    url = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "Occultashield_neo4j")
    
    # 1. Load PDF
    print("\n📄 Step 1: Loading PDF...")
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    print(f"   Loaded {len(documents)} pages")
    
    # 2. Split text into chunks
    print("\n✂️ Step 2: Splitting into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\nArticle ", "\nArtículo ", "\n\n", "\n", ". ", " "]
    )
    chunks = text_splitter.split_documents(documents)
    print(f"   Created {len(chunks)} chunks")
    
    # 3. Process chunks to extract article information
    print("\n🏷️ Step 3: Processing chunks...")
    processed_docs: List[Document] = []
    
    for i, chunk in enumerate(chunks):
        content = chunk.page_content
        
        # Try to extract article number from content
        title = f"GDPR Section {i+1}"
        if "Article" in content[:50]:
            # Extract article title from first line
            first_line = content.split("\n")[0].strip()
            if first_line:
                title = first_line[:100]  # Limit length
        elif "Artículo" in content[:50]:
            first_line = content.split("\n")[0].strip()
            if first_line:
                title = first_line[:100]
        
        # Determine fine tier based on content keywords
        fine_tier = "Standard"
        high_fine_keywords = ["biometric", "special categories", "children", "health", "genetic"]
        critical_keywords = ["supervisory authority", "administrative fine", "penalty"]
        
        content_lower = content.lower()
        if any(kw in content_lower for kw in critical_keywords):
            fine_tier = "Critical"
        elif any(kw in content_lower for kw in high_fine_keywords):
            fine_tier = "High"
        
        processed_docs.append(Document(
            page_content=content,
            metadata={
                "title": title,
                "source": pdf_path,
                "page": chunk.metadata.get("page", 0),
                "chunk_id": i,
                "fine_tier": fine_tier
            }
        ))
    
    # 4. Initialize embeddings
    print("\n🧠 Step 4: Loading embedding model...")
    embedding_model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    embeddings = HuggingFaceEmbeddings(
        model_name=embedding_model,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    print(f"   Using: {embedding_model}")
    
    # 5. Clear existing data if requested
    if clear_existing:
        print("\n🗑️ Step 5: Clearing existing GDPR nodes...")
        graph = Neo4jGraph(url=url, username=username, password=password)
        graph.query("MATCH (n:GDPRArticle) DETACH DELETE n")
        print("   Cleared existing nodes")
    
    # 6. Create vector store with embeddings
    print("\n📊 Step 6: Creating vector store and embeddings...")
    print("   This may take a few minutes...")
    
    vector_store = Neo4jVector.from_documents(
        documents=processed_docs,
        embedding=embeddings,
        url=url,
        username=username,
        password=password,
        index_name="gdpr_vector_index",
        node_label="GDPRArticle",
        text_node_property="content",
        embedding_node_property="embedding",
        pre_delete_collection=clear_existing
    )
    
    print(f"   ✅ Created {len(processed_docs)} nodes with embeddings")
    
    # 7. Create additional indexes for keyword search
    print("\n🔍 Step 7: Creating text indexes...")
    graph = Neo4jGraph(url=url, username=username, password=password)
    
    try:
        # Create full-text index for keyword search
        graph.query("""
        CREATE FULLTEXT INDEX gdpr_fulltext_index IF NOT EXISTS
        FOR (n:GDPRArticle)
        ON EACH [n.content, n.title]
        """)
        print("   ✅ Created fulltext index")
    except Exception as e:
        print(f"   ⚠️ Fulltext index may already exist: {e}")
    
    print(f"\n{'='*60}")
    print("✅ INGESTION COMPLETE")
    print(f"{'='*60}")
    print(f"Total documents ingested: {len(processed_docs)}")
    print(f"Vector index name: gdpr_vector_index")
    print(f"Node label: GDPRArticle")
    print(f"{'='*60}\n")
    
    return len(processed_docs)


def test_search(query: str = "biometric data processing"):
    """Test the vector search after ingestion."""
    print(f"\n🔎 Testing search with query: '{query}'")
    
    url = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "Occultashield_neo4j")
    
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    vector_store = Neo4jVector.from_existing_graph(
        embedding=embeddings,
        url=url,
        username=username,
        password=password,
        index_name="gdpr_vector_index",
        node_label="GDPRArticle",
        text_node_properties=["content", "title"],
        embedding_node_property="embedding"
    )
    
    results = vector_store.similarity_search_with_score(query, k=3)
    
    print(f"\nTop {len(results)} results:")
    for i, (doc, score) in enumerate(results):
        print(f"\n--- Result {i+1} (score: {score:.4f}) ---")
        print(f"Title: {doc.metadata.get('title', 'N/A')}")
        print(f"Content: {doc.page_content[:200]}...")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # Default path - update this to your GDPR PDF location
        pdf_path = r"path/to/your/gdpr.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ Error: PDF file not found at {pdf_path}")
        print("Usage: python ingest_gdpr.py <path_to_gdpr_pdf>")
        sys.exit(1)
    
    # Run ingestion
    ingest_gdpr_pdf(pdf_path, clear_existing=True)
    
    # Test search
    test_search("facial recognition biometric data")
