"""
Knowledge base models for AURA.

This module defines models for storing knowledge sources and their vector embeddings
for semantic search. Supports both pgvector (PostgreSQL) and JSON-in-Text (SQLite)
storage for embeddings, enabling RAG pipeline integration across database backends.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, Index, Enum
from sqlalchemy.orm import relationship
from config.db import Base
from app.models.types import GUID
from datetime import datetime
import uuid

try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    Vector = None

from app.models.enums import CategoryEnum


class KnowledgeSource(Base):
    """
    Represents a knowledge source (document, article, FAQ, etc.).

    Each source is chunked and embedded for semantic search.
    """
    __tablename__ = "knowledge_sources"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False, index=True)
    description = Column(Text)
    content = Column(Text, nullable=False)  # Main content to be embedded
    file_path = Column(String, nullable=True)  # Path to source file in uploads/ (PDF, .md, .doc)
    category = Column(Enum(CategoryEnum), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    chunks = relationship("KnowledgeChunk", back_populates="source", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('ix_knowledge_sources_title_category', 'title', 'category'),
    )


class KnowledgeChunk(Base):
    """
    Represents a chunk of text from a knowledge source with its vector embedding.

    Uses pgvector for efficient similarity search.
    """
    __tablename__ = "knowledge_chunks"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    source_id = Column(GUID(), ForeignKey("knowledge_sources.id"), nullable=False)
    text = Column(Text, nullable=False)
    index = Column(Integer, nullable=False)  # Position in document

    # Vector embedding (768 dimensions for gemini-embedding-001)
    if PGVECTOR_AVAILABLE:
        embedding = Column(Vector(768))
    else:
        embedding = Column(Text)  # Fallback to text if pgvector not available

    token_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    source = relationship("KnowledgeSource", back_populates="chunks")

    # Indexes for vector similarity search
    if PGVECTOR_AVAILABLE:
        __table_args__ = (
            Index('ix_knowledge_chunks_embedding_cosine', 'embedding', postgresql_using='ivfflat', postgresql_ops={'embedding': 'vector_cosine_ops'}),
            Index('ix_knowledge_chunks_source_id', 'source_id'),
        )
    else:
        __table_args__ = (
            Index('ix_knowledge_chunks_source_id', 'source_id'),
        )
