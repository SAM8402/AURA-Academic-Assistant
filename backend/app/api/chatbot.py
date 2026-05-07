"""
Chatbot API endpoints.

This module is a thin HTTP layer — it handles request parsing, authentication,
and response formatting. All business logic lives in ChatOrchestrator.

Endpoints:
  POST /chat                    - Basic chat
  POST /chat/stream             - Streaming chat
  POST /chat/enhanced           - RAG-enhanced chat with knowledge base
  POST /chat/enhanced/stream    - Streaming RAG-enhanced chat
  POST /chat/rag                - Direct RAG pipeline chat
  GET  /chat/search-knowledge   - Search knowledge base directly
  POST /chat/answer-query/{id}  - AI-answer a specific query
  GET  /chat/status             - Service health check
  GET  /chat/user-context       - User context for personalization
  DELETE /chat/conversation/{id}       - Clear conversation
  GET    /chat/conversation/{id}/history - Get conversation history
"""

from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

import logging
import traceback
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config.db import get_db
from app.models.user import User
from app.schemas.chatbot_schema import ChatRequest, ChatResponse, ChatMode
from app.api.dependencies import get_current_user
from app.services.chatbot.base_service import chatbot_service

logger = logging.getLogger(__name__)

chatbot_router = APIRouter(tags=["Chatbot"])


# =============================================================================
# Request/Response models for enhanced endpoints
# =============================================================================

class EnhancedChatRequest(BaseModel):
    """Request model for enhanced chat with knowledge base."""
    message: str
    conversation_id: Optional[str] = None
    use_knowledge_base: bool = True
    mode: Optional[ChatMode] = ChatMode.ACADEMIC


class EnhancedChatResponse(BaseModel):
    """Response model for enhanced (agentic) chat."""
    answer: str
    conversation_id: str
    knowledge_sources_used: int
    tools_used: List[str] = []
    confidence: str = "medium"
    sources: List[Dict[str, str]] = []
    user_context: Dict[str, Any] = {}
    timestamp: str


class RAGChatRequest(BaseModel):
    """Request model for RAG-powered chat."""
    message: str
    conversation_id: Optional[str] = None


class RAGChatResponse(BaseModel):
    """Response model for RAG-powered chat."""
    answer: str
    conversation_id: Optional[str] = None
    confidence: float = 0.0
    has_relevant_context: bool = False
    similarity_score: float = 0.0
    sources: List[Dict[str, Any]] = []
    status: str = "success"
    timestamp: str = ""


# =============================================================================
# Basic Chat Endpoints
# =============================================================================

@chatbot_router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with AI assistant",
    description="Send a message to the AI chatbot and get a response.",
)
async def chat(
    chat_request: ChatRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chat with AI assistant. Requires authentication."""
    try:
        response, conv_id = await chatbot_service.chat(
            message=chat_request.message,
            conversation_id=chat_request.conversation_id,
            mode=chat_request.mode,
        )

        # Persist session
        chatbot_service.memory.save_session(
            db=db,
            user=current_user,
            conversation_id=conv_id,
            user_message=chat_request.message,
            assistant_response=response,
            ip_address=http_request.client.host if http_request.client else None,
            device_info=http_request.headers.get("user-agent", "")[:500],
        )

        return ChatResponse(
            response=response,
            conversation_id=conv_id,
            model=chatbot_service.llm.model if chatbot_service.is_configured else "unavailable",
            timestamp=datetime.now(UTC),
        )

    except Exception as e:
        logger.error("Chat endpoint error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat service temporarily unavailable",
        )


@chatbot_router.post(
    "/chat/stream",
    summary="Stream chat response",
    description="Send a message and get a streaming response (SSE).",
)
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """Stream chat response in real-time."""
    async def generate():
        try:
            async for chunk in chatbot_service.chat_stream(
                message=request.message,
                conversation_id=request.conversation_id,
                mode=request.mode,
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# =============================================================================
# Enhanced Chat Endpoints (with RAG, user context, persistent memory)
# =============================================================================

@chatbot_router.post(
    "/chat/enhanced",
    response_model=EnhancedChatResponse,
    summary="Enhanced chat with knowledge base integration",
    description="Chat with RAG, user context, and persistent memory.",
)
async def chat_enhanced(
    enhanced_request: EnhancedChatRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enhanced chat with knowledge base and context integration."""
    try:
        result = await chatbot_service.chat_with_context(
            db=db,
            user=current_user,
            message=enhanced_request.message,
            conversation_id=enhanced_request.conversation_id,
            use_knowledge_base=enhanced_request.use_knowledge_base,
            mode=enhanced_request.mode or ChatMode.ACADEMIC,
        )

        if not isinstance(result, dict) or "answer" not in result:
            raise ValueError("Invalid service response")

        return EnhancedChatResponse(
            answer=result["answer"],
            conversation_id=result["conversation_id"],
            knowledge_sources_used=result.get("knowledge_sources_used", 0),
            tools_used=result.get("tools_used", []),
            confidence=result.get("confidence", "medium"),
            sources=result.get("sources", []),
            user_context=result.get("user_context", {}),
            timestamp=datetime.now(UTC).isoformat(),
        )

    except Exception as e:
        logger.error("Enhanced chat error: %s", e, exc_info=True)
        conv_id = enhanced_request.conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
        return EnhancedChatResponse(
            answer="I apologize, but I'm having trouble processing your request. Please try again.",
            conversation_id=conv_id,
            knowledge_sources_used=0,
            sources=[],
            user_context={},
            timestamp=datetime.now(UTC).isoformat(),
        )


@chatbot_router.post(
    "/chat/enhanced/stream",
    summary="Enhanced streaming chat with knowledge base",
    description="Streaming version of enhanced chat.",
)
async def chat_enhanced_stream(
    request: EnhancedChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enhanced streaming chat with knowledge base."""
    async def generate():
        try:
            async for chunk in chatbot_service.chat_stream_with_context(
                db=db,
                user=current_user,
                message=request.message,
                conversation_id=request.conversation_id,
                use_knowledge_base=request.use_knowledge_base,
            ):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# =============================================================================
# RAG Pipeline Chat
# =============================================================================

@chatbot_router.post(
    "/chat/rag",
    response_model=RAGChatResponse,
    summary="RAG-powered chat with semantic knowledge base search",
    description="Chat using the full RAG pipeline (embedding → search → generate).",
)
async def chat_rag(
    request: RAGChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """RAG-powered chat endpoint."""
    try:
        from app.services.rag.chat_pipeline import chat_with_rag

        user_name = current_user.full_name if hasattr(current_user, "full_name") else "Student"
        user_role = current_user.role.value if hasattr(current_user.role, "value") else "student"

        result = await chat_with_rag(
            query=request.message,
            user_name=user_name,
            user_role=user_role,
            conversation_id=request.conversation_id,
        )

        return RAGChatResponse(
            answer=result.get("answer", "Sorry, I couldn't generate a response."),
            conversation_id=request.conversation_id or f"rag-{uuid.uuid4().hex[:12]}",
            confidence=result.get("confidence", 0.0),
            has_relevant_context=result.get("has_relevant_context", False),
            similarity_score=result.get("similarity_score", 0.0),
            sources=result.get("sources", []),
            status="success" if result.get("success") else "failed",
            timestamp=datetime.now(UTC).isoformat(),
        )

    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG pipeline dependencies not available",
        )
    except Exception as e:
        logger.error("RAG chat error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG chat failed: {str(e)}",
        )


# =============================================================================
# Knowledge Search
# =============================================================================

@chatbot_router.get(
    "/search-knowledge",
    summary="Search knowledge base",
    description="Search the knowledge base directly (without chatbot).",
)
async def search_knowledge(
    query: str,
    category: Optional[str] = None,
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search knowledge base directly."""
    try:
        from app.services.rag.search_pipeline import semantic_search_chroma
        from app.services.rag.embedding_service import generate_embedding
        from app.models.enums import CategoryEnum

        category_enum = None
        if category:
            try:
                category_enum = CategoryEnum(category)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category: {category}",
                )

        query_embedding = generate_embedding(query)
        if not query_embedding:
            return {"query": query, "results_count": 0, "results": [], "message": "Failed to generate embedding"}

        results = semantic_search_chroma(
            query_embedding=query_embedding,
            top_k=limit,
            filters={"category": category_enum} if category_enum else {},
        )

        formatted = [
            {
                "id": r.get("source_id", ""),
                "title": r.get("source_title", "Unknown"),
                "content": r.get("content", "")[:500],
                "category": r.get("source_category", "Unknown"),
                "score": r.get("score", 0.0),
            }
            for r in (results or [])
        ]

        return {
            "query": query,
            "results_count": len(formatted),
            "results": formatted,
            "message": f"Found {len(formatted)} relevant knowledge sources",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Knowledge search failed: {str(e)}",
        )


# =============================================================================
# Query Answering
# =============================================================================

@chatbot_router.post(
    "/answer-query/{query_id}",
    summary="Answer a specific query using AI and knowledge base",
)
async def answer_query(
    query_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Answer a specific query using enhanced chatbot."""
    try:
        response = await chatbot_service.answer_query(
            db=db, user=current_user, query_id=query_id
        )

        if "error" in response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=response["error"],
            )

        return {
            "query_id": query_id,
            "answer": response["answer"],
            "sources_used": response.get("sources_used", []),
            "confidence": response.get("confidence", "medium"),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query answering failed: {str(e)}",
        )


# =============================================================================
# Conversation Management
# =============================================================================

@chatbot_router.delete(
    "/conversation/{conversation_id}",
    summary="Clear conversation history",
)
async def clear_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
):
    """Clear conversation history."""
    success = chatbot_service.clear_conversation(conversation_id)
    if success:
        return {"message": "Conversation cleared", "conversation_id": conversation_id}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")


@chatbot_router.get(
    "/conversation/{conversation_id}/history",
    summary="Get conversation history",
)
async def get_conversation_history(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get conversation history."""
    history = chatbot_service.get_conversation_history(conversation_id)
    messages = [
        {"role": msg.get("role", "unknown"), "content": msg.get("parts", [{}])[0].get("text", "")}
        for msg in history
        if msg.get("parts")
    ]
    return {"conversation_id": conversation_id, "messages": messages, "total": len(messages)}


# =============================================================================
# Status & Context
# =============================================================================

@chatbot_router.get(
    "/status",
    summary="Get chatbot status",
)
async def get_chatbot_status():
    """Check if chatbot is configured and ready."""
    from config.settings import settings

    return {
        "configured": chatbot_service.is_configured,
        "model": chatbot_service.llm.model if chatbot_service.is_configured else None,
        "available_modes": [mode.value for mode in ChatMode],
        "message": "Chatbot ready" if chatbot_service.is_configured else "Configure GOOGLE_API_KEY in .env",
    }


@chatbot_router.get(
    "/user-context",
    summary="Get user context for chatbot personalization",
)
async def get_user_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user context for chatbot."""
    try:
        from app.services.chatbot.hybrid_service import ToolExecutor
        executor = ToolExecutor(db=db, user=current_user)
        context = executor.get_user_context()
        return {"user_context": context, "message": "User context retrieved successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user context: {str(e)}",
        )


@chatbot_router.get(
    "/metrics",
    summary="Get chatbot usage metrics",
)
async def get_chatbot_metrics(
    current_user: User = Depends(get_current_user),
):
    """Return basic chatbot usage metrics (observability)."""
    return {
        "configured": chatbot_service.is_configured,
        "model": chatbot_service.llm.model if chatbot_service.is_configured else None,
        "active_sessions": len(chatbot_service.memory._sessions),
        "max_session_turns": chatbot_service.memory._max_turns,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@chatbot_router.get(
    "/conversation/{conversation_id}/state",
    summary="Get conversation session state",
)
async def get_conversation_state(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
):
    """Return session state for a conversation."""
    history = chatbot_service.get_conversation_history(conversation_id)
    return {
        "conversation_id": conversation_id,
        "exists": len(history) > 0,
        "message_count": len(history),
        "timestamp": datetime.now(UTC).isoformat(),
    }
