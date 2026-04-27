"""
Service for handling quiz database operations and attempt scoring.
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.schemas.quiz_schema import Answer


class QuizDBService:
    def calculate_score(self, quiz: Quiz, submitted_answers: List[Answer]) -> Dict[str, int]:
        """
        Calculates the score for a quiz attempt.

        Args:
            quiz: The Quiz object from the database.
            submitted_answers: A list of answers submitted by the user.

        Returns:
            A dictionary containing the calculated score and total possible marks.
        """
        score = 0
        total_marks = 0
        quiz_questions = quiz.questions.get("questions", [])

        # Create a map of question index to submitted answer for easy lookup
        answers_map = {ans.question_index: ans.selected_options for ans in submitted_answers}

        for i, question in enumerate(quiz_questions):
            question_marks = question.get("marks", 0)
            total_marks += question_marks

            # Check if the user answered this question
            if i in answers_map:
                user_selection = set(answers_map[i])
                correct_selection = set(question.get("correct_answers", []))

                # For a correct answer, the sets must be identical
                if user_selection == correct_selection:
                    score += question_marks

        return {"score": score, "total_marks": total_marks}

    def create_attempt(
        self, db: Session, quiz: Quiz, user_id: int, score: int, total_marks: int, answers: List[Dict]
    ) -> QuizAttempt:
        """Creates and saves a new quiz attempt record."""
        db_attempt = QuizAttempt(
            quiz_id=quiz.id, user_id=user_id, score=score, total_marks=total_marks, submitted_answers=answers
        )
        db.add(db_attempt)
        db.commit()
        db.refresh(db_attempt)
        return db_attempt

quiz_db_service = QuizDBService()