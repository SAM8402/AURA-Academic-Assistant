"""
Services package for business logic.

Organized into domain-specific subpackages:
- chatbot/  : Chatbot service implementations
- quiz/     : Quiz generation and database services
- slides/   : Slide deck generation, charts, export services
- doubts/   : Doubt summarization and export services
- video/    : Video summary services
- rag/      : RAG pipeline (embedding, ingest, search, chat)
"""

from .chatbot.base_service import ChatOrchestrator
from .quiz.generator_service import QuizService
from .slides.base_service import SlidesService, SlideTheme

__all__ = ["ChatOrchestrator", "QuizService", "SlidesService", "SlideTheme"]

