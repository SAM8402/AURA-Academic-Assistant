"""
Pydantic schemas for Tag API.
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
class TagBase(BaseModel):
    """Base schema for a tag."""
    name: str = Field(..., min_length=2, max_length=50, example="python")


class TagCreate(TagBase):
    """Schema for creating a new tag."""
    pass


class TagUpdate(TagBase):
    """Schema for updating an existing tag."""
    pass


class TagResponse(TagBase):
    """Schema for a tag response, including read-only fields."""
    id: int
    created_at: datetime
    creator: UserSimpleResponse

    class Config:
        from_attributes = True