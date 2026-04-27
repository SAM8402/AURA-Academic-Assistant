"""
SQLAlchemy ORM model for SlideDeck.
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from config.db import Base


class SlideDeck(Base):
    """
    Represents a slide deck containing multiple slides.

    The `slides` attribute stores an array of slide objects,
    typically with 'title' and 'content' (markdown) keys.
    """
    __tablename__ = "slide_decks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    slides = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    course = relationship("Course", back_populates="slide_decks")
    creator = relationship("User", back_populates="slide_decks_created")
