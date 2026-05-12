"""
AURA Chatbot Service — Core Module (Agentic Architecture).

The chatbot uses Google Gemini's function calling to autonomously decide
which tools to invoke (knowledge base, query search, web search) based on
the student's question, rather than following a hardcoded retrieval cascade.

Contains:
- Constants & configuration
- Prompt builder (system prompts, mode instructions)
- LLMProvider (Google Genai SDK wrapper with function calling)
- ChatOrchestrator (agentic pipeline coordinator)

Supporting infrastructure (MemoryManager, ToolExecutor) lives in
hybrid_service.py.
"""

import asyncio
import hashlib
import os
import logging
import re
import time
import uuid
from collections import OrderedDict
from datetime import datetime, UTC
from typing import Any, AsyncIterator, Dict, List, Optional

from sqlalchemy.orm import Session

from config.settings import settings
from app.models.user import User
from app.schemas.chatbot_schema import ChatMode

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Memory
MAX_SESSION_TURNS = 10
MAX_SUMMARY_LENGTH = 500
MAX_PERSISTENT_SESSIONS = 5

# Chatbot-specific model config (independent of settings.py)
# NOTE: Model selection now uses _build_rag_llm() with multi-model fallback
# No default model needed — fallback chain handles model selection
CHATBOT_TEMPERATURE = 0.7
CHATBOT_MAX_TOKENS = 1024

# Retrieval (used by tools) — lower threshold for broader document matching
RAG_TOP_K = 8
RAG_SIMILARITY_THRESHOLD = 0.2
WEB_SEARCH_MAX_RESULTS = 3
DB_QUERY_MATCH_LIMIT = 3
KEYWORD_MIN_LENGTH = 4

# Agentic
MAX_TOOL_ROUNDS = 3  # Max function-calling iterations per request

# Input guards
MAX_MESSAGE_LENGTH = 4000  # Chars — prevents excessively long prompts
MIN_MESSAGE_LENGTH = 2     # Minimum meaningful input

# Response cache (LRU)
RESPONSE_CACHE_SIZE = 128  # Max cached responses
CACHE_TTL_SECONDS = 300    # 5 minutes

# Priority labels (used in response metadata)
PRIORITY_DATABASE_QUERIES = "database_queries"
PRIORITY_QUERY_LIST = "query_list"
PRIORITY_KNOWLEDGE_BASE = "knowledge_base"
PRIORITY_WEB_SEARCH = "web_search"
PRIORITY_GENERAL_KNOWLEDGE = "ai_general_knowledge"
PRIORITY_AGENTIC = "agentic"
PRIORITY_ERROR = "error"


# =============================================================================
# Input Sanitization & Validation
# =============================================================================

# Patterns that indicate prompt injection attempts
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?above",
    r"disregard\s+(all\s+)?previous",
    r"you\s+are\s+now\s+(?:a|an)\s+(?!student)",
    r"system\s*:\s*",
    r"\[INST\]",
    r"<\|im_start\|>",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def sanitize_message(message: str) -> str:
    """
    Sanitize user input: trim, enforce length, detect injection attempts.
    Returns the cleaned message or raises ValueError.
    """
    if not message or not message.strip():
        raise ValueError("Message cannot be empty")

    message = message.strip()

    if len(message) < MIN_MESSAGE_LENGTH:
        raise ValueError("Message is too short. Please provide a meaningful question.")

    if len(message) > MAX_MESSAGE_LENGTH:
        logger.warning("Message truncated from %d to %d chars", len(message), MAX_MESSAGE_LENGTH)
        message = message[:MAX_MESSAGE_LENGTH]

    # Check for obvious prompt injection
    if _INJECTION_RE.search(message):
        logger.warning("Potential prompt injection detected and blocked")
        raise ValueError("Your message could not be processed. Please rephrase your question.")

    return message


# =============================================================================
# Simple LRU Response Cache
# =============================================================================

class _ResponseCache:
    """Thread-safe LRU cache with TTL for identical queries."""

    def __init__(self, maxsize: int = RESPONSE_CACHE_SIZE, ttl: int = CACHE_TTL_SECONDS):
        self._cache: OrderedDict[str, tuple] = OrderedDict()  # key → (response, timestamp)
        self._maxsize = maxsize
        self._ttl = ttl

    def _key(self, user_id: int, message: str, mode: str) -> str:
        raw = f"{user_id}:{mode}:{message.lower().strip()}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, user_id: int, message: str, mode: str) -> Optional[Dict[str, Any]]:
        key = self._key(user_id, message, mode)
        if key not in self._cache:
            return None
        response, ts = self._cache[key]
        if time.time() - ts > self._ttl:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return response

    def put(self, user_id: int, message: str, mode: str, response: Dict[str, Any]) -> None:
        key = self._key(user_id, message, mode)
        self._cache[key] = (response, time.time())
        self._cache.move_to_end(key)
        while len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)


_response_cache = _ResponseCache()


# =============================================================================
# Prompt Builder
# =============================================================================

SYSTEM_PROMPT = """You are AURA (Academic Unified Response Assistant), an AI teaching assistant \
for a university learning management system.

Your identity:
- You are knowledgeable, patient, and encouraging
- You adapt explanation depth to the student's level
- You use examples, analogies, and structured formatting (markdown)
- You admit uncertainty honestly rather than guessing
- You keep responses focused and well-organized

TOOL USAGE — CRITICAL INSTRUCTION:
- For ANY academic or course-related question → ALWAYS call search_knowledge_base first
- The knowledge base contains uploaded course documents — your answer MUST be grounded in these
- If search_knowledge_base returns results, you MUST base your answer on them
- Only after search_knowledge_base returns NO results should you try other tools or your own knowledge
- When the student references queries/doubts → use search_student_queries
- For course enrollment, quizzes, scores, or resources → use get_course_info
- For current events or information you're unsure about → use search_web
- For simple greetings, follow-ups, or general knowledge → answer directly without tools
- You may call multiple tools if the question spans several topics

CITATION AND RESPONSE GUIDELINES:
- When citing knowledge base content, use the EXACT source title as provided (e.g. "According to *Ml Intro*..."). Do NOT rename or paraphrase the title.
- If you used the knowledge base, start your answer with a reference to the exact source document
- When referencing a student query, mention its title and status
- Structure longer responses with markdown headings (##), bullet points, and code blocks
- End with a follow-up suggestion when appropriate: "Would you like me to explain X further?"
- If your answer is based entirely on your training data (no tools used), say so clearly"""


MODE_INSTRUCTIONS: Dict[ChatMode, str] = {
    ChatMode.ACADEMIC: (
        "Focus on educational depth. Provide thorough, well-structured explanations "
        "using clear language. Use concrete examples, analogies, and code snippets "
        "when relevant. Break complex topics into digestible sections with headings. "
        "Cite concepts, theories, or documentation where appropriate. Encourage "
        "critical thinking — explain the reasoning, not just the answer."
    ),
    ChatMode.DOUBT_CLARIFICATION: (
        "Start by restating the student's doubt to confirm understanding. "
        "Ask one or two clarifying questions if the doubt is vague. "
        "Provide step-by-step explanations, guiding the student toward the answer "
        "rather than revealing it outright. Highlight common misconceptions. "
        "Summarize the key takeaway at the end. Keep the tone encouraging "
        "and non-judgmental — mistakes are part of learning."
    ),
    ChatMode.STUDY_HELP: (
        "Be concise and action-oriented. Offer practical study strategies "
        "(spaced repetition, active recall, Pomodoro technique). Help build "
        "realistic study schedules. Recommend specific resources such as "
        "textbooks, online courses, or practice platforms. Suggest techniques "
        "for managing exam stress. Adapt advice to the student's level. "
        "Students should leave with a clear next step."
    ),
    ChatMode.GENERAL: (
        "Be helpful, accurate, and concise. Adapt your tone to be professional "
        "yet approachable. If you do not know something, say so honestly. "
        "Suggest follow-up questions or related topics when relevant. "
        "Use formatting (bullet points, numbered lists, code blocks) to "
        "improve readability. Maintain a positive and encouraging demeanor."
    ),
}


def get_system_prompt(mode: ChatMode = ChatMode.GENERAL) -> str:
    """Return the full system prompt including mode-specific instructions."""
    mode_instruction = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS[ChatMode.GENERAL])
    return f"{SYSTEM_PROMPT}\n\nMode: {mode.value}\n{mode_instruction}"


def rewrite_query_for_rag(message: str) -> str:
    """
    Lightly expand the user message into a search-friendly form.
    Strips filler words and adds implicit academic context.
    """
    # Remove common filler prefixes
    fillers = [
        r"^(hey|hi|hello|please|can you|could you|i want to know|tell me|explain|what is|what are)\s+",
    ]
    cleaned = message
    for pattern in fillers:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned or message


def build_agentic_prompt(
    user_message: str,
    *,
    user_context: Optional[Dict[str, Any]] = None,
    previous_summaries: Optional[List[str]] = None,
) -> str:
    """
    Compose the user prompt for the agentic pipeline.

    Injects user identity, enrolled courses, and persistent memory.
    The agent fetches retrieval context itself via tool calls.
    """
    sections = []

    # User identity + academic profile
    if user_context:
        name = user_context.get("full_name", "Student")
        role = user_context.get("role", "student")
        sections.append(f"Student: {name} (Role: {role})")
        if user_context.get("is_new_user"):
            sections.append("Note: This is a new student — provide extra guidance.")

        # Enrolled courses (enriched context)
        courses = user_context.get("enrolled_courses")
        if courses:
            course_list = ", ".join(courses[:5])
            sections.append(f"Enrolled in: {course_list}")

        # Recent quiz performance
        quiz_avg = user_context.get("quiz_avg_score")
        if quiz_avg is not None:
            sections.append(f"Recent quiz average: {quiz_avg}%")

        recent = user_context.get("recent_topics")
        if recent:
            sections.append(f"Recent topics: {', '.join(recent[:3])}")

    # Past conversation summaries (persistent memory)
    if previous_summaries:
        header = f"Previous sessions ({len(previous_summaries)}):"
        summaries = "\n".join(f"  - {s}" for s in previous_summaries[:5])
        sections.append(f"{header}\n{summaries}")

    # The user's actual question
    sections.append(user_message)

    return "\n\n".join(sections)


# =============================================================================
# LLM Provider
# =============================================================================

try:
    from google import genai
    from google.genai import types
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False
    genai = None
    types = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    _LANGCHAIN_AVAILABLE = True
except ImportError:
    _LANGCHAIN_AVAILABLE = False

from app.services.rag.llm_builder import build_robust_llm

def _build_rag_llm():
    """
    Build RAG LLM with multi-model fallback chain.
    """
    llm, models = build_robust_llm(temperature=0.1, max_retries=1)
    if not llm:
        raise ValueError("No LLM instances created. Check GOOGLE_API_KEY configuration.")
        
    logger.info(f"[OK] RAG Chatbot initialized with dynamic multi-model fallback: {models[0]} -> {models[1:]}")
    return llm


class LLMProvider:
    """
    Wraps Google Genai SDK + LangChain for chat generation.

    Maintains a flat list of (model, api_key) combos built from
    CHATBOT_MODELS x all API keys. On 429 / 503 / RESOURCE_EXHAUSTED,
    automatically rotates to the next combo so the user never sees
    raw API errors.

    - generate()            — Uses _build_rag_llm() with multi-model fallback
    - generate_with_tools() — Uses google.genai SDK (required for function calling)
    - generate_stream()     — Uses google.genai SDK for streaming
    """

    # Models to cycle through (order = priority)
    # Ordered by performance: fastest → reliable → stable → fallback
    @property
    def CHATBOT_MODELS(self):
        return [m.strip() for m in settings.LLM_FALLBACK_CHAIN.split(",") if m.strip()]

    def __init__(self):
        self.client = None
        self.model = None
        self._available = False
        self._combos: List[tuple] = []   # [(model, key), ...]
        self._combo_idx = 0
        self._init_client()

    def _init_client(self) -> None:
        if not _SDK_AVAILABLE:
            logger.warning("Google Genai SDK not installed. Run: pip install google-genai")
            return

        raw_key = settings.GOOGLE_API_KEY
        if not raw_key or raw_key == "your-google-api-key":
            logger.warning("GOOGLE_API_KEY not configured")
            return

        api_keys = [k.strip() for k in raw_key.split(",") if k.strip()]
        if not api_keys:
            logger.warning("No valid API keys found in GOOGLE_API_KEY")
            return

        # Build flat list: every model × every key
        self._combos = [(m, k) for m in self.CHATBOT_MODELS for k in api_keys]
        self._combo_idx = 0

        # Activate the first combo
        self._activate_combo(0)

    def _activate_combo(self, idx: int) -> bool:
        """Activate (model, key) combo at the given index. Returns success."""
        if not self._combos:
            return False
        self._combo_idx = idx % len(self._combos)
        model, key = self._combos[self._combo_idx]
        try:
            os.environ["GOOGLE_API_KEY"] = key
            self.client = genai.Client(api_key=key)
            self.model = model
            self._available = True
            logger.info("LLM active: model=%s, key=...%s (combo %d/%d)",
                        model, key[-6:], self._combo_idx + 1, len(self._combos))
            return True
        except Exception as e:
            logger.error("Failed to activate combo %d (%s): %s", self._combo_idx, model, e)
            return False

    def _rotate(self) -> bool:
        """Rotate to the next (model, key) combo. Returns True if a new combo was activated."""
        if len(self._combos) <= 1:
            return False
        start = self._combo_idx
        for offset in range(1, len(self._combos)):
            next_idx = (start + offset) % len(self._combos)
            if self._activate_combo(next_idx):
                logger.warning("Rotated to combo %d: model=%s", next_idx, self.model)
                return True
        return False

    @staticmethod
    def _is_exhaustion_error(error: Exception) -> bool:
        """Check if an exception is a rate-limit or model-unavailable error."""
        err = str(error).lower()
        return any(marker in err for marker in [
            "429", "resource_exhausted", "503", "unavailable",
            "quota", "rate limit", "overloaded",
            "404", "not_found", "not found",
        ])

    @property
    def is_available(self) -> bool:
        return self._available and self.client is not None

    # -- Simple generation (no tools) -----------------------------------------

    async def generate(
        self,
        system_prompt: str,
        history: List[dict],
        user_message: str,
    ) -> str:
        """Generate a single response using _build_rag_llm with multi-model fallback."""
        if not _LANGCHAIN_AVAILABLE:
            return "LangChain not installed. Please check dependencies."

        try:
            llm = _build_rag_llm()
            full_prompt = f"{system_prompt}\n\n{user_message}"
            response = llm.invoke(full_prompt)
            return response.content.strip() if hasattr(response, "content") else str(response)

        except Exception as e:
            logger.error("LLM generation failed: %s", e)
            return "I'm sorry, I'm temporarily unable to process your request. Please try again in a moment."

    # -- Agentic generation (with function calling) ---------------------------

    async def generate_with_tools(
        self,
        system_prompt: str,
        history: List[dict],
        user_message: str,
        tool_declarations: list,
        tool_executor,
        _retry_count: int = 0,
    ) -> tuple[str, List[str]]:
        """
        Agentic generation with function calling loop.

        Uses google.genai SDK directly (required for function calling).
        The LLM decides which tools to call. We execute them and feed results
        back until the LLM produces a final text response.

        On exhaustion errors, automatically rotates to the next (model, key) combo.

        Returns: (response_text, list_of_tools_used)
        """
        if not self.is_available:
            return "Chat service is not configured.", []

        tools_used = []

        try:
            # Build tool config
            gemini_tools = [types.Tool(function_declarations=tool_declarations)]

            config = types.GenerateContentConfig(
                temperature=CHATBOT_TEMPERATURE,
                max_output_tokens=CHATBOT_MAX_TOKENS,
                system_instruction=system_prompt,
                tools=gemini_tools,
            )

            # Build initial contents
            contents = list(history)
            contents.append({"role": "user", "parts": [{"text": user_message}]})

            # Agentic loop: LLM calls tools → we execute → feed back → repeat
            for round_num in range(MAX_TOOL_ROUNDS):
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )

                # Extract function calls from response
                response_content = response.candidates[0].content
                function_calls = [
                    part for part in response_content.parts
                    if hasattr(part, "function_call") and part.function_call
                ]

                if not function_calls:
                    # No tool calls — model produced a final text response
                    text = response.text if hasattr(response, "text") else ""
                    return text or "I couldn't generate a response.", tools_used

                logger.info(
                    "Agentic round %d: %d tool call(s) — %s",
                    round_num + 1,
                    len(function_calls),
                    [fc.function_call.name for fc in function_calls],
                )

                # Add model's function call message to conversation
                contents.append(response_content)

                # Execute tools in parallel and build function response parts
                async def _run_tool(part):
                    tool_name = part.function_call.name
                    tool_args = dict(part.function_call.args) if part.function_call.args else {}
                    try:
                        result = await tool_executor.execute(tool_name, tool_args)
                    except Exception as e:
                        logger.error("Tool %s failed: %s", tool_name, e)
                        result = {"error": f"Tool execution failed: {str(e)}"}
                    return tool_name, result

                tool_results = await asyncio.gather(*[_run_tool(p) for p in function_calls])

                function_response_parts = []
                for tool_name, result in tool_results:
                    tools_used.append(tool_name)
                    function_response_parts.append(
                        types.Part.from_function_response(
                            name=tool_name,
                            response=result if isinstance(result, dict) else {"result": str(result)},
                        )
                    )

                # Add function responses to conversation
                contents.append(
                    types.Content(role="user", parts=function_response_parts)
                )

            # Exhausted max rounds — do one final call WITHOUT tools
            logger.warning("Exhausted %d tool rounds, generating final response", MAX_TOOL_ROUNDS)
            final_config = types.GenerateContentConfig(
                temperature=CHATBOT_TEMPERATURE,
                max_output_tokens=CHATBOT_MAX_TOKENS,
                system_instruction=system_prompt,
            )
            final_response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=final_config,
            )
            text = final_response.text if hasattr(final_response, "text") else ""
            return text or "I couldn't generate a response.", tools_used

        except Exception as e:
            # Auto-rotate on exhaustion errors (429, 503, quota, etc.)
            if self._is_exhaustion_error(e) and _retry_count < len(self._combos):
                logger.warning("Model/key exhausted (%s:%s), rotating... (attempt %d)",
                               self.model, str(e)[:60], _retry_count + 1)
                if self._rotate():
                    return await self.generate_with_tools(
                        system_prompt=system_prompt,
                        history=history,
                        user_message=user_message,
                        tool_declarations=tool_declarations,
                        tool_executor=tool_executor,
                        _retry_count=_retry_count + 1,
                    )

            logger.error("Agentic generation failed: %s", e, exc_info=True)
            return "I'm sorry, I encountered a temporary issue. Please try again.", tools_used

    # -- Streaming generation -------------------------------------------------

    async def generate_stream(
        self,
        system_prompt: str,
        history: List[dict],
        user_message: str,
    ) -> AsyncIterator[str]:
        """Generate a streaming response. Yields text chunks.
        On exhaustion errors, rotates to the next (model, key) combo and retries."""
        if not self.is_available:
            yield "Chat service is not configured. Please check GOOGLE_API_KEY."
            return

        for attempt in range(len(self._combos) if self._combos else 1):
            try:
                config = types.GenerateContentConfig(
                    temperature=CHATBOT_TEMPERATURE,
                    max_output_tokens=CHATBOT_MAX_TOKENS,
                    system_instruction=system_prompt,
                )

                contents = list(history)
                contents.append({"role": "user", "parts": [{"text": user_message}]})

                async for chunk in await self.client.aio.models.generate_content_stream(
                    model=self.model,
                    contents=contents,
                    config=config,
                ):
                    if hasattr(chunk, "text") and chunk.text:
                        yield chunk.text

                return  # Success — stop retrying

            except Exception as e:
                if self._is_exhaustion_error(e) and attempt < len(self._combos) - 1:
                    logger.warning("Streaming: model/key exhausted (%s), rotating...", self.model)
                    self._rotate()
                    continue
                logger.error("LLM streaming failed: %s", e)
                yield "I'm sorry, I'm temporarily unable to respond. Please try again."
                return


# =============================================================================
# Chat Orchestrator — Main Entry Point
# =============================================================================

class ChatOrchestrator:
    """
    Coordinates the agentic chatbot pipeline.

    For enhanced chat (chat_with_context), the LLM autonomously decides which
    tools to call using Gemini function calling. For basic chat, no tools are
    used.
    """

    def __init__(self):
        from app.services.chatbot.hybrid_service import MemoryManager
        self.memory = MemoryManager()
        self.llm = LLMProvider()

    @property
    def is_configured(self) -> bool:
        return self.llm.is_available

    # -------------------------------------------------------------------------
    # Simple Chat (no tools, no DB)
    # -------------------------------------------------------------------------

    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        mode: ChatMode = ChatMode.GENERAL,
    ) -> tuple[str, str]:
        """Basic chat with conversation memory. Returns (response, conversation_id)."""
        try:
            message = sanitize_message(message)
        except ValueError as e:
            conv_id = conversation_id or self.memory.generate_conversation_id()
            return str(e), conv_id

        conv_id = conversation_id or self.memory.generate_conversation_id()
        system_prompt = get_system_prompt(mode)
        history = self.memory.get_session_history(conv_id)

        response = await self.llm.generate(
            system_prompt=system_prompt,
            history=history,
            user_message=message,
        )

        self.memory.add_turn(conv_id, message, response)
        return response, conv_id

    async def chat_stream(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        mode: ChatMode = ChatMode.GENERAL,
    ) -> AsyncIterator[str]:
        """Streaming basic chat."""
        conv_id = conversation_id or self.memory.generate_conversation_id()
        system_prompt = get_system_prompt(mode)
        history = self.memory.get_session_history(conv_id)

        full_response = ""
        async for chunk in self.llm.generate_stream(
            system_prompt=system_prompt,
            history=history,
            user_message=message,
        ):
            full_response += chunk
            yield chunk

        self.memory.add_turn(conv_id, message, full_response)

    # -------------------------------------------------------------------------
    # Agentic Chat (LLM decides which tools to call)
    # -------------------------------------------------------------------------

    async def chat_with_context(
        self,
        db: Session,
        user: User,
        message: str,
        conversation_id: Optional[str] = None,
        use_knowledge_base: bool = True,
        mode: ChatMode = ChatMode.ACADEMIC,
    ) -> Dict[str, Any]:
        """
        Agentic chat — the LLM autonomously calls tools to gather context.

        Pipeline:
        0. Sanitize input + check cache
        1. Load user context + persistent memory
        2. Build prompt with identity injection + rewritten query
        3. LLM decides which tools to call (function calling loop)
        4. LLM synthesizes tool results into final response
        5. Save to memory + compute confidence + cache result
        """
        from app.services.chatbot.hybrid_service import ToolExecutor, TOOL_DECLARATIONS

        conv_id = conversation_id or self.memory.generate_conversation_id()
        start_time = time.time()

        # 0. Input sanitization
        try:
            message = sanitize_message(message)
        except ValueError as e:
            return self._fallback_response(conv_id, str(e))

        # Check response cache for identical recent queries
        cached = _response_cache.get(user.id, message, mode.value)
        if cached:
            logger.info("Cache hit for user=%s query='%s...'", user.id, message[:40])
            cached_copy = dict(cached)
            cached_copy["conversation_id"] = conv_id
            cached_copy["cached"] = True
            return cached_copy

        try:
            # 1. Create per-request tool executor with DB + user context
            tool_executor = ToolExecutor(db=db, user=user, use_kb=use_knowledge_base)

            # 2. Load context for prompt personalization
            user_context = tool_executor.get_user_context()
            persistent_summaries = self.memory.load_persistent_summaries(db, user)

            # 3. PRE-FETCH KB context — aggressively search the
            #    knowledge base up front so the LLM always has document context.
            kb_context_text = ""
            kb_sources: List[Dict[str, Any]] = []
            if use_knowledge_base:
                try:
                    from config.db import SessionLocal as _KBSession
                    from app.services.rag.search_pipeline import semantic_search_chroma
                    from app.services.rag.embedding_service import generate_embedding

                    search_query = rewrite_query_for_rag(message)
                    query_embedding = generate_embedding(search_query)

                    if query_embedding:
                        kb_session = _KBSession()
                        try:
                            kb_results = semantic_search_chroma(
                                query_embedding=query_embedding,
                                top_k=10,
                                filters={},
                                similarity_threshold=0.15,
                            )
                        finally:
                            kb_session.close()

                        if kb_results:
                            parts = []
                            for r in kb_results[:8]:
                                title = r.get("source_title", "Unknown")
                                content = r.get("content", "")[:800]
                                score = r.get("score", 0)
                                parts.append(f"[Source: {title} | relevance: {score:.2f}]\n{content}")
                                kb_sources.append({"type": "knowledge", "title": title, "category": r.get("source_category", "")})
                            kb_context_text = "\n\n".join(parts)
                            logger.info("Pre-fetched %d KB results (top score=%.3f)", len(parts), kb_results[0].get("score", 0))
                except Exception as kb_err:
                    logger.warning("Pre-fetch KB search failed (non-fatal): %s", kb_err)

            # 4. Build the user prompt (identity + memory + KB context)
            composed_prompt = build_agentic_prompt(
                user_message=message,
                user_context=user_context,
                previous_summaries=persistent_summaries or None,
            )

            # Inject KB context into the prompt with emphatic grounding instruction
            if kb_context_text:
                composed_prompt = (
                    f"{composed_prompt}\n\n"
                    f"==================================================\n"
                    f"CRITICAL — YOU MUST USE THIS CONTENT TO ANSWER\n"
                    f"==================================================\n"
                    f"The following content was retrieved from the uploaded course "
                    f"documents. Your answer MUST be based on this information. "
                    f"Do NOT ignore or contradict it. Cite the EXACT source title as shown in [Source: ...].\n\n"
                    f"{kb_context_text}\n\n"
                    f"==================================================\n"
                    f"END OF UPLOADED DOCUMENT CONTENT\n"
                    f"=================================================="
                )

            # 5. Agentic generation — use the mode the frontend requested
            system_prompt = get_system_prompt(mode)
            history = self.memory.get_session_history(conv_id)

            response, tools_used = await self.llm.generate_with_tools(
                system_prompt=system_prompt,
                history=history,
                user_message=composed_prompt,
                tool_declarations=TOOL_DECLARATIONS,
                tool_executor=tool_executor,
            )

            # Merge pre-fetched KB sources into tool_executor sources
            if kb_sources:
                for src in kb_sources:
                    tool_executor._sources.append(src)
                if "search_knowledge_base" not in tools_used:
                    tools_used.append("search_knowledge_base")

            # 5. Save to memory
            self.memory.add_turn(conv_id, message, response)
            self.memory.save_session(
                db=db, user=user, conversation_id=conv_id,
                user_message=message, assistant_response=response,
            )

            priority = self._infer_priority(tools_used)
            confidence = self._compute_confidence(tools_used, tool_executor)
            elapsed_ms = round((time.time() - start_time) * 1000)

            result = {
                "answer": response,
                "conversation_id": conv_id,
                "mode": mode.value,
                "priority_used": priority,
                "tools_used": tools_used,
                "confidence": confidence,
                "knowledge_sources_used": tools_used.count("search_knowledge_base"),
                "relevant_queries_found": tools_used.count("search_student_queries"),
                "sources": tool_executor.get_sources_used(),
                "user_context": {
                    "role": user_context.get("role", "student"),
                    "is_new_user": user_context.get("is_new_user", False),
                },
                "response_time_ms": elapsed_ms,
            }

            # Cache the result for repeated identical queries
            _response_cache.put(user.id, message, mode.value, result)
            logger.info(
                "Agentic chat completed in %dms | tools=%s | confidence=%s",
                elapsed_ms, tools_used, confidence,
            )

            return result

        except Exception as e:
            logger.error("Agentic chat failed: %s", e, exc_info=True)
            return self._fallback_response(conv_id, str(e))

    async def chat_stream_with_context(
        self,
        db: Session,
        user: User,
        message: str,
        conversation_id: Optional[str] = None,
        use_knowledge_base: bool = True,
    ) -> AsyncIterator[str]:
        """
        Streaming agentic chat.

        Strategy: run the tool-calling loop first (non-streaming), then
        stream the final response. This gives the agent full tool access
        while still providing a streaming UX for the final answer.
        """
        from app.services.chatbot.hybrid_service import ToolExecutor, TOOL_DECLARATIONS

        conv_id = conversation_id or self.memory.generate_conversation_id()

        try:
            tool_executor = ToolExecutor(db=db, user=user, use_kb=use_knowledge_base)
            user_context = tool_executor.get_user_context()
            persistent_summaries = self.memory.load_persistent_summaries(db, user)

            composed_prompt = build_agentic_prompt(
                user_message=message,
                user_context=user_context,
                previous_summaries=persistent_summaries or None,
            )

            system_prompt = get_system_prompt(ChatMode.ACADEMIC)
            history = self.memory.get_session_history(conv_id)

            # Run the agentic tool-calling loop (non-streaming)
            # then collect tool context and stream the final answer
            gemini_tools = [types.Tool(function_declarations=TOOL_DECLARATIONS)]
            config_with_tools = types.GenerateContentConfig(
                temperature=CHATBOT_TEMPERATURE,
                max_output_tokens=CHATBOT_MAX_TOKENS,
                system_instruction=system_prompt,
                tools=gemini_tools,
            )

            contents = list(history)
            contents.append({"role": "user", "parts": [{"text": composed_prompt}]})

            # Tool-calling rounds (non-streaming)
            for _ in range(MAX_TOOL_ROUNDS):
                response = await self.llm.client.aio.models.generate_content(
                    model=self.llm.model,
                    contents=contents,
                    config=config_with_tools,
                )

                response_content = response.candidates[0].content
                function_calls = [
                    p for p in response_content.parts
                    if hasattr(p, "function_call") and p.function_call
                ]

                if not function_calls:
                    # No more tool calls — stream the text from this response
                    text = response.text if hasattr(response, "text") else ""
                    if text:
                        yield text
                    self.memory.add_turn(conv_id, message, text)
                    self.memory.save_session(
                        db=db, user=user, conversation_id=conv_id,
                        user_message=message, assistant_response=text,
                    )
                    return

                # Execute tools
                contents.append(response_content)
                fn_parts = []
                for part in function_calls:
                    result = await tool_executor.execute(
                        part.function_call.name,
                        dict(part.function_call.args) if part.function_call.args else {},
                    )
                    fn_parts.append(
                        types.Part.from_function_response(
                            name=part.function_call.name,
                            response=result if isinstance(result, dict) else {"result": str(result)},
                        )
                    )
                contents.append(types.Content(role="user", parts=fn_parts))

            # Max rounds exhausted — stream the final response without tools
            config_no_tools = types.GenerateContentConfig(
                temperature=CHATBOT_TEMPERATURE,
                max_output_tokens=CHATBOT_MAX_TOKENS,
                system_instruction=system_prompt,
            )

            full_response = ""
            async for chunk in await self.llm.client.aio.models.generate_content_stream(
                model=self.llm.model,
                contents=contents,
                config=config_no_tools,
            ):
                if hasattr(chunk, "text") and chunk.text:
                    full_response += chunk.text
                    yield chunk.text

            self.memory.add_turn(conv_id, message, full_response)
            self.memory.save_session(
                db=db, user=user, conversation_id=conv_id,
                user_message=message, assistant_response=full_response,
            )

        except Exception as e:
            logger.error("Streaming agentic chat failed: %s", e)
            yield f"I apologize, but I encountered an error. Please try again."

    # -------------------------------------------------------------------------
    # Query-Specific
    # -------------------------------------------------------------------------

    async def answer_query(
        self, db: Session, user: User, query_id: int,
    ) -> Dict[str, Any]:
        """Generate an AI answer for a specific database query."""
        from app.models.query import Query

        try:
            query = db.query(Query).filter(Query.id == query_id).first()
            if not query:
                return {"error": "Query not found"}

            message = f"Query: {query.title}\nDescription: {query.description}"
            result = await self.chat_with_context(db=db, user=user, message=message)

            return {
                "query_id": query_id,
                "answer": result["answer"],
                "sources_used": [s.get("title", "") for s in result.get("sources", [])],
                "tools_used": result.get("tools_used", []),
                "confidence": "high" if result.get("knowledge_sources_used", 0) > 0 else "medium",
            }
        except Exception as e:
            logger.error("Failed to answer query %d: %s", query_id, e)
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------

    def clear_conversation(self, conversation_id: str) -> bool:
        return self.memory.clear_session(conversation_id)

    def get_conversation_history(self, conversation_id: str) -> list:
        return self.memory.get_session_history(conversation_id)

    def _infer_priority(self, tools_used: List[str]) -> str:
        """Map the tools used to a priority label for backward compatibility."""
        if not tools_used:
            return PRIORITY_GENERAL_KNOWLEDGE
        if "search_knowledge_base" in tools_used:
            return PRIORITY_KNOWLEDGE_BASE
        if "search_student_queries" in tools_used:
            return PRIORITY_DATABASE_QUERIES
        if "list_all_queries" in tools_used:
            return PRIORITY_QUERY_LIST
        if "get_course_info" in tools_used:
            return PRIORITY_DATABASE_QUERIES
        if "search_web" in tools_used:
            return PRIORITY_WEB_SEARCH
        return PRIORITY_AGENTIC

    def _compute_confidence(self, tools_used: List[str], tool_executor) -> str:
        """
        Compute a confidence label based on what tools were used and what
        sources were returned. This helps the frontend display trust indicators.
        """
        sources = tool_executor.get_sources_used() if tool_executor else []

        if not tools_used:
            return "medium"  # General knowledge — reasonable but unverified

        # Higher confidence when grounded in internal sources
        has_kb = "search_knowledge_base" in tools_used
        has_queries = "search_student_queries" in tools_used
        has_course = "get_course_info" in tools_used
        has_web = "search_web" in tools_used

        if (has_kb or has_queries or has_course) and len(sources) >= 2:
            return "high"
        if has_kb or has_queries or has_course:
            return "high" if sources else "medium"
        if has_web:
            return "medium"

        return "medium"

    def _fallback_response(self, conv_id: str, error: str) -> Dict[str, Any]:
        return {
            "answer": (
                "I apologize, but I'm having trouble processing your request. "
                "This might be due to a temporary issue with the AI service. "
                "Please try again in a moment or ask a different question."
            ),
            "conversation_id": conv_id,
            "priority_used": PRIORITY_ERROR,
            "tools_used": [],
            "confidence": "low",
            "knowledge_sources_used": 0,
            "relevant_queries_found": 0,
            "sources": [],
            "user_context": {},
            "error": error,
        }


# Module-level singleton
chatbot_service = ChatOrchestrator()
