# quiz generation service 
# agents that generate quizzes based on given topic, 

import json
import logging
from typing import List, Dict, Any, Literal

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import PromptTemplate
    from pydantic import BaseModel, Field
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # Define fallback types
    BaseModel = object
    # Create a fallback Field that accepts any arguments but does nothing
    def Field(*args, **kwargs):
        return None
    ChatGoogleGenerativeAI = None # type: ignore
    JsonOutputParser = None
    PromptTemplate = None

from config.settings import settings

logger = logging.getLogger(__name__)

# ============================================================================
# Pydantic Models for Structured Output
# ============================================================================

class QuizQuestion(BaseModel):
    """Defines the structure for a single quiz question."""
    question_text: str = Field(description="The text of the question.")
    question_type: Literal["mcq", "msq", "boolean"] = Field(description="Type of the question: Multiple Choice (mcq), Multiple Select (msq), or True/False (boolean).")
    options: List[str] = Field(description="A list of possible answers. For boolean, should be ['True', 'False'].")
    correct_answers: List[str] = Field(description="A list containing the correct answer(s).")
    explanation: str = Field(description="A brief explanation for the correct answer.")
    marks: int = Field(description="Marks allocated for this question.")

class Quiz(BaseModel):
    """Defines the structure for the entire quiz."""
    questions: List[QuizQuestion] = Field(description="A list of quiz questions.")


# ============================================================================
# Quiz Generation Service
# ============================================================================

class QuizService:
    """
    A service to generate and update quizzes using LangChain and Google Gemini.
    """

    def __init__(self):
        """Initialize the Quiz Generation Service."""
        self.llm = None
        self.parser = None

        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain or related libraries not installed. Quiz generation will not work.")
            logger.warning("Install with: pip install langchain langchain-google-genai")
            return

        if not settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY not found in .env file. Quiz generation will be disabled.")
            return

        try:
            self.parser = JsonOutputParser(pydantic_object=Quiz)
            self.llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.6,  # Slightly creative but still factual for quizzes
            )
            logger.info(f"[OK] QuizService initialized with Gemini model: {settings.GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize Gemini LLM for QuizService: {e}")

    async def generate_quiz(
        self,
        course_name: str,
        topics: List[str],
        difficulty: str,
        marks_per_question: int,
        num_questions: int
    ) -> Dict[str, Any]:
        """
        Generates a quiz based on the provided parameters.

        Args:
            course_name: The name of the course.
            topics: A list of topics to cover in the quiz.
            difficulty: The difficulty level of the quiz (e.g., "Easy", "Medium", "Hard").
            marks_per_question: The marks to be allocated for each question.
            num_questions: The total number of questions to generate.

        Returns:
            A dictionary representing the generated quiz, or an error dictionary.
        """
        if not self.llm:
            return {"error": "Quiz service is not configured due to missing dependencies or API key."}

        prompt_template = """
        You are an expert quiz creator for university-level courses.
        Your task is to generate a quiz for the course "{course_name}".

        **Quiz Requirements:**
        - **Topics to cover:** {topics}
        - **Difficulty Level:** {difficulty}
        - **Total Number of Questions:** {num_questions}
        - **Marks per Question:** {marks_per_question}
        - **Question Types:** Generate a mix of Multiple Choice (mcq), Multiple Select (msq), and True/False (boolean) questions.

        **Instructions:**
        1.  Ensure the questions accurately reflect the specified topics and difficulty.
        2.  For 'mcq', provide 4 options and ensure `correct_answers` has only one item.
        3.  For 'msq', provide 4-6 options and ensure `correct_answers` has two or more items.
        4.  For 'boolean', the `options` list must be ["True", "False"].
        5.  Provide a clear and concise `explanation` for each question.

        **Output Format:**
        You MUST provide the output as a single, valid JSON object that strictly follows this format. Do not include any other text or markdown formatting.
        {format_instructions}
        """

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["course_name", "topics", "difficulty", "num_questions", "marks_per_question"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )

        chain = prompt | self.llm | self.parser

        try:
            logger.info(f"Generating quiz for course: {course_name}, topics: {topics}")
            quiz_data = await chain.ainvoke({
                "course_name": course_name,
                "topics": ", ".join(topics),
                "difficulty": difficulty,
                "num_questions": num_questions,
                "marks_per_question": marks_per_question,
            })
            logger.info("Successfully generated quiz.")
            return quiz_data
        except Exception as e:
            logger.error("Failed to generate or parse quiz", exc_info=True)
            return {"error": "An error occurred while generating the quiz. Please try again later."}


    async def update_quiz(self, quiz_data: Dict[str, Any], feedback: str) -> Dict[str, Any]:
        """
        Updates an existing quiz based on user feedback.

        Args:
            quiz_data: The original quiz object as a dictionary.
            feedback: Text feedback describing the desired changes.

        Returns:
            A dictionary representing the updated quiz, or an error dictionary.
        """
        if not self.llm:
            return {"error": "Quiz service is not configured due to missing dependencies or API key."}

        prompt_template = """
        You are an expert quiz editor. Your task is to update an existing quiz based on user feedback.

        **Original Quiz (in JSON format):**
        {original_quiz}

        **User Feedback for Changes:**
        "{feedback}"

        **Instructions:**
        1.  Read the original quiz and the user feedback carefully.
        2.  Modify the quiz according to the feedback. This could involve changing question text, options, correct answers, explanations, adding new questions, or removing existing ones.
        3.  Ensure the final output is a complete quiz that incorporates the requested changes.
        4.  Maintain the structure and types for all questions (mcq, msq, boolean).
        5.  The final output MUST be a single, valid JSON object that strictly follows the format below. Do not include any other text or markdown formatting.

        **Output Format:**
        {format_instructions}
        """

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["original_quiz", "feedback"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )

        chain = prompt | self.llm | self.parser

        try:
            logger.info(f"Updating quiz with feedback: {feedback}")

            # Serialize the original quiz data to a JSON string for the prompt
            original_quiz_json = json.dumps(quiz_data, indent=2)

            updated_quiz_data = await chain.ainvoke({
                "original_quiz": original_quiz_json,
                "feedback": feedback,
            })
            logger.info("Successfully updated quiz.")
            return updated_quiz_data
        except Exception as e:
            logger.error("Failed to update or parse quiz", exc_info=True)
            return {"error": "An error occurred while updating the quiz. Please try again later."}


# global instance 
quiz_service = QuizService()