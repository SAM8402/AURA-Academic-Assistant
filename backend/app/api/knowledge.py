"""
Knowledge Base API Endpoints for AURA.

Provides CRUD operations for knowledge sources and semantic search capabilities.
Includes RAG pipeline integration for automatic embedding generation and
semantic search using Gemini Embedding API + cosine similarity.
"""

import logging
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from uuid import UUID

from config.db import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.knowledge import KnowledgeSource, KnowledgeChunk
from app.models.task import Task
from app.models.enums import TaskTypeEnum, TaskStatusEnum, CategoryEnum
from app.schemas.knowledge_schema import (
    KnowledgeSourceCreate,
    KnowledgeSourceUpdate,
    KnowledgeSourceOut,
    KnowledgeChunkOut,
    SemanticSearchRequest,
    PaginatedKnowledgeSourceResponse,
    KnowledgeStats
)

# RAG Pipeline imports
from app.services.rag.ingest_pipeline import process_knowledge_source
from app.services.rag.search_pipeline import search as rag_search

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


# ============================================================================
# KNOWLEDGE SOURCE ENDPOINTS
# ============================================================================

@router.post("/sources", response_model=KnowledgeSourceOut, status_code=status.HTTP_201_CREATED)
async def create_knowledge_source(
    source: KnowledgeSourceCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new knowledge source.

    - **title**: Source title (required)
    - **description**: Source description (optional)
    - **content**: Full text content (required)
    - **category**: Category for organization (required)
    - **is_active**: Whether source is active for search (default: true)

    Automatically triggers the RAG embedding pipeline to chunk and embed
    the content for semantic search.
    """
    try:
        # Create knowledge source
        db_source = KnowledgeSource(
            title=source.title,
            description=source.description,
            content=source.content,
            category=source.category,
            is_active=source.is_active
        )

        db.add(db_source)
        db.commit()
        db.refresh(db_source)

        # Trigger RAG embedding pipeline in background
        source_id = str(db_source.id)
        background_tasks.add_task(_run_embedding_pipeline, source_id)
        logger.info("Triggered embedding pipeline for source: %s", source_id)

        return db_source

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create knowledge source: {str(e)}"
        )


@router.post("/sources/upload", response_model=KnowledgeSourceOut, status_code=status.HTTP_201_CREATED)
async def upload_knowledge_file(
    background_tasks: BackgroundTasks,
    title: str = Query(..., description="Source title"),
    category: str = Query(..., description="Category (e.g. courses, assignments)"),
    description: Optional[str] = Query(None, description="Source description"),
    file: UploadFile = File(..., description="PDF, .md, .doc, .docx, or .txt file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a file (PDF, .md, .doc, .docx, .txt) as a knowledge source.

    The file is saved to uploads/knowledge/ and the RAG pipeline extracts
    text content, chunks it into sentences, and generates embeddings.

    Supported formats: .pdf, .md, .txt, .doc, .docx
    """
    import os
    import shutil

    ext = os.path.splitext(file.filename)[1].lower()
    supported = {".pdf", ".md", ".txt", ".doc", ".docx"}
    if ext not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {', '.join(supported)}"
        )

    try:
        # Save file to uploads/knowledge/
        upload_dir = os.path.join("uploads", "knowledge")
        os.makedirs(upload_dir, exist_ok=True)

        # Use a unique filename to avoid collisions
        import uuid as _uuid
        safe_name = f"{_uuid.uuid4().hex[:8]}_{file.filename}"
        file_path = os.path.join(upload_dir, safe_name)

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        abs_file_path = os.path.abspath(file_path)
        logger.info("Saved uploaded file: %s", abs_file_path)

        # Validate category
        try:
            cat_enum = CategoryEnum(category)
        except ValueError:
            valid = [c.value for c in CategoryEnum]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category: {category}. Valid: {valid}"
            )

        # Create knowledge source with file_path (content will be extracted by pipeline)
        db_source = KnowledgeSource(
            title=title,
            description=description or f"Uploaded from {file.filename}",
            content="[Pending file extraction]",  # Placeholder — pipeline will fill this
            file_path=abs_file_path,
            category=cat_enum,
            is_active=True
        )

        db.add(db_source)
        db.commit()
        db.refresh(db_source)

        # Trigger RAG pipeline (will extract text from file, chunk, embed)
        source_id = str(db_source.id)
        background_tasks.add_task(_run_embedding_pipeline, source_id)
        logger.info("Triggered file-based embedding pipeline for: %s → %s", file.filename, source_id)

        return db_source

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload knowledge file: {str(e)}"
        )


@router.get("/categories", response_model=List[str])
async def get_categories(
    current_user: User = Depends(get_current_user)
):
    """
    Get available categories for knowledge sources.

    Returns a list of all available category values.
    """
    return [category.value for category in CategoryEnum]


@router.get("/sources", response_model=PaginatedKnowledgeSourceResponse)
async def list_knowledge_sources(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List knowledge sources with pagination and filters.

    Supports:
    - Full-text search across title, description, and content
    - Category filtering
    - Active status filtering
    - Pagination
    """
    try:
        query = db.query(KnowledgeSource)

        # Apply search
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                or_(
                    KnowledgeSource.title.ilike(search_filter),
                    KnowledgeSource.description.ilike(search_filter),
                    KnowledgeSource.content.ilike(search_filter)
                )
            )

        # Apply filters
        if category:
            try:
                category_enum = CategoryEnum(category)
                query = query.filter(KnowledgeSource.category == category_enum)
            except ValueError:
                pass  # Invalid category, ignore filter

        if is_active is not None:
            query = query.filter(KnowledgeSource.is_active == is_active)

        # Get total count
        total = query.count()

        # Apply pagination
        query = query.order_by(KnowledgeSource.created_at.desc())
        skip = (page - 1) * size
        sources = query.offset(skip).limit(size).all()

        # Calculate pages
        pages = (total + size - 1) // size if total > 0 else 1

        return PaginatedKnowledgeSourceResponse(
            items=sources,
            total=total,
            page=page,
            size=size,
            pages=pages
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve knowledge sources: {str(e)}"
        )


@router.get("/sources/{source_id}", response_model=KnowledgeSourceOut)
async def get_knowledge_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific knowledge source by ID.

    Returns detailed information about a single knowledge source.
    """
    source = db.query(KnowledgeSource).filter(
        KnowledgeSource.id == source_id
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge source not found"
        )

    return source


@router.put("/sources/{source_id}", response_model=KnowledgeSourceOut)
async def update_knowledge_source(
    source_id: UUID,
    source_update: KnowledgeSourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a knowledge source.

    - Only provided fields will be updated
    - If content is modified, re-embedding should be triggered (requires background tasks)
    """
    source = db.query(KnowledgeSource).filter(
        KnowledgeSource.id == source_id
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge source not found"
        )

    try:
        content_modified = False

        # Update fields
        if source_update.title is not None:
            source.title = source_update.title
        if source_update.description is not None:
            source.description = source_update.description
        if source_update.content is not None:
            source.content = source_update.content
            content_modified = True
        if source_update.category is not None:
            source.category = source_update.category
        if source_update.is_active is not None:
            source.is_active = source_update.is_active

        db.commit()
        db.refresh(source)

        # TODO: Trigger re-embedding if content was modified and Celery is configured
        # if content_modified:
        #     process_document.delay(str(source_id))

        return source

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update knowledge source: {str(e)}"
        )


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a knowledge source.

    This will also delete all associated chunks and embeddings.
    """
    source = db.query(KnowledgeSource).filter(
        KnowledgeSource.id == source_id
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge source not found"
        )

    try:
        db.delete(source)
        db.commit()
        return None

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete knowledge source: {str(e)}"
        )


@router.get("/sources/{source_id}/chunks", response_model=List[KnowledgeChunkOut])
async def get_source_chunks(
    source_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all text chunks for a knowledge source.

    Returns all chunks with their embeddings (if generated).
    """
    source = db.query(KnowledgeSource).filter(
        KnowledgeSource.id == source_id
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge source not found"
        )

    chunks = db.query(KnowledgeChunk).filter(
        KnowledgeChunk.source_id == source_id
    ).order_by(KnowledgeChunk.index).all()

    return chunks


@router.post("/search")
async def semantic_search(
    search_request: SemanticSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Perform semantic search across knowledge base using RAG pipeline.

    Uses Gemini embeddings + cosine similarity for semantic matching.
    Returns ranked results with similarity scores.
    """
    try:
        # Build filters
        filters = {}
        if search_request.category:
            filters["category"] = search_request.category

        # Run RAG search pipeline
        result = await rag_search(
            query=search_request.query,
            top_k=search_request.top_k,
            filters=filters
        )

        return {
            "query": search_request.query,
            "results": result.get("results", []),
            "total_results": result.get("total_results", 0),
            "used_cache": result.get("used_cache", False),
            "metadata": result.get("metadata", {}),
            "status": "success" if result.get("success") else "failed",
            "error": result.get("error")
        }

    except Exception as e:
        logger.error("Semantic search failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}"
        )


@router.post("/sources/{source_id}/embed")
async def embed_knowledge_source(
    source_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger embedding generation for a knowledge source.

    Use this to re-embed a source after content updates or if
    initial embedding failed.
    """
    source = db.query(KnowledgeSource).filter(
        KnowledgeSource.id == source_id
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge source not found"
        )

    # Trigger embedding pipeline in background
    background_tasks.add_task(_run_embedding_pipeline, str(source_id))

    return {
        "message": "Embedding pipeline triggered",
        "source_id": str(source_id),
        "status": "processing"
    }


@router.get("/stats", response_model=KnowledgeStats)
async def get_knowledge_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics about the knowledge base.

    Returns counts and metrics for knowledge sources and chunks.
    """
    try:
        total_sources = db.query(KnowledgeSource).count()
        active_sources = db.query(KnowledgeSource).filter(
            KnowledgeSource.is_active == True
        ).count()
        total_chunks = db.query(KnowledgeChunk).count()

        # Count sources by category
        sources_by_category = {}
        for category in CategoryEnum:
            count = db.query(KnowledgeSource).filter(
                KnowledgeSource.category == category
            ).count()
            sources_by_category[category.value] = count

        # Calculate average chunks per source
        avg_chunks = total_chunks / total_sources if total_sources > 0 else 0

        return KnowledgeStats(
            total_sources=total_sources,
            active_sources=active_sources,
            total_chunks=total_chunks,
            sources_by_category=sources_by_category,
            avg_chunks_per_source=round(avg_chunks, 2)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve knowledge statistics: {str(e)}"
        )


# ============================================================================
# BACKGROUND TASK HELPERS
# ============================================================================

def _run_embedding_pipeline(source_id: str):
    """
    Run the RAG embedding pipeline in a background task.

    Bridges sync BackgroundTasks context with async pipeline.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(process_knowledge_source(source_id))
        loop.close()

        if result.get("success"):
            logger.info(
                "Embedding pipeline completed for source %s: %d chunks, %d embeddings",
                source_id,
                result.get("chunks_created", 0),
                result.get("embeddings_generated", 0)
            )
        else:
            logger.error(
                "Embedding pipeline failed for source %s: %s",
                source_id, result.get("error")
            )

    except Exception as e:
        logger.error("Background embedding pipeline error for source %s: %s", source_id, e)
