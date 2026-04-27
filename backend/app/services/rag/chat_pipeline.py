"""
Chat RAG Pipeline for AURA.

Adapted from nexora/backend/pipelines/chat.py.
Provides RAG-enhanced chat: embed query → search KB → generate response with context.

Pipeline steps (LangGraph nodes):
1. Validate input
2. Generate query embedding
3. Search knowledge base
4. Generate response with Gemini using retrieved context
5. Store query record
"""

from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
from uuid import UUID
import logging
import os

from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session
import requests

from config.db import SessionLocal
from config.settings import settings
from app.services.rag.embedding_service import generate_embedding
from app.services.rag.search_pipeline import semantic_search_sqlite

logger = logging.getLogger(__name__)

# Configuration
LLM_MODEL = os.getenv("LLM_MODEL", settings.GEMINI_MODEL)
SIMILARITY_THRESHOLD = 0.35
DEFAULT_TOP_K = 5
TIMEOUT_SECONDS = 30


# ============================================================================
# STATE DEFINITION
# ============================================================================

class ChatRAGState(TypedDict, total=False):
    """Graph state for RAG chat pipeline."""
    # Input
    input_text: str
    user_name: Optional[str]
    user_role: Optional[str]
    conversation_id: Optional[str]

    # Search and retrieval
    query_embedding: Optional[List[float]]
    search_results: Optional[List[Dict[str, Any]]]
    relevant_chunks: Optional[List[Dict[str, Any]]]
    has_relevant_context: Optional[bool]
    similarity_score: Optional[float]

    # Response generation
    answer_text: Optional[str]
    confidence: Optional[float]
    sources: Optional[List[Dict[str, str]]]

    # Error handling
    error: Optional[str]
    status: Optional[str]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def call_gemini_llm(prompt: str, context: str) -> Dict[str, Any]:
    """
    Call Gemini API for response generation with RAG context.

    Args:
        prompt: User question
        context: Retrieved knowledge context

    Returns:
        Response dictionary with answer and metadata
    """
    api_key = settings.GOOGLE_API_KEY
    if not api_key:
        logger.error("No Google API key available")
        return {"error": "API key not available"}

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{LLM_MODEL}:generateContent"
    )

    full_prompt = f"""You are AURA (Academic Unified Response Assistant), an AI assistant for students.
Provide helpful, accurate, and concise answers based on the context provided.

Context from Knowledge Base:
{context}

Student Question: {prompt}

Instructions:
1. Answer based on the provided context when available
2. If the context doesn't contain relevant information, say so clearly but still try to help
3. Be concise but comprehensive
4. Use a helpful, encouraging, and educational tone
5. Format your response clearly with markdown when appropriate
6. If referencing specific sources, mention them

Response:"""

    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048,
            "topP": 0.8,
            "topK": 40
        }
    }

    try:
        response = requests.post(
            f"{endpoint}?key={api_key}",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT_SECONDS
        )

        if response.status_code == 200:
            result = response.json()
            candidates = result.get("candidates", [])
            if candidates and candidates[0].get("content", {}).get("parts"):
                answer_text = candidates[0]["content"]["parts"][0]["text"].strip()
                confidence = _calculate_confidence(answer_text, context)

                return {
                    "answer": answer_text,
                    "confidence": confidence,
                    "token_usage": result.get("usageMetadata", {}),
                    "success": True
                }
        else:
            logger.error("Gemini LLM API error: %d - %s", response.status_code, response.text)
            return {"error": f"API error: {response.status_code}"}

    except Exception as e:
        logger.error("Error calling Gemini LLM API: %s", e)
        return {"error": str(e)}


def _calculate_confidence(answer: str, context: str) -> float:
    """Calculate confidence score based on response quality."""
    if not answer or "I don't have information" in answer:
        return 0.2
    if len(answer) < 20:
        return 0.4
    elif len(answer) < 50:
        return 0.6
    elif any(phrase in answer.lower() for phrase in ["based on", "according to", "the context"]):
        return 0.9
    else:
        return 0.7


# ============================================================================
# PIPELINE NODES
# ============================================================================

def validate_input(state: ChatRAGState) -> ChatRAGState:
    """Node 1: Validate input text."""
    try:
        input_text = state.get("input_text", "")

        if not input_text or len(input_text.strip()) == 0:
            state["error"] = "Input text cannot be empty"
            state["status"] = "failed"
            state["answer_text"] = "Please provide a valid question."
            state["confidence"] = 0.0
            return state

        if len(input_text.split()) < 2:
            state["error"] = "Input too short"
            state["status"] = "failed"
            state["answer_text"] = "Please provide a more detailed question."
            state["confidence"] = 0.0
            return state

        state["status"] = "validated"
        logger.info("Validated input: '%s...'", input_text[:50])
        return state

    except Exception as e:
        logger.error("Error in validation: %s", str(e))
        state["error"] = str(e)
        state["status"] = "failed"
        return state


def generate_query_embedding_node(state: ChatRAGState) -> ChatRAGState:
    """Node 2: Generate embedding for the query."""
    if state.get("error"):
        return state

    try:
        query_text = state["input_text"]
        logger.info("Generating embedding for: '%s'", query_text)

        embedding = generate_embedding(query_text)

        if not embedding:
            state["error"] = "Failed to generate query embedding"
            state["status"] = "failed"
            return state

        state["query_embedding"] = embedding
        state["status"] = "embedding_generated"
        logger.info("Generated embedding (dim=%d) for query", len(embedding))

        return state

    except Exception as e:
        logger.error("Error generating embedding: %s", str(e))
        state["error"] = str(e)
        state["status"] = "failed"
        return state


def search_knowledge_base(state: ChatRAGState) -> ChatRAGState:
    """Node 3: Search knowledge base using semantic similarity."""
    if state.get("error"):
        return state

    session = SessionLocal()
    try:
        embedding = state["query_embedding"]

        search_results = semantic_search_sqlite(
            session=session,
            query_embedding=embedding,
            top_k=DEFAULT_TOP_K,
            filters={}
        )

        if search_results is None:
            search_results = []

        state["search_results"] = search_results

        # Filter by similarity threshold
        relevant_chunks = []
        max_similarity = 0.0

        for result in search_results:
            score = result.get("score", 0.0)
            if score >= SIMILARITY_THRESHOLD:
                relevant_chunks.append(result)
                max_similarity = max(max_similarity, score)

        state["relevant_chunks"] = relevant_chunks
        state["similarity_score"] = max_similarity
        state["has_relevant_context"] = len(relevant_chunks) > 0
        state["status"] = "search_completed"

        logger.info(
            "Found %d relevant chunks (max similarity: %.3f)",
            len(relevant_chunks), max_similarity
        )

        return state

    except Exception as e:
        logger.error("Error in knowledge search: %s", str(e))
        state["error"] = str(e)
        state["status"] = "failed"
        return state
    finally:
        session.close()


def generate_response(state: ChatRAGState) -> ChatRAGState:
    """Node 4: Generate response using Gemini with RAG context."""
    if state.get("error"):
        return state

    try:
        query_text = state["input_text"]
        relevant_chunks = state.get("relevant_chunks", [])

        if not state.get("has_relevant_context"):
            # No relevant context - still generate a response but note it
            context = "No specific information found in the knowledge base for this query."
        else:
            # Build context from relevant chunks
            context_parts = []
            for chunk in relevant_chunks[:3]:  # Top 3 chunks
                source_title = chunk.get("source_title", "Unknown Source")
                content = chunk.get("content", "")
                score = chunk.get("score", 0.0)
                if content:
                    context_parts.append(
                        f"Source: {source_title} (relevance: {score:.2f})\n"
                        f"Content: {content}"
                    )
            context = "\n\n".join(context_parts)

        # Generate response using Gemini
        llm_result = call_gemini_llm(query_text, context)

        if llm_result.get("error"):
            state["error"] = llm_result["error"]
            state["status"] = "llm_failed"
            return state

        state["answer_text"] = llm_result["answer"]
        state["confidence"] = llm_result["confidence"]

        # Build sources list
        sources = []
        for chunk in relevant_chunks[:3]:
            sources.append({
                "title": chunk.get("source_title", "Unknown"),
                "category": chunk.get("source_category", "Unknown"),
                "score": str(round(chunk.get("score", 0.0), 3))
            })
        state["sources"] = sources

        state["status"] = "response_generated"
        logger.info(
            "Generated response with confidence: %.3f",
            llm_result["confidence"]
        )

        return state

    except Exception as e:
        logger.error("Error generating response: %s", str(e))
        state["error"] = str(e)
        state["status"] = "failed"
        return state


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def build_chat_rag_graph():
    """Build and compile the RAG chat graph."""
    graph = StateGraph(ChatRAGState)

    graph.add_node("validate_input", validate_input)
    graph.add_node("generate_query_embedding", generate_query_embedding_node)
    graph.add_node("search_knowledge_base", search_knowledge_base)
    graph.add_node("generate_response", generate_response)

    graph.set_entry_point("validate_input")

    graph.add_conditional_edges(
        "validate_input",
        lambda x: "generate_query_embedding" if not x.get("error") else END,
        {
            "generate_query_embedding": "generate_query_embedding",
            END: END
        }
    )

    graph.add_edge("generate_query_embedding", "search_knowledge_base")
    graph.add_edge("search_knowledge_base", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()


# ============================================================================
# PIPELINE EXECUTION
# ============================================================================

async def chat_with_rag(
    query: str,
    user_name: Optional[str] = None,
    user_role: Optional[str] = None,
    conversation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a chat query through the RAG pipeline.

    Args:
        query: User's question
        user_name: Optional user name for personalization
        user_role: Optional user role for context
        conversation_id: Optional conversation tracking ID

    Returns:
        Response dictionary with answer, sources, and metadata
    """
    try:
        graph = build_chat_rag_graph()

        initial_state = ChatRAGState(
            input_text=query,
            user_name=user_name,
            user_role=user_role,
            conversation_id=conversation_id,
            status="pending"
        )

        logger.info("Starting RAG chat for query: '%s'", query)
        final_state = await graph.ainvoke(initial_state)

        return {
            "success": not bool(final_state.get("error")),
            "answer": final_state.get("answer_text", "I'm sorry, I couldn't process your question."),
            "confidence": final_state.get("confidence", 0.0),
            "sources": final_state.get("sources", []),
            "has_relevant_context": final_state.get("has_relevant_context", False),
            "similarity_score": final_state.get("similarity_score", 0.0),
            "status": final_state.get("status", "unknown"),
            "error": final_state.get("error")
        }

    except Exception as e:
        logger.error("RAG chat pipeline failed: %s", str(e))
        return {
            "success": False,
            "answer": "I'm sorry, I encountered an error processing your question. Please try again.",
            "confidence": 0.0,
            "sources": [],
            "has_relevant_context": False,
            "similarity_score": 0.0,
            "error": str(e)
        }
