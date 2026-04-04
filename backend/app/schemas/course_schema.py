"""
Pydantic schemas for Course API.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserSimpleResponse(BaseModel):
    """A simplified user schema for nested responses."""
    id: int
    email: str

    
    class Config:
        from_attributes = True
class CourseBase(BaseModel):
    """Base schema for a course with common attributes."""
    name: str = Field(..., min_length=3, max_length=100, example="Introduction to Machine Learning")
    description: Optional[str] = Field(None, example="A foundational course on ML concepts.")


class CourseCreate(CourseBase):
    """Schema for creating a new course."""
    pass


class CourseUpdate(BaseModel):
    """Schema for updating an existing course. All fields are optional."""
    name: Optional[str] = Field(None, min_length=3, max_length=100, example="Advanced Machine Learning")
    description: Optional[str] = Field(None, example="An in-depth course on advanced ML concepts.")


class CourseResponse(CourseBase):
    """Schema for a course response, including read-only fields."""
    id: int
    created_at: datetime
    creator: UserSimpleResponse

    class Config:
        from_attributes = True