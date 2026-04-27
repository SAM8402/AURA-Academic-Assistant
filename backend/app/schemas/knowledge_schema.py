"""
Pydantic schemas for knowledge base API endpoints.

This module defines request and response models for knowledge management operations.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from app.models.enums import CategoryEnum


# Knowledge Source Schemas
class KnowledgeSourceCreate(BaseModel):
    """Schema for creating a new knowledge source."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    content: str = Field(..., min_length=1)
    category: CategoryEnum
    is_active: bool = True


class KnowledgeSourceUpdate(BaseModel):
    """Schema for updating an existing knowledge source."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    content: Optional[str] = Field(None, min_length=1)
    category: Optional[CategoryEnum] = None
    is_active: Optional[bool] = None


class KnowledgeSourceOut(BaseModel):
    """Schema for knowledge source response."""
    id: UUID
    title: str
    description: Optional[str] = None
    content: str
    file_path: Optional[str] = None
    category: CategoryEnum
    is_active: bool
    created_at: datetime
    updated_at: datetime
    chunk_count: Optional[int] = 0

    class Config:
        from_attributes = True


# Knowledge Chunk Schemas
class KnowledgeChunkOut(BaseModel):
    """Schema for knowledge chunk response."""
    id: UUID
    source_id: UUID
    text: str
    index: int
    token_count: int
    word_count: int
    embedding: Optional[List[float]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeChunkWithSource(KnowledgeChunkOut):
    """Schema for knowledge chunk with source information."""
    source_title: str
    source_category: CategoryEnum


# Task Schemas
class TaskOut(BaseModel):
    """Schema for background task response."""
    id: UUID
    task_type: str
    status: str
    source_id: Optional[UUID] = None
    metadata_: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Search Schemas
class SemanticSearchRequest(BaseModel):
    """Schema for semantic search request."""
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=50)
    category: Optional[CategoryEnum] = None


class SearchResult(BaseModel):
    """Schema for a single search result."""
    chunk_id: UUID
    text: str
    index: int
    token_count: int
    word_count: int
    source_id: UUID
    source_title: str
    source_category: CategoryEnum
    similarity_score: float
    relevance_score: float
    rank: int
    created_at: datetime


class SemanticSearchResponse(BaseModel):
    """Schema for semantic search response."""
    query: str
    results: List[SearchResult]
    total_results: int


# Pagination Schemas
class PaginationParams(BaseModel):
    """Schema for pagination parameters."""
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class PaginatedKnowledgeSourceResponse(BaseModel):
    """Schema for paginated knowledge source response."""
    items: List[KnowledgeSourceOut]
    total: int
    page: int
    size: int
    pages: int


# Filter Schemas
class SourceFilterParams(BaseModel):
    """Schema for knowledge source filtering."""
    search: Optional[str] = None
    is_active: Optional[bool] = None
    category: Optional[CategoryEnum] = None


# Knowledge Statistics
class KnowledgeStats(BaseModel):
    """Schema for knowledge base statistics."""
    total_sources: int
    active_sources: int
    total_chunks: int
    sources_by_category: dict
    avg_chunks_per_source: float
