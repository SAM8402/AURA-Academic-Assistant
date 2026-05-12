"""
RAG Pipeline Diagnostic — run with: python _diagnose_rag.py
"""
import sys, os, json

# === STEP 1: Check chromadb ===
print("=" * 60)
print("STEP 1: Checking chromadb installation")
print("=" * 60)
try:
    import chromadb
    print(f"[OK] chromadb {chromadb.__version__} installed")
except ImportError as e:
    print(f"[FAIL] chromadb not installed: {e}")
    print("  Fix: pip install chromadb")

# === STEP 2: Check DB ===
print("\n" + "=" * 60)
print("STEP 2: Database state")
print("=" * 60)
os.environ["DATABASE_URL"] = "sqlite:///./app.db"
from config.db import SessionLocal
from app.models.knowledge import KnowledgeSource, KnowledgeChunk

db = SessionLocal()
try:
    sources = db.query(KnowledgeSource).all()
    print(f"KnowledgeSources: {len(sources)}")
    for s in sources:
        print(f"  [{s.id}] title={s.title!r}")
        print(f"        file_path={s.file_path!r}")
        print(f"        chunk_count={s.chunk_count}  is_active={s.is_active}")
        print(f"        content_preview={s.content[:80] if s.content else 'EMPTY'}...")
    
    chunks = db.query(KnowledgeChunk).all()
    print(f"KnowledgeChunks: {len(chunks)}")
    for c in chunks[:3]:
        print(f"  [{c.id}] source_id={c.source_id} index={c.index} text={c.text[:60]}...")
        print(f"        embedding_type={'str' if isinstance(c.embedding, str) else type(c.embedding).__name__} length={len(c.embedding) if c.embedding else 0}")
finally:
    db.close()

# === STEP 3: Test embedding ===
print("\n" + "=" * 60)
print("STEP 3: Testing embedding generation")
print("=" * 60)
try:
    from app.services.rag.embedding_service import generate_embedding, EMBEDDING_MODEL, _API_KEYS
    print(f"Embedding model: {EMBEDDING_MODEL}")
    print(f"API keys available: {len(_API_KEYS)}")
    if _API_KEYS:
        print(f"  First key ends with: ...{_API_KEYS[0][-6:] if len(_API_KEYS[0]) > 6 else _API_KEYS[0]}")
    
    emb = generate_embedding("What is supervised learning?")
    if emb:
        print(f"[OK] Embedding generated! dimension={len(emb)}")
        print(f"  First 5 values: {emb[:5]}")
    else:
        print("[FAIL] generate_embedding returned None")
        print("  Check GOOGLE_API_KEY in .env")
except Exception as e:
    print(f"[FAIL] Embedding exception: {e}")

# === STEP 4: Test ChromaDB search ===
print("\n" + "=" * 60)
print("STEP 4: Testing ChromaDB search")
print("=" * 60)
try:
    from app.services.rag.chroma_client import get_chroma_collection
    collection = get_chroma_collection()
    count = collection.count()
    print(f"ChromaDB collection count: {count}")
    
    if count > 0 and emb:
        results = collection.query(
            query_embeddings=[emb],
            n_results=min(5, count),
            include=["documents", "metadatas", "distances"]
        )
        if results.get("ids") and results["ids"][0]:
            print(f"[OK] Found {len(results['ids'][0])} results in ChromaDB")
            for i in range(len(results["ids"][0])):
                dist = results["distances"][0][i]
                sim = 1.0 - dist
                meta = results["metadatas"][0][i]
                doc = results["documents"][0][i]
                print(f"  [{i}] id={results['ids'][0][i]} sim={sim:.4f}")
                print(f"       source_title={meta.get('source_title','?')}")
                print(f"       text={doc[:60]}...")
        else:
            print("[WARN] ChromaDB has entries but query returned no matches")
    elif count == 0:
        print("[WARN] ChromaDB is empty — no documents were ever embedded")
except Exception as e:
    print(f"[FAIL] ChromaDB search exception: {e}")

# === STEP 5: Test semantic_search_chroma ===
print("\n" + "=" * 60)
print("STEP 5: Testing semantic_search_chroma")
print("=" * 60)
try:
    from app.services.rag.search_pipeline import semantic_search_chroma
    if emb:
        results = semantic_search_chroma(
            query_embedding=emb,
            top_k=5,
            filters={},
            similarity_threshold=0.0  # Show everything
        )
        print(f"Results count (threshold=0.0): {len(results)}")
        for r in results:
            print(f"  score={r['score']:.4f}  title={r.get('source_title','?')}  text={r.get('content','')[:60]}...")
        
        results_filtered = semantic_search_chroma(
            query_embedding=emb,
            top_k=5,
            filters={},
            similarity_threshold=0.15
        )
        print(f"Results count (threshold=0.15): {len(results_filtered)}")
except Exception as e:
    print(f"[FAIL] semantic_search_chroma exception: {e}")

# === STEP 6: Test the file exists ===
print("\n" + "=" * 60)
print("STEP 6: Checking ml_intro.md")
print("=" * 60)
md_path = os.path.abspath(os.path.join("uploads", "knowledge", "ml_intro.md"))
print(f"Expected path: {md_path}")
print(f"File exists: {os.path.exists(md_path)}")
if os.path.exists(md_path):
    from app.services.rag.file_extractor import extract_text_from_file
    content = extract_text_from_file(md_path)
    if content:
        print(f"[OK] Extracted {len(content)} chars")
        print(f"  First 100 chars: {content[:100]}")
    else:
        print("[FAIL] extract_text_from_file returned None")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
