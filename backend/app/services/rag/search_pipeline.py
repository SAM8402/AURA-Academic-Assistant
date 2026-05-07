"""
Semantic Search Pipeline for AURA RAG.

Adapted from nexora/backend/pipelines/search.py.
Uses LangGraph for orchestration + Gemini Embedding API for query embedding
+ cosine similarity for vector search (SQLite-compatible).

Pipeline steps (LangGraph nodes):
1. Check cache for existing results
2. Process and validate query
3. Generate query embedding with Gemini
4. Execute semantic search (in-memory cosine similarity over stored embeddings)
5. Rank and format results
6. Cache results for performance
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import json
import hashlib

from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from config.db import SessionLocal
from app.models.knowledge import KnowledgeChunk, KnowledgeSource
from app.services.rag.embedding_service import (
    generate_embedding,
    cosine_similarity
)

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_TOP_K = 10
MAX_TOP_K = 100
SIMILARITY_THRESHOLD = 0.3  # Minimum similarity score to consider relevant

# Simple in-memory cache
SEARCH_CACHE: Dict[str, Any] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


# ============================================================================
# STATE DEFINITION
# ============================================================================

class SearchState(dict):
    """Graph state for semantic search pipeline."""

    def __init__(self, **kwargs):
        super().__init__()
        self.update(kwargs)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_cache_key(query: str, top_k: int, filters: Dict[str, Any]) -> str:
    """Generate deterministic cache key for search."""
    key_data = {
        "query": query.lower().strip(),
        "top_k": top_k,
        "filters": filters
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()


def clean_cache():
    """Remove expired cache entries."""
    now = datetime.utcnow()
    expired_keys = [
        key for key, value in SEARCH_CACHE.items()
        if value["expires_at"] < now
    ]
    for key in expired_keys:
        del SEARCH_CACHE[key]


# ============================================================================
# CORE SEARCH FUNCTION (SQLite-compatible)
# ============================================================================

def semantic_search_sqlite(
    session: Session,
    query_embedding: List[float],
    top_k: int = DEFAULT_TOP_K,
    filters: Optional[Dict[str, Any]] = None,
    similarity_threshold: float = SIMILARITY_THRESHOLD
) -> List[Dict[str, Any]]:
    """
    Execute semantic vector search using in-memory cosine similarity.

    This is the SQLite-compatible approach: load chunk embeddings from DB,
    compute cosine similarity in Python, and return top results.

    Args:
        session: Database session
        query_embedding: Query embedding vector
        top_k: Number of results to return
        filters: Optional filters (e.g., category)
        similarity_threshold: Minimum similarity score

    Returns:
        List of search results sorted by similarity
    """
    if not query_embedding:
        logger.error("Invalid query embedding")
        return []

    # Build query for chunks
    query = session.query(KnowledgeChunk, KnowledgeSource).join(
        KnowledgeSource,
        KnowledgeChunk.source_id == KnowledgeSource.id
    ).filter(
        KnowledgeSource.is_active == True,
        KnowledgeChunk.embedding.isnot(None)
    )

    # Apply category filter
    if filters and filters.get("category"):
        query = query.filter(KnowledgeSource.category == filters["category"])

    # Fetch all matching chunks
    rows = query.all()

    if not rows:
        logger.info("No knowledge chunks found in database")
        return []

    # Compute cosine similarity for each chunk
    results = []
    for chunk, source in rows:
        try:
            # Parse stored embedding (JSON string in SQLite)
            if isinstance(chunk.embedding, str):
                chunk_embedding = json.loads(chunk.embedding)
            elif isinstance(chunk.embedding, list):
                chunk_embedding = chunk.embedding
            else:
                continue

            # Compute similarity
            score = cosine_similarity(query_embedding, chunk_embedding)

            if score >= similarity_threshold:
                results.append({
                    "id": str(chunk.id),
                    "content": chunk.text,
                    "source_id": str(source.id),
                    "source_title": source.title,
                    "source_category": source.category.value if hasattr(source.category, 'value') else str(source.category),
                    "source_description": source.description,
                    "score": score,
                    "chunk_index": chunk.index,
                    "token_count": chunk.token_count,
                    "word_count": chunk.word_count,
                    "metadata": {}
                })

        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning("Error parsing embedding for chunk %s: %s", chunk.id, e)
            continue

    # Sort by score (descending) and limit to top_k
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]

def semantic_search_chroma(
    query_embedding: List[float],
    top_k: int = DEFAULT_TOP_K,
    filters: Optional[Dict[str, Any]] = None,
    similarity_threshold: float = SIMILARITY_THRESHOLD
) -> List[Dict[str, Any]]:
    """
    Execute semantic vector search using ChromaDB.
    """
    from app.services.rag.chroma_client import get_chroma_collection
    collection = get_chroma_collection()

    where_filter = {}
    if filters and filters.get("category"):
        where_filter = {"category": filters["category"]}

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        logger.error("ChromaDB query failed: %s", e)
        return []

    if not results or not results.get("ids") or not results["ids"][0]:
        return []

    formatted_results = []
    for i in range(len(results["ids"][0])):
        distance = results["distances"][0][i]
        similarity = 1.0 - distance

        if similarity >= similarity_threshold:
            metadata = results["metadatas"][0][i]
            formatted_results.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "source_id": metadata.get("source_id"),
                "source_title": metadata.get("source_title"),
                "source_category": metadata.get("category"),
                "score": similarity,
                "chunk_index": metadata.get("index", 0),
                "token_count": 0,
                "word_count": len(results["documents"][0][i].split()),
                "metadata": {}
            })

    # Sort by score descending just in case
    formatted_results.sort(key=lambda x: x["score"], reverse=True)
    return formatted_results


# ============================================================================
# PIPELINE NODES
# ============================================================================

def check_cache(state: SearchState) -> SearchState:
    """Node 1: Check if results are cached."""
    try:
        clean_cache()

        cache_key = generate_cache_key(
            query=state["query"],
            top_k=state.get("top_k", DEFAULT_TOP_K),
            filters=state.get("filters", {})
        )
        state["cache_key"] = cache_key

        if cache_key in SEARCH_CACHE:
            cached = SEARCH_CACHE[cache_key]
            if datetime.utcnow() < cached["expires_at"]:
                state["ranked_results"] = cached["results"]
                state["used_cache"] = True
                state["status"] = "completed_from_cache"
                logger.info("Cache hit for query: '%s'", state["query"])
                return state

        state["used_cache"] = False
        state["status"] = "cache_miss"
        return state

    except Exception as e:
        logger.warning("Cache check failed: %s", str(e))
        state["used_cache"] = False
        return state


def process_query(state: SearchState) -> SearchState:
    """Node 2: Process and validate search query."""
    if state.get("used_cache"):
        return state

    try:
        query = state["query"]

        if not query or len(query.strip()) == 0:
            state["error"] = "Query cannot be empty"
            state["status"] = "failed"
            return state

        top_k = min(state.get("top_k", DEFAULT_TOP_K), MAX_TOP_K)
        state["top_k"] = max(1, top_k)

        state["metadata"] = {
            "original_query": query,
            "query_length": len(query),
            "top_k": state["top_k"]
        }

        state["status"] = "query_processed"
        logger.info("Processed query: '%s'", query)

        return state

    except Exception as e:
        logger.error("Error processing query: %s", str(e))
        state["error"] = str(e)
        state["status"] = "failed"
        return state


def generate_query_embedding(state: SearchState) -> SearchState:
    """Node 3: Generate query embedding using Gemini."""
    if state.get("used_cache") or state.get("error"):
        return state

    try:
        query = state["query"]
        logger.info("Generating embedding for query: '%s'", query)

        query_embedding = generate_embedding(query)

        if not query_embedding:
            logger.error("Failed to generate query embedding")
            state["error"] = "Embedding generation failed"
            state["status"] = "failed"
            return state

        state["query_embedding"] = query_embedding
        state["status"] = "embedding_generated"
        state["metadata"]["embedding_dimension"] = len(query_embedding)

        logger.info(
            "Generated query embedding (dim=%d) for: '%s'",
            len(query_embedding), query
        )

        return state

    except Exception as e:
        logger.error("Error generating embedding: %s", str(e))
        state["error"] = str(e)
        state["status"] = "failed"
        return state


def execute_search(state: SearchState) -> SearchState:
    """Node 4: Execute search against database."""
    if state.get("used_cache") or state.get("error"):
        return state

    session: Session = SessionLocal()
    try:
        results = semantic_search_chroma(
            query_embedding=state["query_embedding"],
            top_k=state["top_k"],
            filters=state.get("filters", {})
        )

        state["search_results"] = results
        state["status"] = "search_completed"

        logger.info(
            "Search completed: %d results for '%s'",
            len(results), state["query"]
        )

        return state

    except Exception as e:
        logger.error("Error executing search: %s", str(e))
        state["error"] = str(e)
        state["status"] = "failed"
        return state
    finally:
        session.close()


def rank_and_format(state: SearchState) -> SearchState:
    """Node 5: Rank and format search results."""
    if state.get("used_cache") or state.get("error"):
        return state

    try:
        results = state.get("search_results", [])

        ranked_results = []
        for i, result in enumerate(results[:state["top_k"]]):
            result["rank"] = i + 1
            ranked_results.append(result)

        state["ranked_results"] = ranked_results
        state["status"] = "results_ranked"

        state["metadata"]["result_count"] = len(ranked_results)
        if ranked_results:
            state["metadata"]["top_score"] = ranked_results[0].get("score", 0)

        logger.info("Ranked %d results", len(ranked_results))

        return state

    except Exception as e:
        logger.error("Error ranking results: %s", str(e))
        state["error"] = str(e)
        state["status"] = "failed"
        return state


def cache_results(state: SearchState) -> SearchState:
    """Node 6: Cache search results."""
    if state.get("error") or not state.get("cache_key"):
        return state

    try:
        SEARCH_CACHE[state["cache_key"]] = {
            "results": state["ranked_results"],
            "expires_at": datetime.utcnow() + timedelta(seconds=CACHE_TTL_SECONDS),
            "metadata": state.get("metadata", {})
        }

        logger.info("Cached results for key: %s", state["cache_key"])
        state["status"] = "completed"

        return state

    except Exception as e:
        logger.warning("Failed to cache results: %s", str(e))
        state["status"] = "completed"
        return state


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def build_search_graph():
    """Build and compile the search processing graph."""
    graph = StateGraph(SearchState)

    graph.add_node("check_cache", check_cache)
    graph.add_node("process_query", process_query)
    graph.add_node("generate_query_embedding", generate_query_embedding)
    graph.add_node("execute_search", execute_search)
    graph.add_node("rank_and_format", rank_and_format)
    graph.add_node("cache_results", cache_results)

    graph.set_entry_point("check_cache")

    graph.add_conditional_edges(
        "check_cache",
        lambda x: "cached" if x.get("used_cache") else "process_query",
        {
            "cached": END,
            "process_query": "process_query"
        }
    )

    graph.add_edge("process_query", "generate_query_embedding")
    graph.add_edge("generate_query_embedding", "execute_search")
    graph.add_edge("execute_search", "rank_and_format")
    graph.add_edge("rank_and_format", "cache_results")
    graph.add_edge("cache_results", END)

    return graph.compile()


# ============================================================================
# PIPELINE EXECUTION
# ============================================================================

async def search(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run the semantic search pipeline.

    Args:
        query: Search query string
        top_k: Number of results to return
        filters: Additional search filters (e.g., category)

    Returns:
        Search results dictionary
    """
    try:
        graph = build_search_graph()

        initial_state = SearchState(
            query=query,
            top_k=top_k,
            filters=filters or {},
            status="pending",
            metadata={}
        )

        logger.info("Starting search for query: '%s'", query)
        final_state = await graph.ainvoke(initial_state)

        return {
            "success": not bool(final_state.get("error")),
            "query": query,
            "results": final_state.get("ranked_results", []),
            "total_results": len(final_state.get("ranked_results", [])),
            "used_cache": final_state.get("used_cache", False),
            "metadata": final_state.get("metadata", {}),
            "error": final_state.get("error")
        }

    except Exception as e:
        logger.error("Search pipeline failed: %s", str(e))
        return {
            "success": False,
            "query": query,
            "results": [],
            "total_results": 0,
            "error": str(e)
        }
