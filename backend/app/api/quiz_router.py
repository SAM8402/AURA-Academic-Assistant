"""
API router for quiz generation and attempts.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from config.db import get_db
from app.models.user import User
from app.models.course import Course
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.schemas.quiz_schema import (
    QuizGenerationRequest, QuizUpdateRequest, QuizResponse,
    QuizAttemptRequest, QuizAttemptResponse
)
from app.api.dependencies import require_ta, require_authenticated
from app.services.quiz.generator_service import quiz_service
from app.services.quiz.db_service import quiz_db_service

router = APIRouter()


@router.post(
    "/generate",
    response_model=QuizResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new quiz (TA/Admin only)",
)
async def generate_and_save_quiz(
    request: QuizGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ta),
):
    """
    Generates a new quiz using the AI service and saves it to the database.
    If publish_mode is 'auto', the quiz is immediately published.
    """
    course = db.query(Course).filter(Course.id == request.course_id).first() # type: ignore
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Generate quiz content using the AI service
    generated_questions = await quiz_service.generate_quiz(
        course_name=course.name,
        topics=request.topics,
        difficulty=request.difficulty,
        marks_per_question=request.marks_per_question,
        num_questions=request.num_questions,
    )

    if "error" in generated_questions:
        raise HTTPException(status_code=500, detail=f"AI service error: {generated_questions.get('error')}")

    # Determine if quiz should be auto-published
    is_published = request.publish_mode == "auto"

    # Save the generated quiz to the database
    db_quiz = Quiz(
        title=request.title,
        description=request.description,
        course_id=request.course_id,
        created_by_id=current_user.id,
        questions=generated_questions,
        use_latex=request.use_latex,
        publish_mode=request.publish_mode,
        is_published=is_published,
    )
    db.add(db_quiz)
    db.commit()
    db.refresh(db_quiz)
    return db_quiz


@router.put(
    "/{quiz_id}",
    response_model=QuizResponse,
    summary="Update an existing quiz (Creator only)",
)
async def update_existing_quiz(
    quiz_id: int,
    request: QuizUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ta),
):
    """
    Updates an existing quiz using AI-powered feedback. Only the original creator can update it.
    """
    db_quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first() # type: ignore
    if not db_quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    if db_quiz.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only update quizzes you have created.")

    # Update quiz content using the AI service
    updated_questions = await quiz_service.update_quiz(
        quiz_data=db_quiz.questions,
        feedback=request.feedback,
    )

    if "error" in updated_questions:
        raise HTTPException(status_code=500, detail=f"AI service error: {updated_questions.get('error')}")

    db_quiz.questions = updated_questions
    db.commit()
    db.refresh(db_quiz)
    return db_quiz


@router.get("/", response_model=List[QuizResponse], summary="List all quizzes")
def get_all_quizzes(
    search: Optional[str] = Query(None, description="Search quizzes by title."),
    course_id: Optional[int] = Query(None, description="Filter quizzes by course ID."),
    db: Session = Depends(get_db),
    _: User = Depends(require_authenticated),
):
    """
    Retrieves a list of all available quizzes, with optional search and filtering.
    """
    query = db.query(Quiz) # type: ignore
    if search:
        query = query.filter(Quiz.title.ilike(f"%{search}%")) # type: ignore
    if course_id:
        query = query.filter(Quiz.course_id == course_id) # type: ignore
    return query.order_by(Quiz.created_at.desc()).all() # type: ignore


@router.get("/{quiz_id}", response_model=QuizResponse, summary="Get a single quiz")
def get_quiz(quiz_id: int, db: Session = Depends(get_db), _: User = Depends(require_authenticated)):
    db_quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first() # type: ignore
    if not db_quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return db_quiz


@router.post(
    "/{quiz_id}/attempt",
    response_model=QuizAttemptResponse,
    summary="Submit an attempt for a quiz",
)
def submit_quiz_attempt(
    quiz_id: int,
    attempt_in: QuizAttemptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """
    Allows a user to submit their answers for a quiz. The score is calculated and stored.
    """
    db_quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first() # type: ignore
    if not db_quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Check if user has already attempted this quiz (optional, can be enabled)
    # existing_attempt = db.query(QuizAttempt).filter_by(quiz_id=quiz_id, user_id=current_user.id).first()
    # if existing_attempt:
    #     raise HTTPException(status_code=400, detail="You have already attempted this quiz.")

    # Calculate score
    score_result = quiz_db_service.calculate_score(db_quiz, attempt_in.answers)

    # Save the attempt
    db_attempt = quiz_db_service.create_attempt(
        db=db,
        quiz=db_quiz,
        user_id=current_user.id,
        score=score_result["score"],
        total_marks=score_result["total_marks"],
        answers=[ans.model_dump() for ans in attempt_in.answers],
    )

    return db_attempt


@router.post(
    "/{quiz_id}/publish",
    response_model=QuizResponse,
    summary="Publish a quiz (Creator only, manual review mode)",
)
def publish_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ta),
):
    """
    Publishes a quiz with manual review mode. Only the creator can publish.
    Auto-published quizzes are already published at generation time.
    """
    db_quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first() # type: ignore
    if not db_quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    if db_quiz.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only publish quizzes you have created.")
    
    db_quiz.is_published = True
    db.commit()
    db.refresh(db_quiz)
    return db_quiz


@router.post(
    "/{quiz_id}/unpublish",
    response_model=QuizResponse,
    summary="Unpublish a quiz (Creator only)",
)
def unpublish_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ta),
):
    """
    Unpublishes a quiz. Only the creator can unpublish.
    """
    db_quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first() # type: ignore
    if not db_quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    if db_quiz.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only unpublish quizzes you have created.")
    
    db_quiz.is_published = False
    db.commit()
    db.refresh(db_quiz)
    return db_quiz


@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a quiz (Creator only)")
def delete_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ta),
):
    db_quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first() # type: ignore
    if not db_quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if db_quiz.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete quizzes you have created.")

    db.delete(db_quiz)
    db.commit()
    return