"""
Pydantic schemas for Quiz API.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from .user_schema import UserResponse


# AI Generation Schemas
class QuizGenerationRequest(BaseModel):
    """Schema for requesting AI-powered quiz generation."""
    course_id: int = Field(..., example=1)
    title: str = Field(..., min_length=5, max_length=100, example="Python Basics Quiz")
    description: Optional[str] = Field(None, example="A quiz covering fundamental Python concepts.")
    topics: List[str] = Field(..., min_items=1, example=["variables", "data types", "loops"])
    difficulty: str = Field("Medium", example="Easy")
    marks_per_question: int = Field(5, gt=0, example=5)
    num_questions: int = Field(10, gt=0, le=20, example=10)
    use_latex: bool = Field(False, example=False, description="Enable LaTeX rendering for questions.")
    publish_mode: str = Field("manual", example="manual", description="'manual' for manual review, 'auto' for auto-publish.")


class QuizUpdateRequest(BaseModel):
    """Schema for requesting an update to an existing quiz using AI."""
    feedback: str = Field(..., example="Make question 3 harder and add a question about functions.")


# Quiz Attempt Schemas
class Answer(BaseModel):
    """Represents a user's answer to a single question."""
    question_index: int
    selected_options: List[str]


class QuizAttemptRequest(BaseModel):
    """Schema for submitting answers to a quiz."""
    answers: List[Answer]


class QuizAttemptResponse(BaseModel):
    """Schema for returning the result of a quiz attempt."""
    id: int
    quiz_id: int
    user: UserResponse
    score: int
    total_marks: int
    submitted_answers: List[Answer]
    attempted_at: datetime

    class Config:
        from_attributes = True


# General Quiz Schemas
class QuizResponse(BaseModel):
    """Schema for a quiz response, including its questions."""
    id: int
    title: str
    description: Optional[str]
    course_id: int
    creator: UserResponse
    questions: Dict[str, Any]  # The full JSON from the AI service
    use_latex: bool
    publish_mode: str
    is_published: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

    class Config:
        from_attributes = True