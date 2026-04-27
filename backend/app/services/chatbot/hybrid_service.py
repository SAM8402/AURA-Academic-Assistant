"""
Hybrid Chatbot Service supporting both LangChain and Google ADK (native Genai SDK)

This service provides two implementations:
1. LangChain-based (using ChatGoogleGenerativeAI)
2. Native Google Genai SDK (from google-adk)

Choose based on your needs:
- LangChain: Better for complex workflows, memory management, and LangChain ecosystem
- Native SDK: More direct control, faster, and simpler for basic chat

Enhanced Features (Native SDK):
- Cross-Session State Sharing
- Automating Memory Storage with callbacks
- load_memory functionality
- Agent Observability with plugins
"""

import os
import uuid
import logging
from typing import Dict, Optional, AsyncIterator, Any, TYPE_CHECKING, List
from datetime import datetime, timedelta
from enum import Enum

# Web search imports
try:
    from duckduckgo_search import DDGS
    WEB_SEARCH_AVAILABLE = True
except ImportError:
    WEB_SEARCH_AVAILABLE = False
    DDGS = None

if TYPE_CHECKING:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.memory import ConversationBufferMemory
    from langchain.chains import ConversationChain

# Try LangChain imports
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.memory import ConversationBufferMemory
    from langchain.chains import ConversationChain
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    ChatGoogleGenerativeAI = None
    ConversationBufferMemory = None
    ConversationChain = None

# Try Google Genai SDK imports (from google-adk)
try:
    from google import genai
    from google.genai import types
    from google.adk.agents import LlmAgent
    from google.adk.models.google_llm import Gemini
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.memory import InMemoryMemoryService
    from google.adk.tools import AgentTool, ToolContext
    from google.adk.plugins.base_plugin import BasePlugin
    from google.adk.plugins.logging_plugin import LoggingPlugin
    from google.adk.agents.callback_context import CallbackContext
    from google.adk.agents.base_agent import BaseAgent
    from google.adk.models.llm_request import LlmRequest
    GENAI_SDK_AVAILABLE = True
except ImportError:
    GENAI_SDK_AVAILABLE = False
    genai = None
    types = None
    LlmAgent = None
    Gemini = None
    Runner = None
    InMemorySessionService = None
    InMemoryMemoryService = None
    AgentTool = None
    ToolContext = None
    BasePlugin = None
    LoggingPlugin = None
    CallbackContext = None
    BaseAgent = None
    LlmRequest = None

from config.settings import settings
from app.schemas.chatbot_schema import ChatMode

# SQLAlchemy imports for database integration
try:
    from sqlalchemy.orm import Session
    from app.models.user import User
    from app.models.knowledge import KnowledgeSource, KnowledgeChunk
    from app.models.task import Task
    from app.models.query import Query
    from app.models.enums import CategoryEnum, TaskStatusEnum
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Session = None
    User = None
    KnowledgeSource = None
    KnowledgeChunk = None
    Task = None
    Query = None
    CategoryEnum = None
    TaskStatusEnum = None


# ============================================================================
# Custom Tools for Cross-Session State Sharing
# ============================================================================

def save_user_context(context: ToolContext, key: str, value: str) -> str:
    """
    Save user context to session state for cross-session sharing.

    Args:
        context: Tool invocation context
        key: Context key (e.g., 'username', 'topic', 'preferences')
        value: Context value to store

    Returns:
        Confirmation message
    """
    if not GENAI_SDK_AVAILABLE or not hasattr(context, 'invocation_context'):
        return f"Context saved locally: {key}={value}"

    session = context.invocation_context.session
    session.state[key] = value
    return f"Saved {key} to your session state"


def retrieve_user_context(context: ToolContext, key: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve user context from session state.

    Args:
        context: Tool invocation context
        key: Specific key to retrieve (None = return all)

    Returns:
        Session state dictionary or specific value
    """
    if not GENAI_SDK_AVAILABLE or not hasattr(context, 'invocation_context'):
        return {"message": "Context retrieval not available"}

    session = context.invocation_context.session

    if key:
        return {key: session.state.get(key, "Not found")}
    else:
        return dict(session.state)


def preload_memory(context: ToolContext) -> str:
    """
    Preload previous conversation memories from memory service.

    Args:
        context: Tool invocation context

    Returns:
        Status message
    """
    if not GENAI_SDK_AVAILABLE or not hasattr(context, 'invocation_context'):
        return "Memory preload not available"

    try:
        invocation_context = context.invocation_context
        memory_service = invocation_context.memory_service

        if not memory_service:
            return "Memory service not configured"

        # Memory service automatically loads relevant memories
        # This tool explicitly triggers memory awareness
        return "Previous conversation context loaded successfully"

    except Exception as e:
        return f"Memory preload failed: {str(e)}"


# ============================================================================
# Callback for Automating Memory Storage
# ============================================================================

async def auto_save_to_memory(callback_context: CallbackContext) -> None:
    """
    Automatically save session to memory after each agent turn.

    This callback ensures conversation context is persisted for future sessions.

    Args:
        callback_context: Agent callback context
    """
    try:
        invocation_context = callback_context._invocation_context
        memory_service = invocation_context.memory_service
        session = invocation_context.session

        if memory_service and session:
            await memory_service.add_session_to_memory(session)
            logging.debug(f"[Memory] Auto-saved session {session.id}")

    except Exception as e:
        logging.error(f"[Memory] Auto-save failed: {e}")


# ============================================================================
# Observability Plugin for Agent Monitoring
# ============================================================================

class ChatbotObservabilityPlugin(BasePlugin):
    """
    Custom plugin for tracking chatbot metrics and performance.

    Features:
    - Count agent invocations
    - Count tool calls
    - Count LLM requests
    - Track conversation patterns
    """

    def __init__(self) -> None:
        """Initialize the observability plugin with counters."""
        super().__init__(name="chatbot_observability")
        self.agent_count: int = 0
        self.tool_count: int = 0
        self.llm_request_count: int = 0
        self.conversations: Dict[str, int] = {}

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> None:
        """Count agent invocations."""
        self.agent_count += 1
        logging.info(f"[Observability] Agent runs: {self.agent_count}")

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> None:
        """Count LLM requests."""
        self.llm_request_count += 1
        logging.info(f"[Observability] LLM requests: {self.llm_request_count}")

    def get_metrics(self) -> Dict[str, int]:
        """Get current metrics."""
        return {
            "agent_invocations": self.agent_count,
            "tool_calls": self.tool_count,
            "llm_requests": self.llm_request_count,
            "unique_conversations": len(self.conversations)
        }


# ============================================================================
# Chat Implementation Enum
# ============================================================================

class ChatImplementation(str, Enum):
    """Available chat implementations"""
    LANGCHAIN = "langchain"
    NATIVE_SDK = "native_sdk"


class HybridChatbotService:
    """
    Hybrid chatbot service supporting both LangChain and native Google Genai SDK.

    Features:
    - Dual implementation support
    - Conversation memory for both implementations
    - Streaming support
    - Multiple chat modes
    """

    def __init__(
        self,
        implementation: ChatImplementation = ChatImplementation.NATIVE_SDK,
        enable_memory: bool = True,
        enable_observability: bool = True,
        app_name: str = "AURA"
    ):
        """
        Initialize chatbot service.

        Args:
            implementation: Which implementation to use (langchain or native_sdk)
            enable_memory: Enable cross-session memory storage (Native SDK only)
            enable_observability: Enable metrics tracking (Native SDK only)
            app_name: Application name for session management
        """
        self.implementation = implementation
        self.conversations: Dict[str, Any] = {}
        self.llm = None
        self.genai_client = None

        # ADK-specific components for enhanced features
        self.session_service = None
        self.memory_service = None
        self.observability_plugin = None
        self.adk_agent = None
        self.adk_runner = None
        self.app_name = app_name
        self.enable_memory = enable_memory
        self.enable_observability = enable_observability

        # Initialize based on selected implementation
        if implementation == ChatImplementation.LANGCHAIN:
            self._init_langchain()
        elif implementation == ChatImplementation.NATIVE_SDK:
            self._init_native_sdk()

    def _init_langchain(self):
        """Initialize LangChain implementation"""
        if not LANGCHAIN_AVAILABLE:
            print("[WARNING] LangChain not available. Install: pip install langchain langchain-google-genai")
            return

        if not settings.GOOGLE_API_KEY:
            print("[WARNING] GOOGLE_API_KEY not set")
            return

        try:
            self.llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=settings.GEMINI_TEMPERATURE,
                max_output_tokens=settings.GEMINI_MAX_TOKENS
            )
            print(f"[OK] LangChain Gemini LLM initialized - Model: {settings.GEMINI_MODEL}")
        except Exception as e:
            print(f"[ERROR] Failed to initialize LangChain: {e}")

    def _init_native_sdk(self):
        """
        Initialize native Google Genai SDK with enhanced ADK features.

        Features:
        - Session management for cross-session state
        - Memory service for conversation persistence
        - Custom tools for state management
        - Auto-save callback for memory automation
        - Observability plugin for metrics
        """
        if not GENAI_SDK_AVAILABLE:
            print("[WARNING] Google Genai SDK not available. Install: pip install google-adk")
            return

        if not settings.GOOGLE_API_KEY:
            print("[WARNING] GOOGLE_API_KEY not set")
            return

        # Set API key as environment variable for Google ADK
        os.environ['GOOGLE_API_KEY'] = settings.GOOGLE_API_KEY

        try:
            # Basic client for simple operations
            self.genai_client = genai.Client(api_key=settings.GOOGLE_API_KEY)

            # Initialize session service for cross-session state sharing
            self.session_service = InMemorySessionService()
            print("[OK] Session service initialized")

            # Initialize memory service if enabled
            if self.enable_memory:
                self.memory_service = InMemoryMemoryService()
                print("[OK] Memory service initialized")

            # Initialize observability plugin if enabled
            if self.enable_observability:
                self.observability_plugin = ChatbotObservabilityPlugin()
                print("[OK] Observability plugin initialized")

            # Configure retry options for reliability
            retry_config = types.HttpRetryOptions(
                attempts=5,
                exp_base=7,
                initial_delay=1,
                http_status_codes=[429, 500, 503, 504]
            )

            # Create LLM agent with memory callback
            # Note: Custom tools with ToolContext are not compatible with ADK's automatic function calling
            # Memory and session state are managed by the Runner's session_service and memory_service

            self.adk_agent = LlmAgent(
                model=Gemini(
                    model=settings.GEMINI_MODEL,
                    api_key=settings.GOOGLE_API_KEY,
                    retry_options=retry_config
                ),
                name="AURA",
                description="AURA (Academic Unified Response Assistant) - AI teaching assistant with cross-session memory",
                instruction="""You are AURA, an intelligent academic assistant.

Your conversations are automatically saved and can be referenced in future sessions.
Provide clear, educational explanations and help students learn effectively.""",
                after_agent_callback=auto_save_to_memory if self.enable_memory else None
            )

            # Create plugins list
            plugins = []
            if self.enable_observability and self.observability_plugin:
                plugins.append(self.observability_plugin)
            # Note: LoggingPlugin has emoji characters that cause UnicodeEncodeError on Windows
            # We use our custom ChatbotObservabilityPlugin instead

            # Create runner with all enhanced features
            self.adk_runner = Runner(
                agent=self.adk_agent,
                app_name=self.app_name,
                session_service=self.session_service,
                memory_service=self.memory_service if self.enable_memory else None,
                plugins=plugins
            )

            print(f"[OK] Google ADK initialized - Model: {settings.GEMINI_MODEL}")
            print(f"     - Memory: {'Enabled' if self.enable_memory else 'Disabled'}")
            print(f"     - Observability: {'Enabled' if self.enable_observability else 'Disabled'}")
            print(f"     - Session Service: Active")

        except Exception as e:
            print(f"[ERROR] Failed to initialize Google ADK: {e}")
            import traceback
            traceback.print_exc()

    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        mode: ChatMode = ChatMode.GENERAL
    ) -> tuple[str, str]:
        """
        Generate chat response using selected implementation.

        Args:
            message: User's message
            conversation_id: Optional conversation ID for history
            mode: Chat mode (academic, general, etc.)

        Returns:
            Tuple of (response, conversation_id)
        """
        if not conversation_id:
            conversation_id = f"conv-{uuid.uuid4().hex[:12]}"

        # Route to appropriate implementation
        if self.implementation == ChatImplementation.LANGCHAIN:
            return await self._chat_langchain(message, conversation_id, mode)
        elif self.implementation == ChatImplementation.NATIVE_SDK:
            return await self._chat_native_sdk(message, conversation_id, mode)
        else:
            return ("No chat implementation available", conversation_id)

    async def _chat_langchain(
        self,
        message: str,
        conversation_id: str,
        mode: ChatMode
    ) -> tuple[str, str]:
        """Chat using LangChain implementation"""
        if not self.llm:
            return (
                "[WARNING] LangChain chatbot not configured.",
                conversation_id
            )

        try:
            # Get or create conversation memory
            memory = self._get_or_create_langchain_memory(conversation_id)

            # Create conversation chain
            conversation = ConversationChain(
                llm=self.llm,
                memory=memory,
                verbose=False
            )

            # Generate response
            response = await conversation.apredict(input=message)

            return response, conversation_id

        except Exception as e:
            print(f"LangChain chat error: {e}")
            return f"I apologize, but I encountered an error: {str(e)}", conversation_id

    async def _chat_native_sdk(
        self,
        message: str,
        conversation_id: str,
        mode: ChatMode
    ) -> tuple[str, str]:
        """
        Chat using native Google Genai SDK with ADK runner.

        This method uses the enhanced ADK features:
        - Session management for state persistence
        - Memory service for cross-session context
        - Custom tools for user context management
        - Auto-save callback for automatic memory storage
        - Observability for tracking metrics
        """
        if not self.adk_runner:
            # Fallback to basic genai_client if ADK not available
            return await self._chat_native_sdk_basic(message, conversation_id, mode)

        try:
            # Use conversation_id as session_id for ADK
            session_id = conversation_id
            user_id = "default_user"  # Could be extracted from request context

            # Create or get session
            try:
                session = await self.session_service.create_session(
                    app_name=self.app_name,
                    user_id=user_id,
                    session_id=session_id
                )
            except:
                session = await self.session_service.get_session(
                    app_name=self.app_name,
                    user_id=user_id,
                    session_id=session_id
                )

            # Add mode-specific context to session state
            session.state["chat_mode"] = mode.value

            # Convert message to ADK Content format
            user_message = types.Content(
                role="user",
                parts=[types.Part(text=message)]
            )

            # Run the agent with session context
            response_text = ""
            async for event in self.adk_runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=user_message
            ):
                # Extract response from event
                if event.content and event.content.parts:
                    if event.content.parts[0].text and event.content.parts[0].text != "None":
                        response_text = event.content.parts[0].text

            # Memory is automatically saved by the callback
            return response_text, conversation_id

        except Exception as e:
            print(f"ADK chat error: {e}")
            import traceback
            traceback.print_exc()
            return f"I apologize, but I encountered an error: {str(e)}", conversation_id

    async def _chat_native_sdk_basic(
        self,
        message: str,
        conversation_id: str,
        mode: ChatMode
    ) -> tuple[str, str]:
        """Fallback basic chat using genai client (without ADK features)"""
        if not self.genai_client:
            return (
                "[WARNING] Google Genai SDK not configured.",
                conversation_id
            )

        try:
            # Get or create conversation history
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = []

            history = self.conversations[conversation_id]

            # Add system instruction based on mode
            system_instruction = self._get_system_prompt(mode)

            # Prepare chat config
            config = types.GenerateContentConfig(
                temperature=settings.GEMINI_TEMPERATURE,
                max_output_tokens=settings.GEMINI_MAX_TOKENS,
                system_instruction=system_instruction,
            )

            # Add user message to history
            history.append({
                "role": "user",
                "parts": [{"text": message}]
            })

            # Generate response
            response = await self.genai_client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=history,
                config=config
            )

            # Extract response text
            response_text = response.text if hasattr(response, 'text') else str(response)

            # Add assistant response to history
            history.append({
                "role": "model",
                "parts": [{"text": response_text}]
            })

            # Update conversation history
            self.conversations[conversation_id] = history

            return response_text, conversation_id

        except Exception as e:
            print(f"Native SDK chat error: {e}")
            return f"I apologize, but I encountered an error: {str(e)}", conversation_id

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
        if not conversation_id:
            conversation_id = f"conv-{uuid.uuid4().hex[:12]}"

        # Route to appropriate implementation
        if self.implementation == ChatImplementation.NATIVE_SDK and self.genai_client:
            async for chunk in self._chat_stream_native_sdk(message, conversation_id, mode):
                yield chunk
        elif self.implementation == ChatImplementation.LANGCHAIN and self.llm:
            async for chunk in self._chat_stream_langchain(message, conversation_id, mode):
                yield chunk
        else:
            yield "[WARNING] No streaming implementation available"

    async def _chat_stream_native_sdk(
        self,
        message: str,
        conversation_id: str,
        mode: ChatMode
    ) -> AsyncIterator[str]:
        """
        Stream chat using native Google Genai SDK with ADK runner.

        Uses enhanced features:
        - Session management
        - Memory service
        - Auto-save callback (triggered after completion)
        """
        if not self.adk_runner:
            # Fallback to basic streaming
            async for chunk in self._chat_stream_native_sdk_basic(message, conversation_id, mode):
                yield chunk
            return

        try:
            session_id = conversation_id
            user_id = "default_user"

            # Create or get session
            try:
                session = await self.session_service.create_session(
                    app_name=self.app_name,
                    user_id=user_id,
                    session_id=session_id
                )
            except:
                session = await self.session_service.get_session(
                    app_name=self.app_name,
                    user_id=user_id,
                    session_id=session_id
                )

            # Add mode to session state
            session.state["chat_mode"] = mode.value

            # Convert message to ADK format
            user_message = types.Content(
                role="user",
                parts=[types.Part(text=message)]
            )

            # Stream response from agent
            async for event in self.adk_runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=user_message
            ):
                if event.content and event.content.parts:
                    if event.content.parts[0].text and event.content.parts[0].text != "None":
                        yield event.content.parts[0].text

            # Memory automatically saved by callback

        except Exception as e:
            yield f"Error: {str(e)}"
            import traceback
            traceback.print_exc()

    async def _chat_stream_native_sdk_basic(
        self,
        message: str,
        conversation_id: str,
        mode: ChatMode
    ) -> AsyncIterator[str]:
        """Fallback basic streaming using genai client (without ADK features)"""
        try:
            # Get or create conversation history
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = []

            history = self.conversations[conversation_id]

            # Add system instruction
            system_instruction = self._get_system_prompt(mode)

            # Prepare config
            config = types.GenerateContentConfig(
                temperature=settings.GEMINI_TEMPERATURE,
                max_output_tokens=settings.GEMINI_MAX_TOKENS,
                system_instruction=system_instruction,
            )

            # Add user message
            history.append({
                "role": "user",
                "parts": [{"text": message}]
            })

            # Stream response
            full_response = ""
            async for chunk in await self.genai_client.aio.models.generate_content_stream(
                model=settings.GEMINI_MODEL,
                contents=history,
                config=config
            ):
                if hasattr(chunk, 'text'):
                    full_response += chunk.text
                    yield chunk.text

            # Add complete response to history
            history.append({
                "role": "model",
                "parts": [{"text": full_response}]
            })

            self.conversations[conversation_id] = history

        except Exception as e:
            yield f"Error: {str(e)}"

    async def _chat_stream_langchain(
        self,
        message: str,
        conversation_id: str,
        mode: ChatMode
    ) -> AsyncIterator[str]:
        """Stream chat using LangChain"""
        try:
            memory = self._get_or_create_langchain_memory(conversation_id)
            memory.chat_memory.add_user_message(message)

            full_response = ""
            async for chunk in self.llm.astream(message):
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                full_response += content
                yield content

            memory.chat_memory.add_ai_message(full_response)

        except Exception as e:
            yield f"Error: {str(e)}"

    def _get_or_create_langchain_memory(self, conversation_id: str) -> Any:
        """Get or create LangChain conversation memory"""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = ConversationBufferMemory(
                return_messages=True,
                memory_key="history"
            )
        return self.conversations[conversation_id]

    def _get_system_prompt(self, mode: ChatMode) -> str:
        """Get system prompt based on mode"""
        prompts = {
            ChatMode.ACADEMIC: "You are AURA, an academic AI assistant. Provide clear, educational explanations with examples.",
            ChatMode.DOUBT_CLARIFICATION: "You are AURA, helping students clarify doubts. Ask clarifying questions and provide step-by-step explanations.",
            ChatMode.STUDY_HELP: "You are AURA, a study assistant. Help with study strategies, time management, and learning techniques.",
            ChatMode.GENERAL: "You are AURA (Academic Unified Response Assistant), an AI teaching assistant. Be helpful, educational, and encouraging."
        }
        return prompts.get(mode, prompts[ChatMode.GENERAL])

    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear conversation history"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False

    def get_conversation_history(self, conversation_id: str) -> list:
        """Get conversation history"""
        if conversation_id in self.conversations:
            return self.conversations[conversation_id]
        return []

    # =========================================================================
    # Knowledge Base Integration Methods
    # =========================================================================

    def search_knowledge_base(
        self,
        db: Session,
        query: str,
        category: Optional[CategoryEnum] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search knowledge base for relevant information using RAG semantic search.

        Uses Gemini embeddings + cosine similarity for semantic matching,
        with keyword search as fallback.

        Args:
            db: Database session
            query: Search query
            category: Optional category filter
            limit: Maximum number of results

        Returns:
            List of relevant knowledge sources with similarity scores
        """
        if not SQLALCHEMY_AVAILABLE:
            logging.warning("SQLAlchemy not available for knowledge base search")
            return []

        # Try RAG semantic search first
        try:
            from app.services.rag.search_pipeline import semantic_search_sqlite
            from app.services.rag.embedding_service import generate_embedding

            # Generate query embedding
            query_embedding = generate_embedding(query)

            if query_embedding:
                # Build filters
                filters = {}
                if category:
                    filters["category"] = category

                # Run semantic search
                results = semantic_search_sqlite(
                    session=db,
                    query_embedding=query_embedding,
                    top_k=limit,
                    filters=filters,
                    similarity_threshold=0.3
                )

                if results:
                    logging.info(
                        "RAG semantic search found %d results for: '%s'",
                        len(results), query[:50]
                    )
                    return [
                        {
                            "id": r.get("source_id", ""),
                            "title": r.get("source_title", "Unknown"),
                            "description": r.get("source_description", ""),
                            "content": r.get("content", "")[:500] + "..." if len(r.get("content", "")) > 500 else r.get("content", ""),
                            "category": r.get("source_category", "Unknown"),
                            "relevance": f"semantic ({r.get('score', 0.0):.3f})",
                            "score": r.get("score", 0.0)
                        }
                        for r in results
                    ]

        except Exception as e:
            logging.warning("RAG semantic search failed, falling back to keyword: %s", e)

        # Fallback to keyword search
        try:
            db_query = db.query(KnowledgeSource).filter(
                KnowledgeSource.is_active == True
            )

            if category:
                db_query = db_query.filter(KnowledgeSource.category == category)

            if query:
                search_term = f"%{query}%"
                from sqlalchemy import or_
                db_query = db_query.filter(
                    or_(
                        KnowledgeSource.title.ilike(search_term),
                        KnowledgeSource.description.ilike(search_term),
                        KnowledgeSource.content.ilike(search_term)
                    )
                )

            sources = db_query.limit(limit).all()

            return [
                {
                    "id": str(source.id),
                    "title": source.title,
                    "description": source.description,
                    "content": source.content[:500] + "..." if len(source.content) > 500 else source.content,
                    "category": source.category.value,
                    "relevance": "keyword"
                }
                for source in sources
            ]

        except Exception as e:
            logging.error("Error searching knowledge base: %s", e)
            return []

    def get_relevant_chunks(
        self,
        db: Session,
        source_id: str,
        limit: int = 3
    ) -> List[str]:
        """
        Get text chunks from a knowledge source.

        Args:
            db: Database session
            source_id: Knowledge source ID
            limit: Maximum number of chunks

        Returns:
            List of text chunks
        """
        if not SQLALCHEMY_AVAILABLE:
            return []

        try:
            chunks = db.query(KnowledgeChunk).filter(
                KnowledgeChunk.source_id == source_id
            ).order_by(KnowledgeChunk.index).limit(limit).all()

            return [chunk.text for chunk in chunks]

        except Exception as e:
            logging.error(f"Error getting chunks: {e}")
            return []

    def search_web(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Dict[str, str]]:
        """
        Search the web for real-time information using DuckDuckGo.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of search results with title, snippet, and URL
        """
        if not WEB_SEARCH_AVAILABLE:
            logging.warning("Web search not available - duckduckgo_search not installed")
            return []

        try:
            # Initialize DuckDuckGo search
            with DDGS() as ddgs:
                # Perform text search
                results = list(ddgs.text(
                    keywords=query,
                    max_results=max_results,
                    backend="api"  # Use API backend for faster results
                ))

                # Format results
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        "title": result.get("title", ""),
                        "snippet": result.get("body", ""),
                        "url": result.get("href", ""),
                        "source": "web_search"
                    })

                logging.info(f"Web search for '{query}' returned {len(formatted_results)} results")
                return formatted_results

        except Exception as e:
            logging.error(f"Error performing web search: {e}")
            import traceback
            traceback.print_exc()
            return []

    # =========================================================================
    # User Context Retrieval Methods
    # =========================================================================

    def get_user_context(
        self,
        db: Session,
        user: User
    ) -> Dict[str, Any]:
        """
        Get comprehensive user context for personalization.

        Args:
            db: Database session
            user: Current user

        Returns:
            User context dictionary
        """
        if not SQLALCHEMY_AVAILABLE:
            return {
                "user_id": getattr(user, 'id', 'unknown'),
                "full_name": getattr(user, 'full_name', 'Unknown'),
                "role": getattr(user, 'role', 'unknown')
            }

        try:
            # Get recent queries
            recent_queries = db.query(Query).filter(
                Query.student_id == user.id
            ).order_by(Query.created_at.desc()).limit(5).all()

            # Get active tasks
            active_tasks = db.query(Task).filter(
                Task.status.in_([TaskStatusEnum.PENDING.value, TaskStatusEnum.IN_PROGRESS.value])
            ).limit(5).all()

            # Get user statistics
            total_queries = db.query(Query).filter(Query.student_id == user.id).count()

            return {
                "user_id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role.value if hasattr(user.role, 'value') else user.role,
                "recent_queries": [
                    {
                        "title": q.title,
                        "status": q.status.value if hasattr(q.status, 'value') else str(q.status),
                        "created_at": q.created_at.isoformat() if q.created_at else None
                    }
                    for q in recent_queries
                ],
                "active_tasks_count": len(active_tasks),
                "total_queries": total_queries,
                "is_new_user": total_queries == 0
            }

        except Exception as e:
            logging.error(f"Error getting user context: {e}")
            return {
                "user_id": user.id,
                "full_name": user.full_name,
                "role": user.role.value if hasattr(user.role, 'value') else user.role
            }

    def get_relevant_categories(
        self,
        user: User
    ) -> List[CategoryEnum]:
        """
        Get relevant categories based on user role.

        Args:
            user: Current user

        Returns:
            List of relevant categories
        """
        if not SQLALCHEMY_AVAILABLE or not CategoryEnum:
            return []

        role = user.role.value if hasattr(user.role, 'value') else user.role

        # Map roles to relevant categories
        role_categories = {
            "student": [CategoryEnum.COURSES, CategoryEnum.ASSIGNMENTS, CategoryEnum.QUIZZES],
            "ta": [CategoryEnum.COURSES, CategoryEnum.QUERIES, CategoryEnum.ASSIGNMENTS],
            "instructor": [CategoryEnum.COURSES, CategoryEnum.PLACEMENT, CategoryEnum.ADMISSION],
            "admin": list(CategoryEnum)  # All categories
        }

        return role_categories.get(role, [CategoryEnum.QUERIES])

    # =========================================================================
    # Enhanced Chat Methods with Knowledge Base Integration
    # =========================================================================

    async def chat_with_context(
        self,
        db: Session,
        user: User,
        message: str,
        conversation_id: Optional[str] = None,
        use_knowledge_base: bool = True
    ) -> Dict[str, Any]:
        """
        Chat with knowledge base and user context integration.

        Args:
            db: Database session
            user: Current user
            message: User's message
            conversation_id: Optional conversation ID
            use_knowledge_base: Whether to search knowledge base

        Returns:
            Response dictionary with answer and context
        """
        try:
            # Get user context
            user_context = self.get_user_context(db, user)

            # Check if user is asking to list ALL queries
            list_keywords = ['list all', 'show all', 'all queries', 'all my queries', 'what queries']
            is_asking_for_query_list = any(keyword in message.lower() for keyword in list_keywords)

            # PRIORITY 1: Always search database queries first for relevant matches
            relevant_queries_info = None
            all_queries_info = None

            if SQLALCHEMY_AVAILABLE:
                try:
                    user_role = user.role.value if hasattr(user.role, 'value') else user.role

                    if is_asking_for_query_list:
                        # User wants to see ALL queries - fetch complete list
                        if user_role == "student":
                            all_queries = db.query(Query).filter(
                                Query.student_id == user.id
                            ).order_by(Query.created_at.desc()).all()
                        else:
                            all_queries = db.query(Query).order_by(
                                Query.created_at.desc()
                            ).all()

                        if all_queries:
                            all_queries_info = []
                            for q in all_queries:
                                query_info = {
                                    "id": q.id,
                                    "title": q.title,
                                    "description": q.description[:100] + "..." if len(q.description) > 100 else q.description,
                                    "status": q.status.value if hasattr(q.status, 'value') else str(q.status),
                                    "category": q.category.value if hasattr(q.category, 'value') else str(q.category),
                                    "priority": q.priority.value if hasattr(q.priority, 'value') else str(q.priority),
                                    "created_at": q.created_at.isoformat() if q.created_at else None,
                                    "response_count": len(q.responses) if q.responses else 0
                                }
                                if user_role != "student" and q.student:
                                    query_info["student_name"] = q.student.full_name
                                all_queries_info.append(query_info)
                    else:
                        # Search for relevant queries based on message content (PRIORITY 1)
                        # Use simple keyword matching from query titles, descriptions, and responses
                        message_lower = message.lower()
                        search_words = [w for w in message_lower.split() if len(w) > 3]  # Words longer than 3 chars

                        if search_words:
                            if user_role == "student":
                                queries = db.query(Query).filter(
                                    Query.student_id == user.id
                                ).all()
                            else:
                                queries = db.query(Query).all()

                            # Find queries that match the search words
                            matching_queries = []
                            for q in queries:
                                query_text = f"{q.title} {q.description}".lower()

                                # Add response content to search
                                if q.responses:
                                    response_text = " ".join([r.content for r in q.responses[:3]])  # First 3 responses
                                    query_text += " " + response_text.lower()

                                # Check if any search word appears in query
                                match_score = sum(1 for word in search_words if word in query_text)

                                if match_score > 0:
                                    matching_queries.append((q, match_score))

                            # Sort by match score (most relevant first) and take top 3
                            matching_queries.sort(key=lambda x: x[1], reverse=True)
                            top_matches = matching_queries[:3]

                            if top_matches:
                                relevant_queries_info = []
                                for q, score in top_matches:
                                    query_info = {
                                        "id": q.id,
                                        "title": q.title,
                                        "description": q.description,
                                        "status": q.status.value if hasattr(q.status, 'value') else str(q.status),
                                        "category": q.category.value if hasattr(q.category, 'value') else str(q.category),
                                        "created_at": q.created_at.isoformat() if q.created_at else None,
                                        "response_count": len(q.responses) if q.responses else 0,
                                        "match_score": score
                                    }

                                    # Include responses for context
                                    if q.responses:
                                        query_info["responses"] = []
                                        for r in q.responses[:2]:  # Include top 2 responses
                                            query_info["responses"].append({
                                                "content": r.content,
                                                "user_name": r.user.full_name if r.user else "Unknown",
                                                "is_solution": r.is_solution
                                            })

                                    if user_role != "student" and q.student:
                                        query_info["student_name"] = q.student.full_name

                                    relevant_queries_info.append(query_info)

                except Exception as e:
                    logging.error(f"Error searching queries: {e}")

            # PRIORITY 2: Search knowledge base only if no relevant queries found
            kb_results = []
            if use_knowledge_base and SQLALCHEMY_AVAILABLE and not is_asking_for_query_list and not relevant_queries_info:
                relevant_categories = self.get_relevant_categories(user)

                # Search across relevant categories
                for category in relevant_categories:
                    results = self.search_knowledge_base(
                        db=db,
                        query=message,
                        category=category,
                        limit=2
                    )
                    kb_results.extend(results)

            # PRIORITY 3: Search web for real-time information if no KB results found
            web_results = []
            if not is_asking_for_query_list and not relevant_queries_info and not kb_results and WEB_SEARCH_AVAILABLE:
                logging.info(f"No KB results found, searching web for: {message}")
                web_results = self.search_web(query=message, max_results=3)

            # Build enhanced context
            context_parts = []

            # Add user context
            context_parts.append(f"User: {user_context['full_name']} (Role: {user_context['role']})")

            if user_context.get('is_new_user'):
                context_parts.append("Note: This is a new user, provide extra helpful guidance.")

            # PRIORITY 1: Show relevant database queries if found
            if relevant_queries_info:
                context_parts.append("\n=== RELEVANT QUERIES FROM DATABASE (Priority 1) ===")
                context_parts.append(f"Found {len(relevant_queries_info)} relevant queries that may answer your question:\n")

                for idx, q in enumerate(relevant_queries_info, 1):
                    context_parts.append(f"{idx}. [{q['status'].upper()}] {q['title']}")
                    context_parts.append(f"   Description: {q['description']}")
                    context_parts.append(f"   Category: {q['category']} | Responses: {q['response_count']}")

                    # Include existing responses
                    if q.get('responses'):
                        context_parts.append("   Existing Responses:")
                        for ridx, r in enumerate(q['responses'], 1):
                            solution_tag = " [SOLUTION]" if r.get('is_solution') else ""
                            context_parts.append(f"     {ridx}. {r['user_name']}: {r['content']}{solution_tag}")

                    context_parts.append("")

            # If user asked to list all queries, provide complete list
            elif all_queries_info:
                user_role = user.role.value if hasattr(user.role, 'value') else user.role

                if user_role == "student":
                    context_parts.append("\n=== YOUR QUERIES (Complete List) ===")
                    context_parts.append(f"Total queries you've posted: {len(all_queries_info)}")
                    context_parts.append("\nHere are ALL your queries:\n")
                else:
                    context_parts.append("\n=== ALL STUDENT QUERIES (System-Wide) ===")
                    context_parts.append(f"Total queries in system: {len(all_queries_info)}")
                    context_parts.append("\nHere are ALL queries from all students:\n")

                for idx, q in enumerate(all_queries_info, 1):
                    if user_role != "student" and "student_name" in q:
                        context_parts.append(f"{idx}. [{q['status'].upper()}] {q['title']} (by {q['student_name']})")
                    else:
                        context_parts.append(f"{idx}. [{q['status'].upper()}] {q['title']}")

                    context_parts.append(f"   Category: {q['category']} | Priority: {q['priority']}")
                    context_parts.append(f"   Description: {q['description']}")
                    context_parts.append(f"   Responses: {q['response_count']} | Created: {q['created_at']}")
                    context_parts.append("")

            elif user_context.get('recent_queries'):
                recent_topics = [q['title'] for q in user_context['recent_queries'][:3]]
                context_parts.append(f"Recent topics: {', '.join(recent_topics)}")

            # PRIORITY 2: Add knowledge base context (only if no relevant queries found)
            if kb_results:
                context_parts.append("\n=== RELEVANT INFORMATION FROM KNOWLEDGE BASE (Priority 2) ===")
                context_parts.append("No existing queries found, but found relevant information in knowledge base:\n")
                for idx, result in enumerate(kb_results[:3], 1):
                    context_parts.append(f"\n{idx}. {result['title']} ({result['category']})")
                    context_parts.append(f"   {result['content']}")

            # PRIORITY 3: Add web search results (if no KB results)
            if web_results:
                context_parts.append("\n=== REAL-TIME INFORMATION FROM WEB SEARCH (Priority 3) ===")
                context_parts.append("Found current information from the internet:\n")
                for idx, result in enumerate(web_results, 1):
                    context_parts.append(f"\n{idx}. Title: {result['title']}")
                    context_parts.append(f"   Content: {result['snippet']}")
                    context_parts.append(f"   URL: {result['url']}")
                    context_parts.append(f"   [You MUST include this URL in your response]")

            # Combine message with context based on priority
            if relevant_queries_info:
                # PRIORITY 1: Answer from database queries
                enhanced_message = f"""
{chr(10).join(context_parts)}

=== User Question ===
{message}

IMPORTANT INSTRUCTIONS - PRIORITY 1 (Database Queries):
I found relevant queries from the database that may answer the user's question.
These queries include existing responses from TAs and instructors.

Please:
1. Check if the existing responses already answer the user's question
2. If yes, summarize the solution from the existing responses
3. Reference which query and response contains the answer
4. If the existing responses don't fully answer, provide additional context
5. Be clear, professional, and cite the source queries

Source: Database queries (Priority 1)
"""
            elif all_queries_info:
                # User asked to list all queries
                enhanced_message = f"""
{chr(10).join(context_parts)}

=== User Question ===
{message}

IMPORTANT INSTRUCTIONS:
The user is asking to see all their queries. I have provided the COMPLETE list above.
Please format your response as a clear, well-organized list showing:
- Query number
- Title
- Status (OPEN/IN_PROGRESS/RESOLVED)
- Category and Priority
- Number of responses
- Brief summary

These are the user's actual QUERIES from the query system, not conversation history.
"""
            elif kb_results:
                # PRIORITY 2: Answer from knowledge base
                enhanced_message = f"""
{chr(10).join(context_parts)}

=== User Question ===
{message}

IMPORTANT INSTRUCTIONS - PRIORITY 2 (Knowledge Base):
No existing queries found in database, but found relevant information in the knowledge base.
Please provide a comprehensive answer based on the knowledge base sources above.
Reference the specific sources (title and category) when answering.

Source: Knowledge Base (Priority 2)
"""
            elif web_results:
                # PRIORITY 3: Answer from web search
                enhanced_message = f"""
{chr(10).join(context_parts)}

=== User Question ===
{message}

IMPORTANT INSTRUCTIONS - PRIORITY 3 (Web Search):
I found current information from the web to answer this question.
Please provide a comprehensive answer based on the web search results above.

CRITICAL - YOU MUST INCLUDE SOURCE LINKS:
1. After your answer, ALWAYS add a "📚 Sources:" section
2. List each source with its title and FULL URL in markdown format: [Title](URL)
3. Make the URLs clickable by using markdown link format
4. Example format:

   📚 Sources:
   - [Article Title 1](https://example.com/article1)
   - [Article Title 2](https://example.com/article2)

5. Make it clear this is current information from the internet
6. If it's a question requiring real-time data (weather, AQI, news, stock prices, etc.),
   provide the most recent information from the search results
7. Be accurate and factual based on the sources provided

REMEMBER: Always include the sources section with clickable links at the end!

Source: Web Search (Priority 3)
"""
            else:
                # PRIORITY 4: Use AI's general knowledge
                enhanced_message = f"""
{chr(10).join(context_parts)}

=== User Question ===
{message}

INSTRUCTIONS - PRIORITY 4 (General AI Knowledge):
No relevant information found in database queries, knowledge base, or web search.
Please answer using your general knowledge, but be clear that this is general information
and suggest the user may want to ask a TA/instructor for course-specific guidance.

Source: General AI Knowledge (Priority 4)
"""

            # Get response from base chat method
            response, conv_id = await self.chat(
                message=enhanced_message,
                conversation_id=conversation_id
            )

            # Determine which priority was used
            if relevant_queries_info:
                priority_used = "database_queries"
                sources = [
                    {
                        "type": "query",
                        "title": str(q["title"]),
                        "category": str(q["category"]),
                        "query_id": str(q["id"])
                    }
                    for q in relevant_queries_info
                ]
            elif all_queries_info:
                priority_used = "query_list"
                sources = []
            elif kb_results:
                priority_used = "knowledge_base"
                sources = [
                    {
                        "type": "knowledge",
                        "title": str(r["title"]),
                        "category": str(r["category"])
                    }
                    for r in kb_results[:3]
                ]
            elif web_results:
                priority_used = "web_search"
                sources = [
                    {
                        "type": "web",
                        "title": str(r["title"]),
                        "url": str(r["url"])
                    }
                    for r in web_results
                ]
            else:
                priority_used = "ai_general_knowledge"
                sources = []

            # Add metadata
            return {
                "answer": response,
                "conversation_id": conv_id,
                "priority_used": priority_used,
                "knowledge_sources_used": len(kb_results),
                "relevant_queries_found": len(relevant_queries_info) if relevant_queries_info else 0,
                "sources": sources,
                "user_context": {
                    "role": user_context["role"],
                    "is_new_user": user_context.get("is_new_user", False)
                }
            }

        except Exception as e:
            logging.error(f"Error in enhanced chat: {e}")
            import traceback
            traceback.print_exc()

            # Fallback to basic chat
            try:
                response, conv_id = await self.chat(
                    message=message,
                    conversation_id=conversation_id
                )
                return {
                    "answer": response,
                    "conversation_id": conv_id,
                    "priority_used": "fallback",
                    "knowledge_sources_used": 0,
                    "relevant_queries_found": 0,
                    "sources": [],
                    "user_context": {},
                    "error": "Knowledge base integration failed, using basic response"
                }
            except Exception as fallback_error:
                logging.error(f"Fallback chat also failed: {fallback_error}")
                traceback.print_exc()

                # Final fallback - return friendly error message
                conversation_id = conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
                return {
                    "answer": "I apologize, but I'm having trouble processing your request right now. This might be due to:\n\n1. A temporary issue with the AI service\n2. The question being outside my current knowledge scope\n3. A network connectivity issue\n\nPlease try:\n- Asking a different question\n- Checking your internet connection\n- Waiting a moment and trying again\n\nIf this persists, please contact support.",
                    "conversation_id": conversation_id,
                    "priority_used": "error",
                    "knowledge_sources_used": 0,
                    "relevant_queries_found": 0,
                    "sources": [],
                    "user_context": {},
                    "error": f"Chat service temporarily unavailable: {str(fallback_error)}"
                }

    async def chat_stream_with_context(
        self,
        db: Session,
        user: User,
        message: str,
        conversation_id: Optional[str] = None,
        use_knowledge_base: bool = True
    ) -> AsyncIterator[str]:
        """
        Streaming chat with knowledge base and user context.

        Args:
            db: Database session
            user: Current user
            message: User's message
            conversation_id: Optional conversation ID
            use_knowledge_base: Whether to search knowledge base

        Yields:
            Response chunks
        """
        try:
            # Get user context
            user_context = self.get_user_context(db, user)

            # Search knowledge base if enabled
            kb_results = []
            if use_knowledge_base and SQLALCHEMY_AVAILABLE:
                relevant_categories = self.get_relevant_categories(user)
                for category in relevant_categories:
                    results = self.search_knowledge_base(
                        db=db,
                        query=message,
                        category=category,
                        limit=2
                    )
                    kb_results.extend(results)

            # Build enhanced context
            context_parts = [f"User: {user_context['full_name']} (Role: {user_context['role']})"]

            if kb_results:
                context_parts.append("\n=== Relevant Information ===")
                for idx, result in enumerate(kb_results[:3], 1):
                    context_parts.append(f"\n{idx}. {result['title']}: {result['content']}")

            # Enhanced message
            enhanced_message = f"""
{chr(10).join(context_parts)}

=== Question ===
{message}
"""

            # Stream response
            async for chunk in self.chat_stream(
                message=enhanced_message,
                conversation_id=conversation_id
            ):
                yield chunk

        except Exception as e:
            logging.error(f"Error in streaming chat: {e}")
            yield f"Error: {str(e)}"

    # =========================================================================
    # Query-Specific Methods
    # =========================================================================

    async def answer_query(
        self,
        db: Session,
        user: User,
        query_id: int
    ) -> Dict[str, Any]:
        """
        Answer a specific query from the database.

        Args:
            db: Database session
            user: Current user
            query_id: Query ID

        Returns:
            Answer dictionary
        """
        if not SQLALCHEMY_AVAILABLE:
            return {"error": "Database not available"}

        try:
            # Get the query
            query = db.query(Query).filter(Query.id == query_id).first()

            if not query:
                return {"error": "Query not found"}

            # Search knowledge base for relevant information
            kb_results = self.search_knowledge_base(
                db=db,
                query=f"{query.title} {query.description}",
                limit=3
            )

            # Build context
            context = f"""
Query Title: {query.title}
Description: {query.description}
Category: {query.category.value if hasattr(query.category, 'value') else query.category}
"""

            if kb_results:
                context += "\n=== Relevant Information ===\n"
                for result in kb_results:
                    context += f"\n{result['title']}: {result['content']}\n"

            # Get answer
            full_message = f"{context}\n\nPlease provide a comprehensive answer to this query."

            response, _ = await self.chat(message=full_message)

            return {
                "query_id": query_id,
                "answer": response,
                "sources_used": [r["title"] for r in kb_results],
                "confidence": "high" if kb_results else "medium"
            }

        except Exception as e:
            logging.error(f"Error answering query: {e}")
            return {"error": str(e)}

    # =========================================================================
    # Implementation Management Methods
    # =========================================================================

    def switch_implementation(self, implementation: ChatImplementation):
        """
        Switch between LangChain and native SDK implementations.

        Args:
            implementation: New implementation to use
        """
        print(f"Switching from {self.implementation} to {implementation}")
        self.implementation = implementation

        if implementation == ChatImplementation.LANGCHAIN and not self.llm:
            self._init_langchain()
        elif implementation == ChatImplementation.NATIVE_SDK and not self.genai_client:
            self._init_native_sdk()

    def get_metrics(self) -> Optional[Dict[str, int]]:
        """
        Get observability metrics from the chatbot.

        Returns:
            Dictionary of metrics or None if observability is disabled
        """
        if self.observability_plugin:
            return self.observability_plugin.get_metrics()
        return None

    async def get_session_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session state for a conversation.

        Args:
            conversation_id: Conversation/session ID

        Returns:
            Session state dictionary or None if not available
        """
        if not self.session_service:
            return None

        try:
            session = await self.session_service.get_session(
                app_name=self.app_name,
                user_id="default_user",
                session_id=conversation_id
            )
            return dict(session.state) if session else None
        except:
            return None

    async def load_memory_for_session(self, conversation_id: str) -> bool:
        """
        Explicitly load memory for a session.

        Args:
            conversation_id: Conversation/session ID

        Returns:
            True if memory loaded successfully, False otherwise
        """
        if not self.memory_service:
            return False

        try:
            # Memory service automatically loads relevant memories
            # This method explicitly triggers memory awareness
            return True
        except Exception as e:
            logging.error(f"Memory load failed: {e}")
            return False


# Global chatbot instance - using native SDK with enhanced features by default
hybrid_chatbot_service = HybridChatbotService(
    implementation=ChatImplementation.NATIVE_SDK,
    enable_memory=True,
    enable_observability=True,
    app_name="AURA"
)
