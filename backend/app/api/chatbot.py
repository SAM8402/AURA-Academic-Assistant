"""
Chatbot API endpoints with streaming support.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.db import get_db
from app.models.user import User
from app.models.chat_session import ChatSession
from app.schemas.chatbot_schema import ChatRequest, ChatResponse, ChatMode
from app.api.dependencies import get_current_user
from app.services.chatbot_service_hybrid import hybrid_chatbot_service as chatbot_service
from datetime import datetime, UTC
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import traceback
import logging


def get_user_previous_conversations(
    db: Session,
    user: User,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get summaries of user's previous conversations from chat_sessions.

    Args:
        db: Database session
        user: Current user
        limit: Maximum number of previous sessions to fetch

    Returns:
        List of previous conversation summaries
    """
    previous_conversations = []

    try:
        # Get all chat sessions for this user
        all_sessions = db.query(ChatSession).order_by(
            ChatSession.updated_at.desc()
        ).all()

        for session in all_sessions:
            if session.metadata_:
                session_user_id = session.metadata_.get("user_id")
                session_user_email = session.metadata_.get("user_email")

                # Check if this session belongs to the current user
                if session_user_id == user.id or session_user_email == user.email:
                    summary = session.metadata_.get("summary", "")
                    messages = session.metadata_.get("messages", [])
                    message_count = session.metadata_.get("message_count", 0)

                    if summary or messages:  # Only include sessions with content
                        previous_conversations.append({
                            "conversation_id": session.metadata_.get("conversation_id", "unknown"),
                            "summary": summary,
                            "message_count": message_count,
                            "started_at": session.metadata_.get("started_at", ""),
                            "last_message_at": session.metadata_.get("last_message_at", ""),
                            "recent_topics": [
                                msg.get("content", "")[:100]
                                for msg in messages[-4:]
                                if msg.get("role") == "user"
                            ]
                        })

                    if len(previous_conversations) >= limit:
                        break

    except Exception as e:
        logging.warning(f"Error fetching previous conversations: {e}")

    return previous_conversations


def build_personalization_context(previous_conversations: List[Dict[str, Any]]) -> str:
    """
    Build personalization context string from previous conversations.

    Args:
        previous_conversations: List of previous conversation data

    Returns:
        Formatted context string for LLM
    """
    if not previous_conversations:
        return ""

    context_parts = [
        "\n=== USER'S PREVIOUS CONVERSATION HISTORY ===",
        f"This user has {len(previous_conversations)} previous chat sessions with you.",
        "Here are summaries of their past conversations:\n"
    ]

    for idx, conv in enumerate(previous_conversations[:5], 1):  # Limit to 5 for context length
        context_parts.append(f"Session {idx}:")
        if conv.get("summary"):
            context_parts.append(f"  Summary: {conv['summary']}")
        if conv.get("recent_topics"):
            context_parts.append(f"  Topics discussed: {', '.join(conv['recent_topics'][:3])}")
        if conv.get("message_count"):
            context_parts.append(f"  Messages exchanged: {conv['message_count']}")
        context_parts.append("")

    context_parts.append(
        "Use this history to personalize your responses. "
        "Reference past discussions when relevant. "
        "Remember the user's interests and learning patterns.\n"
    )

    return "\n".join(context_parts)


def get_or_create_chat_session(
    db: Session,
    user: User,
    conversation_id: Optional[str],
    request: Request = None
) -> ChatSession:
    """
    Get existing chat session for a conversation or create a new one.

    - Same user + same conversation_id = return existing session
    - Same user + new/different conversation_id = create new session
    - Each session stores conversation summary in metadata

    Args:
        db: Database session
        user: Current user
        conversation_id: Conversation ID to track
        request: FastAPI request object for IP/device info

    Returns:
        ChatSession object
    """
    # If we have a conversation_id, try to find existing session for it
    if conversation_id:
        try:
            all_sessions = db.query(ChatSession).order_by(
                ChatSession.updated_at.desc()
            ).all()

            for session in all_sessions:
                if session.metadata_:
                    session_conv_id = session.metadata_.get("conversation_id")
                    session_user_id = session.metadata_.get("user_id")

                    # Found existing session for this conversation and user
                    if session_conv_id == conversation_id and session_user_id == user.id:
                        return session

        except Exception as e:
            logging.warning(f"Error searching for existing chat session: {e}")

    # Create new session for this conversation
    ip_address = None
    device_info = None

    if request:
        ip_address = request.client.host if request.client else None
        device_info = request.headers.get("user-agent", "")[:500]

    session_metadata = {
        "user_id": user.id,
        "user_email": user.email,
        "user_role": user.role.value if hasattr(user.role, 'value') else str(user.role),
        "conversation_id": conversation_id,
        "started_at": datetime.now(UTC).isoformat(),
        "message_count": 0,
        "messages": [],  # Store conversation messages
        "summary": ""    # Will store conversation summary
    }

    new_session = ChatSession(
        ip_address=ip_address,
        device_info=device_info,
        language="en",
        metadata_=session_metadata
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    logging.info(f"New chat session created for user: {user.email}, conversation: {conversation_id}")
    return new_session


def update_chat_session_with_message(
    db: Session,
    session: ChatSession,
    user_message: str,
    ai_response: str,
    conversation_id: str = None
):
    """
    Update chat session with new message and generate summary.

    Args:
        db: Database session
        session: ChatSession to update
        user_message: User's message
        ai_response: AI's response
        conversation_id: Conversation ID
    """
    try:
        current_metadata = session.metadata_ or {}

        # Update message count
        message_count = current_metadata.get("message_count", 0) + 1
        current_metadata["message_count"] = message_count

        # Store messages (keep last 10 for summary)
        messages = current_metadata.get("messages", [])
        messages.append({
            "role": "user",
            "content": user_message[:500],  # Truncate long messages
            "timestamp": datetime.now(UTC).isoformat()
        })
        messages.append({
            "role": "assistant",
            "content": ai_response[:500],  # Truncate long responses
            "timestamp": datetime.now(UTC).isoformat()
        })
        # Keep only last 20 messages (10 exchanges)
        current_metadata["messages"] = messages[-20:]

        # Generate conversation summary
        summary_parts = []
        for msg in messages[-6:]:  # Last 3 exchanges for summary
            if msg["role"] == "user":
                summary_parts.append(f"Q: {msg['content'][:100]}")

        current_metadata["summary"] = " | ".join(summary_parts) if summary_parts else "Conversation started"
        current_metadata["last_message_at"] = datetime.now(UTC).isoformat()

        if conversation_id:
            current_metadata["conversation_id"] = conversation_id

        session.metadata_ = current_metadata
        session.updated_at = datetime.now(UTC)

        # Tell SQLAlchemy that the JSON field has been modified
        flag_modified(session, "metadata_")

        db.commit()
        logging.info(f"Chat session updated: {message_count} messages for conversation {conversation_id}")
    except Exception as e:
        logging.error(f"Failed to update chat session: {e}")
        db.rollback()


chatbot_router = APIRouter(tags=["Chatbot"])


@chatbot_router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with AI assistant",
    description="""
    Send a message to the AI chatbot and get a response.

    **Features:**
    - Conversation memory (maintains context)
    - Multiple chat modes (academic, general, study help, doubt clarification)
    - Powered by Google Gemini AI
    - Automatically saves chat session to database

    **Example:**
    ```json
    {
      "message": "Explain binary search algorithm",
      "mode": "academic",
      "conversation_id": "conv-abc123"
    }
    ```
    """
)
async def chat(
    chat_request: ChatRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chat with AI assistant.

    Requires authentication.
    """
    try:
        # Get user's previous conversation history for personalization
        previous_conversations = get_user_previous_conversations(
            db=db,
            user=current_user,
            limit=5
        )

        # Build personalization context
        personalization_context = build_personalization_context(previous_conversations)

        # Enhance message with personalization context if user has history
        enhanced_message = chat_request.message
        if personalization_context:
            enhanced_message = f"""{personalization_context}

=== Current Message ===
{chat_request.message}

Remember to personalize your response based on the user's conversation history above."""

        # Generate response
        response, conv_id = await chatbot_service.chat(
            message=enhanced_message,
            conversation_id=chat_request.conversation_id,
            mode=chat_request.mode
        )

        # Get or create chat session for this conversation
        # New conversation = new session, same conversation = same session
        chat_session = get_or_create_chat_session(
            db=db,
            user=current_user,
            conversation_id=conv_id,
            request=http_request
        )

        # Update session with message and summary
        update_chat_session_with_message(
            db=db,
            session=chat_session,
            user_message=chat_request.message,  # Store original message, not enhanced
            ai_response=response,
            conversation_id=conv_id
        )

        return ChatResponse(
            response=response,
            conversation_id=conv_id,
            model=chatbot_service.llm.model if chatbot_service.llm else "fallback",
            timestamp=datetime.now(UTC)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat service temporarily unavailable"
        )


@chatbot_router.post(
    "/chat/stream",
    summary="Stream chat response",
    description="""
    Send a message and get a streaming response (real-time).

    **Features:**
    - Real-time streaming responses
    - See AI typing in real-time
    - Better UX for long responses

    **Response:** Server-Sent Events (SSE) stream
    """
)
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Stream chat response in real-time.

    Returns Server-Sent Events (SSE) stream.
    """
    async def generate():
        try:
            async for chunk in chatbot_service.chat_stream(
                message=request.message,
                conversation_id=request.conversation_id,
                mode=request.mode
            ):
                yield f"data: {chunk}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@chatbot_router.delete(
    "/conversation/{conversation_id}",
    summary="Clear conversation history",
    description="Delete conversation history for a specific conversation ID."
)
async def clear_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Clear conversation history."""
    success = chatbot_service.clear_conversation(conversation_id)

    if success:
        return {"message": "Conversation cleared successfully", "conversation_id": conversation_id}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )


@chatbot_router.get(
    "/conversation/{conversation_id}/history",
    summary="Get conversation history",
    description="Retrieve the message history for a conversation."
)
async def get_conversation_history(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get conversation history."""
    history = chatbot_service.get_conversation_history(conversation_id)

    if not history:
        return {"conversation_id": conversation_id, "messages": [], "total": 0}

    messages = []
    for msg in history:
        messages.append({
            "role": msg.type,  # 'human' or 'ai'
            "content": msg.content,
        })

    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "total": len(messages)
    }


@chatbot_router.get(
    "/status",
    summary="Get chatbot status",
    description="Check if chatbot is configured and ready."
)
async def get_chatbot_status():
    """Get chatbot configuration status."""
    from app.core.config import settings

    # Check if any implementation is available
    is_configured = (
        chatbot_service.llm is not None or
        chatbot_service.genai_client is not None or
        chatbot_service.adk_runner is not None
    )

    # Get model name
    model_name = None
    if chatbot_service.llm and hasattr(chatbot_service.llm, 'model'):
        model_name = chatbot_service.llm.model
    else:
        model_name = settings.GEMINI_MODEL

    # Get implementation info
    impl_info = {
        "implementation": chatbot_service.implementation.value,
        "adk_runner": chatbot_service.adk_runner is not None,
        "session_service": chatbot_service.session_service is not None,
        "memory_service": chatbot_service.memory_service is not None,
        "observability": chatbot_service.observability_plugin is not None
    }

    return {
        "configured": is_configured,
        "model": model_name,
        "available_modes": [mode.value for mode in ChatMode],
        "features": impl_info,
        "message": "Chatbot ready with enhanced features" if is_configured else "Configure GOOGLE_API_KEY in .env"
    }


@chatbot_router.get(
    "/metrics",
    summary="Get chatbot metrics",
    description="Get observability metrics (agent invocations, LLM requests, etc.)"
)
async def get_chatbot_metrics(
    current_user: User = Depends(get_current_user)
):
    """Get chatbot observability metrics."""
    metrics = chatbot_service.get_metrics()

    if metrics:
        return {
            "metrics": metrics,
            "message": "Metrics retrieved successfully"
        }
    else:
        return {
            "metrics": None,
            "message": "Observability not enabled or not available"
        }


@chatbot_router.get(
    "/conversation/{conversation_id}/state",
    summary="Get conversation session state",
    description="Retrieve the session state for a conversation (user context, preferences, etc.)"
)
async def get_conversation_state(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get session state for a conversation."""
    state = await chatbot_service.get_session_state(conversation_id)

    if state:
        return {
            "conversation_id": conversation_id,
            "state": state,
            "message": "Session state retrieved successfully"
        }
    else:
        return {
            "conversation_id": conversation_id,
            "state": {},
            "message": "No session state found or session service not available"
        }

# ============================================================================
# Enhanced Chatbot Endpoints with Knowledge Base Integration
# ============================================================================


class EnhancedChatRequest(BaseModel):
    """Request model for enhanced chat with knowledge base."""
    message: str
    conversation_id: Optional[str] = None
    use_knowledge_base: bool = True
    mode: Optional[ChatMode] = ChatMode.ACADEMIC


class EnhancedChatResponse(BaseModel):
    """Response model for enhanced chat."""
    answer: str
    conversation_id: str
    knowledge_sources_used: int
    sources: List[Dict[str, str]]
    user_context: Dict[str, Any]
    timestamp: str


@chatbot_router.post(
    "/chat/enhanced",
    response_model=EnhancedChatResponse,
    summary="Enhanced chat with knowledge base integration",
    description="""
    Chat with AI assistant that integrates:
    - Knowledge base search for accurate, sourced information
    - User context (role, history, previous queries)
    - Personalized responses based on user profile
    - Automatically saves chat session to database

    **Features:**
    - Retrieval Augmented Generation (RAG) using knowledge base
    - Context-aware responses
    - Source citations
    - Role-based personalization
    """
)
async def chat_enhanced(
    enhanced_request: EnhancedChatRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enhanced chat with knowledge base and context integration.

    This endpoint searches the knowledge base for relevant information
    and provides context-aware responses personalized to the user.
    It also includes the user's previous conversation history for personalization.
    """
    try:
        # Get user's previous conversation history for personalization
        previous_conversations = get_user_previous_conversations(
            db=db,
            user=current_user,
            limit=5
        )

        # Build personalization context from previous conversations
        personalization_context = build_personalization_context(previous_conversations)

        # Enhance message with personalization context
        enhanced_message = enhanced_request.message
        if personalization_context:
            enhanced_message = f"""{personalization_context}

=== Current Question ===
{enhanced_request.message}"""

        response = await chatbot_service.chat_with_context(
            db=db,
            user=current_user,
            message=enhanced_message,
            conversation_id=enhanced_request.conversation_id,
            use_knowledge_base=enhanced_request.use_knowledge_base
        )

        # Validate response structure
        if not isinstance(response, dict):
            raise ValueError(f"Service returned invalid response type: {type(response)}")

        if "answer" not in response:
            raise ValueError("Service response missing 'answer' field")

        if "conversation_id" not in response:
            raise ValueError("Service response missing 'conversation_id' field")

        conv_id = response["conversation_id"]

        # Get or create chat session for this conversation
        # New conversation = new session, same conversation = same session
        chat_session = get_or_create_chat_session(
            db=db,
            user=current_user,
            conversation_id=conv_id,
            request=http_request
        )

        # Update session with message and summary
        update_chat_session_with_message(
            db=db,
            session=chat_session,
            user_message=enhanced_request.message,
            ai_response=response["answer"],
            conversation_id=conv_id
        )

        return EnhancedChatResponse(
            answer=response["answer"],
            conversation_id=conv_id,
            knowledge_sources_used=response.get("knowledge_sources_used", 0),
            sources=response.get("sources", []),
            user_context=response.get("user_context", {}),
            timestamp=datetime.now(UTC).isoformat()
        )

    except Exception as e:
        # Log the full error
        print(f"ERROR in chat_enhanced: {e}")
        traceback.print_exc()

        # Return a friendly error response instead of 500
        conversation_id = enhanced_request.conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
        return EnhancedChatResponse(
            answer="I apologize, but I'm having trouble processing your request right now. Please try asking a different question or try again in a moment.",
            conversation_id=conversation_id,
            knowledge_sources_used=0,
            sources=[],
            user_context={},
            timestamp=datetime.now(UTC).isoformat()
        )


@chatbot_router.post(
    "/chat/enhanced/stream",
    summary="Enhanced streaming chat with knowledge base",
    description="""
    Streaming version of enhanced chat with knowledge base integration.

    Returns Server-Sent Events (SSE) for real-time response streaming.
    """
)
async def chat_enhanced_stream(
    request: EnhancedChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enhanced streaming chat with knowledge base."""
    async def generate():
        try:
            async for chunk in chatbot_service.chat_stream_with_context(
                db=db,
                user=current_user,
                message=request.message,
                conversation_id=request.conversation_id,
                use_knowledge_base=request.use_knowledge_base
            ):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@chatbot_router.get(
    "/search-knowledge",
    summary="Search knowledge base",
    description="""
    Search the knowledge base for relevant information.

    This endpoint allows direct search of the knowledge base
    without going through the chatbot.
    """
)
async def search_knowledge(
    query: str,
    category: Optional[str] = None,
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search knowledge base directly."""
    try:
        from app.models.enums import CategoryEnum

        # Convert category string to enum if provided
        category_enum = None
        if category:
            try:
                category_enum = CategoryEnum(category)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category: {category}"
                )

        results = chatbot_service.search_knowledge_base(
            db=db,
            query=query,
            category=category_enum,
            limit=limit
        )

        return {
            "query": query,
            "results_count": len(results),
            "results": results,
            "message": f"Found {len(results)} relevant knowledge sources"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Knowledge search failed: {str(e)}"
        )


@chatbot_router.post(
    "/answer-query/{query_id}",
    summary="Answer a specific query using AI and knowledge base",
    description="""
    Generate an AI answer for a specific query from the database.

    Uses knowledge base and context to provide comprehensive answers.
    """
)
async def answer_query(
    query_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Answer a specific query using enhanced chatbot."""
    try:
        response = await chatbot_service.answer_query(
            db=db,
            user=current_user,
            query_id=query_id
        )

        if "error" in response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=response["error"]
            )

        return {
            "query_id": query_id,
            "answer": response["answer"],
            "sources_used": response.get("sources_used", []),
            "confidence": response.get("confidence", "medium"),
            "timestamp": datetime.now(UTC).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query answering failed: {str(e)}"
        )


@chatbot_router.get(
    "/user-context",
    summary="Get user context for chatbot personalization",
    description="""
    Retrieve the user context that the chatbot uses for personalization.

    Includes:
    - User profile information
    - Recent queries
    - Active tasks
    - Usage statistics
    """
)
async def get_user_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user context for chatbot."""
    try:
        context = chatbot_service.get_user_context(db, current_user)

        return {
            "user_context": context,
            "relevant_categories": [
                cat.value for cat in chatbot_service.get_relevant_categories(current_user)
            ],
            "message": "User context retrieved successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user context: {str(e)}"
        )
