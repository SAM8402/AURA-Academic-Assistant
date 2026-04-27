# backend/app/models/doubts.py

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from config.db import Base


class DoubtUpload(Base):
    __tablename__ = "doubt_uploads"

    id = Column(Integer, primary_key=True, index=True)
    course_code = Column(String(50), index=True, nullable=False)
    source = Column(String(100), nullable=False)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to child messages
    messages = relationship(
        "DoubtMessage",
        back_populates="upload",
        cascade="all, delete-orphan"
    )


class DoubtMessage(Base):
    __tablename__ = "doubt_messages"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("doubt_uploads.id"), index=True, nullable=False)

    author_role = Column(String(50), nullable=False)  # e.g., "student", "ta"
    text = Column(Text, nullable=False)

    upload = relationship("DoubtUpload", back_populates="messages")
