from config.db import SessionLocal
from app.models.knowledge import KnowledgeSource, KnowledgeChunk

db = SessionLocal()
sources = db.query(KnowledgeSource).all()
print(f'KnowledgeSources count: {len(sources)}')
for s in sources:
    print(f'  id={s.id}  title={s.title!r}  file_path={s.file_path!r}  chunk_count={s.chunk_count}  is_active={s.is_active}')
print(f'KnowledgeChunks count: {db.query(KnowledgeChunk).count()}')

# Also test search
from app.services.rag.embedding_service import generate_embedding
from app.services.rag.search_pipeline import semantic_search_chroma

emb = generate_embedding("What is supervised learning?")
if emb:
    results = semantic_search_chroma(emb, top_k=5, filters={}, similarity_threshold=0.0)
    print(f'Search results (threshold=0.0): {len(results)}')
    for r in results:
        print(f'  score={r["score"]:.4f}  title={r.get("source_title","?")}  content={r.get("content","")[:80]}...')
else:
    print('Embedding generation returned None')
db.close()
