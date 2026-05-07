"""
Knowledge Processing Pipeline for AURA RAG.

Adapted from nexora/backend/pipelines/knowledge.py.
Uses LangGraph for orchestration + sentence-wise chunking + Gemini embeddings.

Pipeline steps (LangGraph nodes):
1. Load & validate KnowledgeSource from DB
2. Split into sentence-wise chunks
3. Generate embeddings with Gemini Embedding API
4. Store KnowledgeChunks with embeddings to database
5. Update task status and cleanup
"""

from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
from uuid import UUID
import logging
import json
import re

from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from config.db import SessionLocal
from app.models.knowledge import KnowledgeSource, KnowledgeChunk
from app.models.task import Task
from app.models.enums import TaskStatusEnum
from app.services.rag.embedding_service import generate_embeddings_batch

logger = logging.getLogger(__name__)

# Configuration for sentence-wise chunking
SENTENCES_PER_CHUNK = 3   # Group N sentences into one chunk
SENTENCE_OVERLAP = 1      # Overlap N sentences between consecutive chunks


# ============================================================================
# SENTENCE SPLITTING UTILITIES
# ============================================================================

def split_into_sentences(text: str) -> List[str]:
    """
    Split text into individual sentences using a two-pass approach.

    Pass 1: Split on sentence-ending punctuation (. ! ?) followed by
            whitespace and an uppercase letter.
    Pass 2: Rejoin false splits caused by abbreviations (Dr., Mr., etc.)

    Handles:
    - Standard sentence endings (. ! ?)
    - Abbreviations (Dr., Mr., Mrs., etc.)
    - Decimal numbers (3.14)
    - Newline-separated content
    """
    # Normalize whitespace
    text = text.strip()
    if not text:
        return []

    # Known abbreviations that should NOT trigger a sentence split
    ABBREVIATIONS = {
        'mr', 'mrs', 'ms', 'dr', 'prof', 'jr', 'sr', 'inc', 'ltd', 'corp',
        'vs', 'etc', 'avg', 'approx', 'dept', 'est', 'govt', 'max', 'min',
        'no', 'vol', 'fig', 'eq', 'ref', 'ch', 'sec', 'pt', 'st',
        'e.g', 'i.e', 'al'
    }

    # Split on paragraph boundaries first
    paragraphs = re.split(r'\n\s*\n', text)

    sentences = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Split on . ! ? followed by whitespace and an uppercase letter or quote
        # Uses a simple split pattern that Python's re can handle
        raw_parts = re.split(r'([.!?])\s+(?=[A-Z"\'])', para)

        # Reassemble: raw_parts alternates between text and the delimiter
        reassembled = []
        i = 0
        while i < len(raw_parts):
            if i + 1 < len(raw_parts) and raw_parts[i + 1] in '.!?':
                # Attach the punctuation back to the sentence
                reassembled.append(raw_parts[i] + raw_parts[i + 1])
                i += 2
            else:
                reassembled.append(raw_parts[i])
                i += 1

        # Rejoin abbreviation-triggered false splits
        merged = []
        for part in reassembled:
            part = part.strip()
            if not part:
                continue

            if merged:
                # Check if previous sentence ended with an abbreviation
                prev = merged[-1]
                last_word = prev.rstrip('.').rsplit(None, 1)[-1].lower() if prev else ''
                if last_word in ABBREVIATIONS:
                    # Rejoin: the split was a false positive
                    merged[-1] = prev + ' ' + part
                    continue

            merged.append(part)

        sentences.extend(merged)

    return sentences


def group_sentences_into_chunks(
    sentences: List[str],
    sentences_per_chunk: int = SENTENCES_PER_CHUNK,
    overlap: int = SENTENCE_OVERLAP
) -> List[str]:
    """
    Group sentences into overlapping chunks for better context.

    Args:
        sentences: List of individual sentences
        sentences_per_chunk: Number of sentences per chunk
        overlap: Number of overlapping sentences between chunks

    Returns:
        List of chunk strings (each containing multiple sentences)
    """
    if not sentences:
        return []

    # If very few sentences, return as a single chunk
    if len(sentences) <= sentences_per_chunk:
        return [" ".join(sentences)]

    chunks = []
    step = max(1, sentences_per_chunk - overlap)

    for i in range(0, len(sentences), step):
        chunk_sentences = sentences[i:i + sentences_per_chunk]
        chunk_text = " ".join(chunk_sentences)

        if chunk_text.strip():
            chunks.append(chunk_text.strip())

        # Stop if we've covered all sentences
        if i + sentences_per_chunk >= len(sentences):
            break

    return chunks


# ============================================================================
# STATE DEFINITION
# ============================================================================

class KnowledgeState(TypedDict, total=False):
    """Graph state for knowledge processing pipeline."""
    source_id: str
    task_id: Optional[str]
    source_data: Optional[Dict[str, Any]]
    chunks: Optional[List[str]]
    embeddings: Optional[List[List[float]]]
    metadata: Optional[Dict[str, Any]]
    error: Optional[str]
    status: Optional[str]


# ============================================================================
# PIPELINE NODES
# ============================================================================

def load_and_validate(state: KnowledgeState) -> KnowledgeState:
    """
    Node 1: Load KnowledgeSource from database and validate.

    If the source has a file_path, extracts text from the uploaded file
    (PDF, .md, .doc, .docx, .txt) and uses that as the content.
    """
    from app.services.rag.file_extractor import extract_text_from_file

    session: Session = SessionLocal()
    try:
        source_id = UUID(state["source_id"])
        source = session.query(KnowledgeSource).filter(
            KnowledgeSource.id == source_id
        ).first()

        if not source:
            state["error"] = f"KnowledgeSource {source_id} not found"
            state["status"] = "failed"
            return state

        # Determine content: file extraction takes priority
        content = None
        content_origin = "database"

        if source.file_path:
            logger.info("Extracting content from file: %s", source.file_path)
            content = extract_text_from_file(source.file_path)
            if content:
                content_origin = f"file:{source.file_path}"
                # Update the stored content with extracted text
                source.content = content
                session.commit()
                logger.info("Extracted %d chars from file: %s", len(content), source.file_path)
            else:
                logger.warning(
                    "File extraction failed for %s, falling back to stored content",
                    source.file_path
                )

        if not content:
            content = source.content

        if not content or len(content.strip()) == 0:
            state["error"] = "Source content is empty (no text content and no valid file)"
            state["status"] = "failed"
            return state

        # Check size limits (10MB)
        if len(content) > 10 * 1024 * 1024:
            state["error"] = "Source content exceeds 10MB limit"
            state["status"] = "failed"
            return state

        # Store serializable data (not SQLAlchemy object)
        state["source_data"] = {
            "id": str(source.id),
            "title": source.title,
            "content": content,
            "category": source.category.value if hasattr(source.category, 'value') else str(source.category)
        }
        state["status"] = "validated"
        state["metadata"] = {
            "source_id": str(source.id),
            "title": source.title,
            "category": state["source_data"]["category"],
            "content_length": len(content),
            "content_origin": content_origin,
            "file_path": source.file_path
        }

        logger.info(
            "Loaded KnowledgeSource %s (%d chars, origin: %s)",
            source.id, len(content), content_origin
        )

        # Update task status if tracking
        if state.get("task_id"):
            task = session.query(Task).filter(
                Task.id == UUID(state["task_id"])
            ).first()
            if task:
                task.status = TaskStatusEnum.IN_PROGRESS.value
                session.commit()

        return state

    except Exception as e:
        logger.error("Error loading source: %s", str(e))
        state["error"] = str(e)
        state["status"] = "failed"
        return state
    finally:
        session.close()


def chunk_document(state: KnowledgeState) -> KnowledgeState:
    """
    Node 2: Split content into sentence-wise chunks.

    Uses sentence boundary detection to split text, then groups
    sentences into overlapping chunks (default: 3 sentences per chunk,
    1 sentence overlap) for better semantic coherence.
    """
    if state.get("error"):
        return state

    try:
        source_data = state["source_data"]
        content = source_data["content"]

        # Step 1: Split into sentences
        sentences = split_into_sentences(content)

        if not sentences:
            state["error"] = "No sentences found in content"
            state["status"] = "failed"
            return state

        # Step 2: Group sentences into overlapping chunks
        chunks = group_sentences_into_chunks(
            sentences,
            sentences_per_chunk=SENTENCES_PER_CHUNK,
            overlap=SENTENCE_OVERLAP
        )

        state["chunks"] = chunks
        state["status"] = "chunked"

        state["metadata"]["total_sentences"] = len(sentences)
        state["metadata"]["chunk_count"] = len(chunks)
        state["metadata"]["sentences_per_chunk"] = SENTENCES_PER_CHUNK
        state["metadata"]["sentence_overlap"] = SENTENCE_OVERLAP
        state["metadata"]["avg_chunk_size"] = (
            sum(len(c) for c in chunks) // len(chunks) if chunks else 0
        )

        logger.info(
            "Sentence-wise chunking: %d sentences -> %d chunks for source %s "
            "(avg size: %d chars)",
            len(sentences), len(chunks), source_data["id"],
            state["metadata"]["avg_chunk_size"]
        )

        return state

    except Exception as e:
        logger.error("Error chunking document: %s", str(e))
        state["error"] = str(e)
        state["status"] = "failed"
        return state


def generate_embeddings(state: KnowledgeState) -> KnowledgeState:
    """Node 3: Generate embeddings using Gemini embedding model."""
    if state.get("error"):
        return state

    try:
        chunks = state["chunks"]
        if not chunks:
            state["error"] = "No chunks to embed"
            state["status"] = "failed"
            return state

        logger.info("Generating embeddings for %d chunks using Gemini", len(chunks))

        all_embeddings = generate_embeddings_batch(chunks)

        if len(all_embeddings) != len(chunks):
            logger.error(
                "Embedding count mismatch: %d vs %d",
                len(all_embeddings), len(chunks)
            )
            state["error"] = "Embedding generation failed"
            state["status"] = "failed"
            return state

        state["embeddings"] = all_embeddings
        state["status"] = "embedded"

        state["metadata"]["embeddings_generated"] = len(all_embeddings)
        state["metadata"]["embedding_dimension"] = (
            len(all_embeddings[0]) if all_embeddings else 0
        )

        logger.info(
            "Generated %d embeddings (dim=%d) for source %s",
            len(all_embeddings),
            state["metadata"]["embedding_dimension"],
            state["source_data"]["id"]
        )

        return state

    except Exception as e:
        logger.error("Error generating embeddings: %s", str(e))
        state["error"] = str(e)
        state["status"] = "failed"
        return state


def store_chunks(state: KnowledgeState) -> KnowledgeState:
    """Node 4: Store chunks and embeddings in database."""
    if state.get("error"):
        return state

    session: Session = SessionLocal()
    try:
        source_data = state["source_data"]
        chunks = state["chunks"]
        embeddings = state["embeddings"]
        source_id = UUID(source_data["id"])

        source = session.query(KnowledgeSource).filter(
            KnowledgeSource.id == source_id
        ).first()

        if not source:
            state["error"] = f"Source {source_id} not found in database"
            state["status"] = "failed"
            return state

        if len(chunks) != len(embeddings):
            state["error"] = "Chunk and embedding count mismatch"
            state["status"] = "failed"
            return state

        from app.services.rag.chroma_client import get_chroma_collection
        collection = get_chroma_collection()

        # Delete old chunks for idempotency from SQLite and ChromaDB
        old_chunks = session.query(KnowledgeChunk).filter(
            KnowledgeChunk.source_id == source.id
        ).all()
        
        old_chunk_ids = [str(c.id) for c in old_chunks]
        if old_chunk_ids:
            try:
                collection.delete(ids=old_chunk_ids)
            except Exception as e:
                logger.warning("Error deleting old chunks from ChromaDB: %s", e)
                
        deleted = session.query(KnowledgeChunk).filter(
            KnowledgeChunk.source_id == source.id
        ).delete()
        session.commit()
        logger.info("Deleted %d old chunks for source %s", deleted, source.id)

        # Store new chunks with embeddings (as JSON text for SQLite)
        stored_chunks = []
        chroma_ids = []
        chroma_embeddings = []
        chroma_documents = []
        chroma_metadatas = []
        
        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            # For SQLite, store embedding as JSON string
            embedding_value = json.dumps(embedding)

            chunk = KnowledgeChunk(
                source_id=source.id,
                text=chunk_text,
                index=i,
                embedding=embedding_value,
                token_count=len(chunk_text.split()),
                word_count=len(chunk_text.split())
            )
            session.add(chunk)
            session.flush() # flush to generate chunk.id
            stored_chunks.append(chunk)
            
            chroma_ids.append(str(chunk.id))
            chroma_embeddings.append(embedding)
            chroma_documents.append(chunk_text)
            chroma_metadatas.append({
                "source_id": str(source.id),
                "source_title": source.title,
                "category": source.category.value if hasattr(source.category, 'value') else str(source.category),
                "index": i
            })
            
        if chroma_ids:
            try:
                collection.add(
                    ids=chroma_ids,
                    embeddings=chroma_embeddings,
                    documents=chroma_documents,
                    metadatas=chroma_metadatas
                )
            except Exception as e:
                logger.warning("Error adding chunks to ChromaDB: %s", e)

        # Update source chunk count
        source.chunk_count = len(stored_chunks)
        source.updated_at = datetime.utcnow()
        session.add(source)
        session.commit()

        state["status"] = "stored"
        state["metadata"]["chunks_stored"] = len(stored_chunks)

        logger.info(
            "Stored %d chunks with embeddings for source %s",
            len(stored_chunks), source.id
        )

        return state

    except Exception as e:
        session.rollback()
        logger.error("Error storing chunks: %s", str(e))
        state["error"] = str(e)
        state["status"] = "failed"
        return state
    finally:
        session.close()


def finalize_task(state: KnowledgeState) -> KnowledgeState:
    """Node 5: Update task status and cleanup."""
    session: Session = SessionLocal()
    try:
        if not state.get("task_id"):
            return state

        task_id = UUID(state["task_id"])
        task = session.query(Task).filter(Task.id == task_id).first()

        if task:
            if state.get("error"):
                task.status = TaskStatusEnum.FAILED.value
                task.error_message = state["error"]
                logger.error("Task %s failed: %s", task_id, state["error"])
            else:
                task.status = TaskStatusEnum.COMPLETED.value
                task.completed_at = datetime.utcnow()

                metadata = json.loads(task.metadata_) if task.metadata_ else {}
                metadata.update({
                    "chunks_created": state["metadata"].get("chunk_count", 0),
                    "embeddings_generated": state["metadata"].get("embeddings_generated", 0),
                    "processing_time": (datetime.utcnow() - task.created_at).total_seconds()
                })
                task.metadata_ = json.dumps(metadata)
                logger.info("Task %s completed successfully", task_id)

            session.commit()

        state["status"] = "completed" if not state.get("error") else "failed"
        return state

    except Exception as e:
        logger.error("Error finalizing task: %s", str(e))
        return state
    finally:
        session.close()


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def build_knowledge_graph():
    """Build and compile the knowledge processing graph."""
    graph = StateGraph(KnowledgeState)

    graph.add_node("load_and_validate", load_and_validate)
    graph.add_node("chunk_document", chunk_document)
    graph.add_node("generate_embeddings", generate_embeddings)
    graph.add_node("store_chunks", store_chunks)
    graph.add_node("finalize_task", finalize_task)

    graph.set_entry_point("load_and_validate")

    graph.add_conditional_edges(
        "load_and_validate",
        lambda x: "chunk_document" if not x.get("error") else "finalize_task",
        {
            "chunk_document": "chunk_document",
            "finalize_task": "finalize_task"
        }
    )

    graph.add_edge("chunk_document", "generate_embeddings")
    graph.add_edge("generate_embeddings", "store_chunks")
    graph.add_edge("store_chunks", "finalize_task")
    graph.add_edge("finalize_task", END)

    return graph.compile()


# ============================================================================
# PIPELINE EXECUTION
# ============================================================================

async def process_knowledge_source(
    source_id: str,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run the knowledge processing pipeline for a given source.

    Args:
        source_id: UUID of the knowledge source
        task_id: Optional UUID of the tracking task

    Returns:
        Processing result dictionary
    """
    try:
        graph = build_knowledge_graph()

        initial_state = KnowledgeState(
            source_id=source_id,
            task_id=task_id,
            status="pending",
            metadata={}
        )

        logger.info("Starting knowledge processing for source %s", source_id)
        final_state = await graph.ainvoke(initial_state)

        return {
            "success": not bool(final_state.get("error")),
            "status": final_state.get("status", "unknown"),
            "source_id": source_id,
            "chunks_created": final_state.get("metadata", {}).get("chunk_count", 0),
            "embeddings_generated": final_state.get("metadata", {}).get("embeddings_generated", 0),
            "error": final_state.get("error")
        }

    except Exception as e:
        logger.error("Pipeline execution failed: %s", str(e))
        return {
            "success": False,
            "status": "failed",
            "source_id": source_id,
            "error": str(e)
        }
