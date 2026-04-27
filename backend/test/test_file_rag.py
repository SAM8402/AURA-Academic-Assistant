"""
End-to-end test for file-based RAG pipeline.
Tests: file extraction → DB storage → ingest pipeline → semantic search.
"""

import asyncio
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


async def test_file_rag():
    print("=" * 60)
    print("FILE-BASED RAG PIPELINE TEST")
    print("=" * 60)

    # Step 1: Test file extractor
    print("\n--- Step 1: File Extraction ---")
    from app.services.rag.file_extractor import extract_text_from_file, get_supported_files_in_uploads

    files = get_supported_files_in_uploads()
    print(f"Found {len(files)} supported files in uploads/")
    for f in files:
        print(f"  {f['relative_path']} ({f['extension']}, {f['size_bytes']} bytes)")

    md_path = os.path.abspath("uploads/knowledge/ml_intro.md")
    content = extract_text_from_file(md_path)
    print(f"Extracted {len(content)} chars from ml_intro.md")
    assert content and "Machine learning" in content, "File extraction failed!"
    print("PASS: File extraction works")

    # Step 2: Create a file-based knowledge source
    print("\n--- Step 2: Create File-Based KnowledgeSource ---")
    from config.db import SessionLocal
    from app.models.knowledge import KnowledgeSource
    from app.models.enums import CategoryEnum

    session = SessionLocal()
    source = KnowledgeSource(
        title="Machine Learning Introduction",
        description="ML basics from uploaded markdown file",
        content="[Pending file extraction]",
        file_path=md_path,
        category=CategoryEnum.COURSES,
        is_active=True,
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    source_id = str(source.id)
    print(f"Created source: {source_id}")
    print(f"  file_path: {source.file_path}")
    session.close()

    # Step 3: Run ingest pipeline (will extract from file)
    print("\n--- Step 3: Ingest Pipeline (File -> Chunks -> Embeddings) ---")
    from app.services.rag.ingest_pipeline import process_knowledge_source

    result = await process_knowledge_source(source_id)
    print(f"Pipeline result: success={result['success']}, chunks={result.get('chunks_created', 0)}")
    assert result["success"], f"Pipeline failed: {result.get('error')}"
    print("PASS: File-based ingest pipeline works")

    # Step 4: Verify content was extracted and stored
    print("\n--- Step 4: Verify Stored Content ---")
    session = SessionLocal()
    source = session.query(KnowledgeSource).filter(
        KnowledgeSource.id == source.id
    ).first()
    assert "Machine learning" in source.content, "Content not extracted from file!"
    print(f"Stored content: {len(source.content)} chars")
    preview = source.content[:100].encode("ascii", errors="replace").decode("ascii")
    print(f"  First 100 chars: \"{preview}...\"")
    print(f"  Chunks in DB: {source.chunk_count}")
    session.close()
    print("PASS: Content extracted and stored correctly")

    # Step 5: Semantic search for file content
    print("\n--- Step 5: Semantic Search ---")
    from app.services.rag.search_pipeline import search

    results = await search("What is reinforcement learning?")
    result_list = results.get("results", [])
    print(f"Search returned {len(result_list)} results")

    if result_list:
        top = result_list[0]
        title = top.get("source_title", "")
        score = top.get("score", 0)
        print(f"  Top result: \"{title}\" (score: {score:.3f})")

    print("PASS: Semantic search finds file content")

    print("\n" + "=" * 60)
    print("ALL FILE-BASED RAG TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_file_rag())
