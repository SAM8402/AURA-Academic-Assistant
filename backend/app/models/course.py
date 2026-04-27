"""
SQLAlchemy ORM model for Course.
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from config.db import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("User")
    quizzes = relationship("Quiz", back_populates="course", cascade="all, delete-orphan")
    slide_decks = relationship("SlideDeck", back_populates="course", cascade="all, delete-orphan")
    assigned_users = relationship("UserCourse", back_populates="course", cascade="all, delete-orphan")