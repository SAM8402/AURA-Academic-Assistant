"""
Async Chatbot Service using LangChain and Google Gemini.
"""

import logging
import uuid
from typing import Dict, Optional, AsyncIterator, Any, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.memory import ConversationBufferMemory
    from langchain.chains import ConversationChain

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.memory import ConversationBufferMemory
    from langchain.chains import ConversationChain
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    ChatGoogleGenerativeAI = None  # type: ignore
    ConversationBufferMemory = None  # type: ignore
    ConversationChain = None  # type: ignore

from app.core.config import settings
from app.schemas.chatbot_schema import ChatMode

logger = logging.getLogger(__name__)


class ChatbotService:
    """Async chatbot service with streaming support."""

    def __init__(self):
        """Initialize Gemini LLM."""
        self.conversations: Dict[str, Any] = {}
        self.llm = None

        if not LANGCHAIN_AVAILABLE:
            logger.error("langchain or langchain-google-genai is not installed. Run: pip install langchain langchain-google-genai")
            return

        if not settings.GOOGLE_API_KEY:
            logger.error("GOOGLE_API_KEY is not configured. Add it to the .env file.")
            return

        try:
            self.llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=settings.GEMINI_TEMPERATURE,
                max_output_tokens=settings.GEMINI_MAX_TOKENS,
            )
            logger.info("Gemini LLM initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Gemini LLM: %s", e)

    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        mode: ChatMode = ChatMode.GENERAL
    ) -> tuple[str, str]:
        """
        Generate chat response.

        Args:
            message: User's message
            conversation_id: Optional conversation ID for history
            mode: Chat mode (academic, general, etc.)

        Returns:
            Tuple of (response, conversation_id)
        """
        if not conversation_id:
            conversation_id = f"conv-{uuid.uuid4().hex[:12]}"

        if not self.llm:
            return (
                "Chatbot is not configured. Please ensure GOOGLE_API_KEY is set and dependencies are installed.",
                conversation_id
            )

        try:
            memory = self._get_or_create_memory(conversation_id)
            system_prompt = self._get_system_prompt(mode)

            conversation = ConversationChain(
                llm=self.llm,
                memory=memory,
                verbose=False
            )

            response = await conversation.apredict(input=message)

            return response, conversation_id

        except Exception as e:
            logger.error("Chat error for conversation %s: %s", conversation_id, e, exc_info=True)
            return "I apologize, but something went wrong while processing your request. Please try again.", conversation_id

    async def chat_stream(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        mode: ChatMode = ChatMode.GENERAL
    ) -> AsyncIterator[str]:
        """
        Generate streaming chat response.

        Args:
            message: User's message
            conversation_id: Optional conversation ID
            mode: Chat mode

        Yields:
            Response chunks as they're generated
        """
        if not self.llm:
            yield "Chatbot is not configured. Please ensure GOOGLE_API_KEY is set and dependencies are installed."
            return

        conv_id = conversation_id or f"conv-{uuid.uuid4().hex[:12]}"

        try:
            memory = self._get_or_create_memory(conv_id)

            memory.chat_memory.add_user_message(message)

            full_response = ""
            async for chunk in self.llm.astream(message):
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                full_response += content
                yield content

            memory.chat_memory.add_ai_message(full_response)

        except Exception as e:
            logger.error("Streaming chat error for conversation %s: %s", conv_id, e, exc_info=True)
            yield "I apologize, but something went wrong while processing your request. Please try again."

    def _get_or_create_memory(self, conversation_id: str) -> Any:
        """Get or create conversation memory."""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = ConversationBufferMemory(
                return_messages=True,
                memory_key="history"
            )
        return self.conversations[conversation_id]

    def _get_system_prompt(self, mode: ChatMode) -> str:
        """Get system prompt based on mode."""
        prompts = {
            ChatMode.ACADEMIC: (
                "You are AURA, an AI academic assistant specializing in computer science, software engineering, "
                "and related technical disciplines.\n\n"
                "Guidelines:\n"
                "- Provide thorough, well-structured explanations using clear language.\n"
                "- Use concrete examples, analogies, and code snippets when relevant.\n"
                "- Cite concepts, theories, or documentation where appropriate.\n"
                "- Break complex topics into smaller, digestible sections with headings.\n"
                "- When a question is ambiguous, state your interpretation before answering.\n"
                "- Encourage critical thinking — do not simply give answers; explain the reasoning behind them."
            ),
            ChatMode.DOUBT_CLARIFICATION: (
                "You are AURA, a patient and supportive AI tutor focused on helping students understand difficult concepts.\n\n"
                "Guidelines:\n"
                "- Start by restating the student's question to confirm understanding.\n"
                "- Ask one or two clarifying questions if the doubt is vague or incomplete.\n"
                "- Provide step-by-step explanations, guiding the student toward the answer rather than revealing it outright.\n"
                "- Highlight common misconceptions related to the topic.\n"
                "- Summarize the key takeaway at the end of your response.\n"
                "- Keep the tone encouraging and non-judgmental — mistakes are part of learning."
            ),
            ChatMode.STUDY_HELP: (
                "You are AURA, an AI study coach dedicated to helping students learn more effectively.\n\n"
                "Guidelines:\n"
                "- Offer practical, actionable study strategies (e.g., spaced repetition, active recall, Pomodoro technique).\n"
                "- Help students build realistic study schedules based on their goals and available time.\n"
                "- Recommend resources such as textbooks, online courses, documentation, or practice platforms.\n"
                "- Suggest techniques for managing exam stress and maintaining motivation.\n"
                "- Adapt your advice to the student's level (beginner, intermediate, advanced).\n"
                "- Be concise and action-oriented — students should leave with a clear next step."
            ),
            ChatMode.GENERAL: (
                "You are AURA, a friendly and knowledgeable AI teaching assistant.\n\n"
                "Guidelines:\n"
                "- Be helpful, accurate, and concise in your responses.\n"
                "- Adapt your tone to be professional yet approachable.\n"
                "- If you do not know something, say so honestly rather than guessing.\n"
                "- When relevant, suggest follow-up questions or related topics the user might explore.\n"
                "- Use formatting (bullet points, numbered lists, code blocks) to improve readability.\n"
                "- Maintain a positive and encouraging demeanor in all interactions."
            ),
        }
        return prompts.get(mode, prompts[ChatMode.GENERAL])

    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear conversation history."""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False

    def get_conversation_history(self, conversation_id: str) -> list:
        """Get conversation history."""
        if conversation_id in self.conversations:
            memory = self.conversations[conversation_id]
            return memory.chat_memory.messages
        return []


# Global chatbot instance
chatbot_service = ChatbotService()
