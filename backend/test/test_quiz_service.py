"""
Pytest integration tests for the QuizService.

These tests verify the functionality of generating and updating quizzes
by making live calls to the Google Gemini API.
"""

import pytest
import os
import json
from typing import Dict, Any

# Add the project's root directory (`backend`) to the Python path
# This is often needed for pytest to find the 'app' module
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.quiz.generator_service import QuizService

# --- Test Configuration ---

# Mark all tests in this file as 'integration' and 'quiz'.
# The 'quiz' marker is a custom marker you can add to pytest.ini if you wish.
# These tests will be skipped if the GOOGLE_API_KEY is not set, which is
# crucial for environments like CI/CD where secrets may not be available.
pytestmark = [
    pytest.mark.integration,
    pytest.mark.quiz,
    pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY not set in environment")
]


# --- Fixtures ---

@pytest.fixture(scope="module")
def quiz_service() -> QuizService:
    """
    Provides a singleton instance of the QuizService for the test module.
    This is efficient as the LLM is initialized only once per test session.
    """
    service = QuizService()
    if not service.llm:
        pytest.xfail("QuizService LLM failed to initialize. Check GOOGLE_API_KEY and dependencies.")
    return service

@pytest.fixture
def generation_params() -> Dict[str, Any]:
    """Provides standard parameters for generating a quiz."""
    return {
        "course_name": "Introduction to Python Programming",
        "topics": ["Data Structures (Lists, Dictionaries)", "Control Flow (if/else, for loops)"],
        "difficulty": "Easy",
        "marks_per_question": 5,
        "num_questions": 2,  # Using 2 to keep tests fast
    }


@pytest.fixture
def generation_update_quiz_params() -> Dict[str, Any]:
    """Provides standard parameters for generating a quiz."""
    return {
        "course_name": "Introduction to Quant Computing",
        "topics": ["Cubits", "Quantum entanglement"],
        "difficulty": "Easy",
        "marks_per_question": 5,
        "num_questions": 2,  # Using 2 to keep tests fast
    }


# --- Test Class for QuizService ---

@pytest.mark.asyncio
class TestQuizService:
    """Groups tests for the QuizService."""

    async def test_generate_quiz_success(self, quiz_service: QuizService, generation_params: Dict[str, Any]):
        """
        Tests successful quiz generation.
        Verifies the structure and content of the generated quiz.
        """
        print("\n[TEST] Generating a new quiz...")
        generated_quiz = await quiz_service.generate_quiz(**generation_params)

        # Assertions
        assert isinstance(generated_quiz, dict)
        assert "error" not in generated_quiz, f"API returned an error: {generated_quiz.get('error')}"
        assert "questions" in generated_quiz
        assert isinstance(generated_quiz["questions"], list)
        assert len(generated_quiz["questions"]) == generation_params["num_questions"]

        first_question = generated_quiz["questions"][0]
        assert "question_text" in first_question
        assert "question_type" in first_question
        assert "options" in first_question
        assert "correct_answers" in first_question
        assert first_question["marks"] == generation_params["marks_per_question"]

        print("[SUCCESS] Quiz generated and validated.")
        print(json.dumps(generated_quiz, indent=2))

    async def test_update_quiz_success(self, quiz_service: QuizService, generation_update_quiz_params: Dict[str, Any]):
        """
        Tests successful quiz update based on feedback.
        First generates a quiz, then provides feedback to update it.
        """
        print("\n[TEST] Generating initial quiz for update test...")
        initial_quiz_obj = await quiz_service.generate_quiz(**generation_update_quiz_params)
        
        # Ensure the result is not None and convert from Pydantic model to dict
        assert initial_quiz_obj is not None, "Quiz generation returned None."
        initial_quiz = initial_quiz_obj.dict() if hasattr(initial_quiz_obj, 'dict') else initial_quiz_obj
        assert "error" not in initial_quiz, f"Failed to generate initial quiz for update test: {initial_quiz.get('error')}"

        feedback = (
            "Good start. Now, please add one more 'boolean' question about list indexing."
        )

        print(f"\n[TEST] Updating quiz with feedback: '{feedback}'")
        updated_quiz = await quiz_service.update_quiz(
            quiz_data=initial_quiz, # Pass the dictionary
            feedback=feedback
        )

        # Ensure the result is not None and convert from Pydantic model to dict
        assert updated_quiz is not None, "Quiz update returned None."
        updated_quiz_dict = updated_quiz.dict() if hasattr(updated_quiz, 'dict') else updated_quiz

        # --- Basic Assertions ---
        assert isinstance(updated_quiz_dict, dict)
        assert "error" not in updated_quiz, f"API returned an error during update: {updated_quiz.get('error')}"
        assert "questions" in updated_quiz

        initial_questions = initial_quiz.get("questions", [])
        updated_questions = updated_quiz.get("questions", [])

        # --- Assert Question Count ---
        # The number of questions should now be one more than the original.
        assert len(updated_questions) == len(initial_questions) + 1, \
            "The number of questions did not increase by one."

        # --- Assert New Question Content ---
        initial_question_texts = {q["question_text"] for q in initial_questions}
        
        # Find the newly added question by finding one that wasn't in the initial set.
        newly_added_questions = [q for q in updated_questions if q["question_text"] not in initial_question_texts]
        
        assert len(newly_added_questions) == 1, "Exactly one new question should have been added."
        
        added_question = newly_added_questions[0]
        assert added_question["question_type"] == "boolean", "The new question is not of type 'boolean' as requested."
        assert "list" in added_question["question_text"].lower() or "indexing" in added_question["question_text"].lower(), \
            "The new question content does not seem to be about 'list indexing'."

        print("[SUCCESS] Quiz updated and validated.")
        print(json.dumps(updated_quiz, indent=2))