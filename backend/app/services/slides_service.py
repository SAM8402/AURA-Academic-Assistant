# slide generation service 
# agents that generate slide based on given instructions 

import logging
from typing import Dict, Any
from enum import Enum

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import PromptTemplate
    from pydantic import BaseModel, Field
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # Define fallback types
    BaseModel = object
    Field = object
    ChatGoogleGenerativeAI = None # type: ignore
    StrOutputParser = None
    PromptTemplate = None

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Schemas for Slide Generation
# ============================================================================

class SlideTheme(str, Enum):
    """Enumeration for the available slide themes."""
    MINIMAL = "minimal"
    CORPORATE = "corporate"
    DARK = "dark"
    STORYTELLING = "storytelling"


# ============================================================================
# Slide Generation Service
# ============================================================================

class SlidesService:
    """
    A service to generate presentation slides in Markdown format using an LLM.
    """

    def __init__(self):
        """Initialize the Slides Generation Service."""
        self.llm = None
        self.parser = None

        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain not installed. Slide generation will be disabled.")
            return

        self.parser = StrOutputParser()

        if not settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY not found in .env file. Slide generation will be disabled.")
            return

        try:
            self.llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                api_key=settings.GOOGLE_API_KEY,
                temperature=0.7  # A bit more creative for slide content
            )
            logger.info(f"[OK] SlidesService initialized with Gemini model: {settings.GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize Gemini LLM for SlidesService: {e}")

    async def generate_slides(
        self,
        instructions: str,
        theme: SlideTheme
    ) -> str:
        """
        Generates presentation slides as a Markdown string.

        Args:
            instructions: User-provided text describing the desired slide content.
            theme: The visual and narrative theme for the slides.

        Returns:
            A single string containing Reveal.js-compatible Markdown, or an error message.
        """
        if not self.llm:
            return "## Error\n\nSlide service is not configured due to missing dependencies or API key."

        prompt_template = """
        You are an expert presentation designer. Your task is to create a slide deck in Reveal.js-compatible Markdown format based on the user's instructions and a selected theme.

        **Theme:** {theme}
        - **minimal:** Use clean headings, simple bullet points, and lots of white space. Avoid jargon.
        - **corporate:** Use professional language, structured lists, and a formal tone. Focus on data and key takeaways.
        - **dark:** Use high-contrast text. Suitable for technical presentations with code snippets.
        - **storytelling:** Use a narrative structure. Each slide builds on the last. Use rhetorical questions and engaging language.

        **User Instructions:**
        "{instructions}"

        **Output Requirements:**
        1.  **Format:** Raw Markdown only. DO NOT wrap the output in code fences (like ```markdown).
        2.  **Slide Separator:** Use three hyphens (`---`) on a new line to separate individual slides.
        3.  **Hierarchy:** Use `#` for the main title slide, `##` for subsequent slide titles, and `*` for bullet points.
        4.  **Conciseness:** Keep the text on each slide brief and to the point. Focus on keywords and short phrases.
        5.  **Adherence:** Strictly follow the user's instructions and apply the chosen theme's style.
        """

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["instructions", "theme"],
        )

        chain = prompt | self.llm | self.parser

        try:
            logger.info(f"Generating slides for theme '{theme.value}' with instructions: '{instructions[:50]}...'")
            slides_markdown = await chain.ainvoke({
                "instructions": instructions,
                "theme": theme.value,
            })
            logger.info("Successfully generated slides markdown.")
            return slides_markdown.strip()
        except Exception as e:
            logger.error(f"Failed to generate slides: {e}")
            return f"## Error\n\nAn error occurred while generating the slides: {str(e)}"
        