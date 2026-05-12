"""
AURA Chatbot Service — Supporting Infrastructure (Agentic Architecture).

Contains:
- MemoryManager: Session memory (sliding window) + persistent DB storage
- ToolExecutor: Executes the tools that the agentic LLM calls
- TOOL_DECLARATIONS: Gemini function declarations for the agent's toolbox
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.chat_session import ChatSession
from app.models.enums import CategoryEnum
from app.models.query import Query
from app.models.user import User
from app.services.chatbot.base_service import (
    MAX_SESSION_TURNS,
    MAX_SUMMARY_LENGTH,
    MAX_PERSISTENT_SESSIONS,
    RAG_TOP_K,
    RAG_SIMILARITY_THRESHOLD,
    WEB_SEARCH_MAX_RESULTS,
    DB_QUERY_MATCH_LIMIT,
    KEYWORD_MIN_LENGTH,
    rewrite_query_for_rag,
)

# Optional dependencies
try:
    from google.genai import types
    _TYPES_AVAILABLE = True
except ImportError:
    _TYPES_AVAILABLE = False
    types = None

try:
    from duckduckgo_search import DDGS
    _WEB_SEARCH_AVAILABLE = True
except ImportError:
    _WEB_SEARCH_AVAILABLE = False
    DDGS = None

logger = logging.getLogger(__name__)

Turn = Dict[str, Any]


# =============================================================================
# Tool Declarations (Gemini Function Calling Schema)
# =============================================================================

def _build_tool_declarations() -> list:
    """Build the function declarations for the agent's toolbox."""
    if not _TYPES_AVAILABLE:
        return []

    return [
        types.FunctionDeclaration(
            name="search_knowledge_base",
            description=(
                "Search the academic knowledge base for relevant course materials, "
                "lecture notes, textbook content, and educational resources. "
                "Use this when the student asks about academic topics, concepts, "
                "theories, or course-specific content."
            ),
            parameters={
                "type": "OBJECT",
                "properties": {
                    "query": {
                        "type": "STRING",
                        "description": "The search query to find relevant content in the knowledge base",
                    },
                },
                "required": ["query"],
            },
        ),
        types.FunctionDeclaration(
            name="search_student_queries",
            description=(
                "Search the student's existing queries and their responses in the "
                "learning management system. This finds relevant past questions asked "
                "by the student (or all students if the user is a TA/instructor), "
                "along with responses from TAs and instructors. Use this when the "
                "student asks about their doubts, queries, or previously asked questions."
            ),
            parameters={
                "type": "OBJECT",
                "properties": {
                    "query": {
                        "type": "STRING",
                        "description": "Keywords to search in existing queries and responses",
                    },
                },
                "required": ["query"],
            },
        ),
        types.FunctionDeclaration(
            name="list_all_queries",
            description=(
                "List all queries (questions/doubts) for the current student, showing "
                "title, status (OPEN/IN_PROGRESS/RESOLVED), category, priority, and "
                "number of responses. Use when the student asks to see all their "
                "queries, check status of their doubts, or wants an overview."
            ),
            parameters={
                "type": "OBJECT",
                "properties": {},
            },
        ),
        types.FunctionDeclaration(
            name="search_web",
            description=(
                "Search the internet for current information. Use this ONLY when: "
                "(1) the question involves recent events, news, or time-sensitive data, "
                "(2) the knowledge base didn't have relevant results, or "
                "(3) the student explicitly asks for online resources."
            ),
            parameters={
                "type": "OBJECT",
                "properties": {
                    "query": {
                        "type": "STRING",
                        "description": "The web search query",
                    },
                },
                "required": ["query"],
            },
        ),
        types.FunctionDeclaration(
            name="get_course_info",
            description=(
                "Get information about the student's enrolled courses, available quizzes, "
                "quiz scores, and course resources. Use when the student asks about their "
                "courses, grades, quiz performance, available materials, or enrollment."
            ),
            parameters={
                "type": "OBJECT",
                "properties": {
                    "info_type": {
                        "type": "STRING",
                        "description": (
                            "What information to retrieve. One of: "
                            "'courses' (enrolled courses), "
                            "'quizzes' (available quizzes and scores), "
                            "'resources' (course materials and resources)"
                        ),
                    },
                },
                "required": ["info_type"],
            },
        ),
    ]


TOOL_DECLARATIONS = _build_tool_declarations()


# =============================================================================
# Memory Manager
# =============================================================================

class MemoryManager:
    """
    Manages conversation memory across two tiers:
      1. Session Memory  — sliding window of last N turns (in-memory)
      2. Persistent Memory — conversation summaries stored in ChatSession DB
    """

    def __init__(self, max_turns: int = MAX_SESSION_TURNS):
        self._sessions: Dict[str, List[Turn]] = {}
        self._max_turns = max_turns

    # -- Session Memory (Tier 1) ----------------------------------------------

    def get_session_history(self, conversation_id: str) -> List[Turn]:
        """Return conversation history as Gemini-format messages."""
        return list(self._sessions.get(conversation_id, []))

    def add_turn(
        self, conversation_id: str, user_message: str, assistant_response: str,
    ) -> None:
        """Append a user/assistant exchange and enforce the sliding window."""
        if conversation_id not in self._sessions:
            self._sessions[conversation_id] = []

        history = self._sessions[conversation_id]
        history.append({"role": "user", "parts": [{"text": user_message}]})
        history.append({"role": "model", "parts": [{"text": assistant_response}]})

        max_entries = self._max_turns * 2
        if len(history) > max_entries:
            self._sessions[conversation_id] = history[-max_entries:]

    def clear_session(self, conversation_id: str) -> bool:
        if conversation_id in self._sessions:
            del self._sessions[conversation_id]
            return True
        return False

    def generate_conversation_id(self) -> str:
        return f"conv-{uuid.uuid4().hex[:12]}"

    # -- Persistent Memory (Tier 2) -------------------------------------------

    def load_persistent_summaries(
        self, db: Session, user: User, limit: int = MAX_PERSISTENT_SESSIONS,
    ) -> List[str]:
        """Load conversation summaries from previous sessions."""
        summaries = []
        try:
            sessions = (
                db.query(ChatSession)
                .order_by(ChatSession.updated_at.desc())
                .all()
            )
            for session in sessions:
                if not session.metadata_:
                    continue
                if (
                    session.metadata_.get("user_id") != user.id
                    and session.metadata_.get("user_email") != user.email
                ):
                    continue
                summary = session.metadata_.get("summary", "")
                if summary:
                    summaries.append(summary)
                if len(summaries) >= limit:
                    break
        except Exception as e:
            logger.warning("Failed to load persistent summaries: %s", e)
        return summaries

    def save_session(
        self,
        db: Session,
        user: User,
        conversation_id: str,
        user_message: str,
        assistant_response: str,
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None,
    ) -> None:
        """Persist the current exchange to the ChatSession table."""
        try:
            chat_session = self._find_existing_session(db, user, conversation_id)
            if chat_session is None:
                chat_session = self._create_session(
                    db, user, conversation_id, ip_address, device_info
                )
            self._update_session(db, chat_session, user_message, assistant_response, conversation_id)
        except Exception as e:
            logger.error("Failed to save session: %s", e)
            db.rollback()

    def _find_existing_session(
        self, db: Session, user: User, conversation_id: str,
    ) -> Optional[ChatSession]:
        try:
            sessions = (
                db.query(ChatSession).order_by(ChatSession.updated_at.desc()).all()
            )
            for session in sessions:
                if not session.metadata_:
                    continue
                if (
                    session.metadata_.get("conversation_id") == conversation_id
                    and session.metadata_.get("user_id") == user.id
                ):
                    return session
        except Exception as e:
            logger.warning("Error searching for existing session: %s", e)
        return None

    def _create_session(
        self, db: Session, user: User, conversation_id: str,
        ip_address: Optional[str] = None, device_info: Optional[str] = None,
    ) -> ChatSession:
        metadata = {
            "user_id": user.id,
            "user_email": user.email,
            "user_role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "conversation_id": conversation_id,
            "started_at": datetime.now(UTC).isoformat(),
            "message_count": 0,
            "messages": [],
            "summary": "",
        }
        session = ChatSession(
            ip_address=ip_address,
            device_info=device_info,
            language="en",
            metadata_=metadata,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info("Created chat session for user=%s conv=%s", user.email, conversation_id)
        return session

    def _update_session(
        self, db: Session, chat_session: ChatSession,
        user_message: str, assistant_response: str, conversation_id: str,
    ) -> None:
        meta = chat_session.metadata_ or {}
        meta["message_count"] = meta.get("message_count", 0) + 1

        messages = meta.get("messages", [])
        now = datetime.now(UTC).isoformat()
        messages.append({"role": "user", "content": user_message[:500], "timestamp": now})
        messages.append({"role": "assistant", "content": assistant_response[:500], "timestamp": now})
        meta["messages"] = messages[-20:]

        recent_questions = [
            f"Q: {m['content'][:100]}" for m in messages[-6:] if m["role"] == "user"
        ]
        meta["summary"] = " | ".join(recent_questions)[:MAX_SUMMARY_LENGTH] or "Conversation started"
        meta["last_message_at"] = now
        meta["conversation_id"] = conversation_id

        chat_session.metadata_ = meta
        chat_session.updated_at = datetime.now(UTC)
        flag_modified(chat_session, "metadata_")
        db.commit()


# =============================================================================
# Tool Executor — Runs the tools the LLM requests
# =============================================================================

class ToolExecutor:
    """
    Executes tool calls from the agentic LLM.

    Created per-request with the current DB session and user, so each tool
    has access to the right context without global state.
    Includes retry logic and timeout protection for robustness.
    """

    TOOL_TIMEOUT_SECONDS = 10  # Max time per tool execution
    MAX_RETRIES = 2            # Retry failed tools once

    def __init__(self, db: Session, user: User, use_kb: bool = True):
        self.db = db
        self.user = user
        self.use_kb = use_kb
        self._sources: List[Dict[str, Any]] = []
        self._execution_times: Dict[str, float] = {}

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a tool call with retry and timeout protection."""
        import time

        handlers = {
            "search_knowledge_base": self._search_knowledge_base,
            "search_student_queries": self._search_student_queries,
            "list_all_queries": self._list_all_queries,
            "search_web": self._search_web,
            "get_course_info": self._get_course_info,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                start = time.time()
                # Run synchronous handler directly (NOT in thread pool)
                # because handlers use self.db which is not thread-safe
                result = handler(**args)
                elapsed = round((time.time() - start) * 1000)
                self._execution_times[tool_name] = elapsed
                logger.info("Tool %s completed in %dms (attempt %d)", tool_name, elapsed, attempt + 1)
                return result

            except Exception as e:
                logger.warning("Tool %s failed (attempt %d/%d): %s", tool_name, attempt + 1, self.MAX_RETRIES, e)
                last_error = str(e)

        return {"error": last_error or f"Tool {tool_name} failed after {self.MAX_RETRIES} attempts", "tool": tool_name}

    def get_user_context(self) -> Dict[str, Any]:
        """Collect user metadata for prompt personalization."""
        context = {
            "user_id": self.user.id,
            "full_name": self.user.full_name,
            "role": self.user.role.value if hasattr(self.user.role, "value") else self.user.role,
            "is_new_user": False,
        }
        try:
            total_queries = self.db.query(Query).filter(Query.student_id == self.user.id).count()
            context["is_new_user"] = total_queries == 0
            recent = (
                self.db.query(Query).filter(Query.student_id == self.user.id)
                .order_by(Query.created_at.desc()).limit(3).all()
            )
            context["recent_topics"] = [q.title for q in recent] if recent else []

            # Enrolled courses
            try:
                from app.models.user_course import UserCourse
                from app.models.course import Course
                enrollments = (
                    self.db.query(Course.name)
                    .join(UserCourse, UserCourse.course_id == Course.id)
                    .filter(UserCourse.user_id == self.user.id)
                    .all()
                )
                context["enrolled_courses"] = [e[0] for e in enrollments] if enrollments else []
            except Exception:
                context["enrolled_courses"] = []

            # Recent quiz performance
            try:
                from app.models.quiz_attempt import QuizAttempt
                attempts = (
                    self.db.query(QuizAttempt)
                    .filter(QuizAttempt.user_id == self.user.id)
                    .order_by(QuizAttempt.attempted_at.desc())
                    .limit(5).all()
                )
                if attempts:
                    avg = sum(a.score / max(a.total_marks, 1) * 100 for a in attempts) / len(attempts)
                    context["quiz_avg_score"] = round(avg, 1)
            except Exception:
                pass

        except Exception as e:
            logger.warning("Failed to load user context: %s", e)
        return context

    def get_sources_used(self) -> List[Dict[str, Any]]:
        """Return all sources gathered during tool execution."""
        return list(self._sources)

    # -- Tool: Search Knowledge Base ------------------------------------------

    def _search_knowledge_base(self, query: str) -> Dict[str, Any]:
        """RAG semantic search over the knowledge base with query rewriting."""
        if not self.use_kb:
            return {"results": [], "message": "Knowledge base search is disabled for this request"}

        try:
            from config.db import SessionLocal
            from app.services.rag.search_pipeline import semantic_search_chroma
            from app.services.rag.embedding_service import generate_embedding

            search_query = rewrite_query_for_rag(query)
            logger.info("KB search: original='%s' rewritten='%s'", query[:60], search_query[:60])

            query_embedding = generate_embedding(search_query)
            if not query_embedding:
                logger.warning("KB search: embedding generation failed for '%s'", search_query[:60])
                return {"results": [], "message": "Failed to generate embedding for query"}

            logger.info("KB search: embedding generated (dim=%d)", len(query_embedding))

            kb_session = SessionLocal()
            try:
                # Broad search across ALL documents — no category restriction
                all_results = semantic_search_chroma(
                    query_embedding=query_embedding,
                    top_k=RAG_TOP_K,
                    filters={},
                    similarity_threshold=0.15,
                )
            finally:
                kb_session.close()

            if not all_results:
                logger.info("KB search: no results found for '%s'", search_query[:60])
                return {"results": [], "message": "No relevant content found in knowledge base"}

            all_results.sort(key=lambda r: r.get("score", 0), reverse=True)
            top = all_results[:RAG_TOP_K]

            formatted = []
            for r in top:
                title = r.get("source_title", "Unknown")
                category = r.get("source_category", "Unknown")
                content = r.get("content", "")
                score = r.get("score", 0.0)

                formatted.append({
                    "title": title,
                    "category": category,
                    "content": content[:600],
                    "relevance_score": round(score, 3),
                })
                self._sources.append({"type": "knowledge", "title": title, "category": category})

            logger.info("KB search: found %d results (top score=%.3f)", len(formatted), formatted[0]["relevance_score"] if formatted else 0)

            return {
                "results": formatted,
                "total_found": len(formatted),
                "message": f"Found {len(formatted)} relevant knowledge base entries",
            }

        except ImportError:
            return {"results": [], "message": "RAG pipeline not available"}
        except Exception as e:
            logger.warning("Knowledge base search failed: %s", e, exc_info=True)
            return {"results": [], "message": f"Search error: {str(e)}"}

    # -- Tool: Search Student Queries -----------------------------------------

    def _search_student_queries(self, query: str) -> Dict[str, Any]:
        """Keyword search in the student's existing queries and responses."""
        try:
            user_role = self.user.role.value if hasattr(self.user.role, "value") else self.user.role
            words = [w for w in query.lower().split() if len(w) >= KEYWORD_MIN_LENGTH]
            if not words:
                return {"results": [], "message": "Query too short for meaningful search"}

            # Scope queries by role
            if user_role == "student":
                all_queries = self.db.query(Query).filter(Query.student_id == self.user.id).all()
            else:
                all_queries = self.db.query(Query).all()

            # Score each query by keyword overlap
            scored = []
            for q in all_queries:
                text = f"{q.title} {q.description}".lower()
                if q.responses:
                    text += " " + " ".join(r.content.lower() for r in q.responses[:3])
                score = sum(1 for w in words if w in text)
                if score > 0:
                    scored.append((q, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            top = scored[:DB_QUERY_MATCH_LIMIT]

            if not top:
                return {"results": [], "message": "No matching queries found"}

            formatted = []
            for q, score in top:
                status = q.status.value if hasattr(q.status, "value") else str(q.status)
                category = q.category.value if hasattr(q.category, "value") else str(q.category)

                entry = {
                    "title": q.title,
                    "description": q.description[:200],
                    "status": status,
                    "category": category,
                    "response_count": len(q.responses) if q.responses else 0,
                    "responses": [],
                }

                # Include top responses with solution tags
                if q.responses:
                    for r in q.responses[:2]:
                        entry["responses"].append({
                            "author": r.user.full_name if r.user else "Unknown",
                            "content": r.content[:300],
                            "is_solution": bool(r.is_solution),
                        })

                formatted.append(entry)
                self._sources.append({
                    "type": "query", "title": str(q.title),
                    "category": category, "query_id": str(q.id),
                })

            return {
                "results": formatted,
                "total_found": len(formatted),
                "message": f"Found {len(formatted)} relevant queries",
            }

        except Exception as e:
            logger.error("Query search failed: %s", e)
            return {"results": [], "message": f"Search error: {str(e)}"}

    # -- Tool: List All Queries -----------------------------------------------

    def _list_all_queries(self) -> Dict[str, Any]:
        """List all queries for the current student (or all, for TAs/instructors)."""
        try:
            user_role = self.user.role.value if hasattr(self.user.role, "value") else self.user.role

            if user_role == "student":
                queries = (
                    self.db.query(Query)
                    .filter(Query.student_id == self.user.id)
                    .order_by(Query.created_at.desc())
                    .all()
                )
            else:
                queries = (
                    self.db.query(Query)
                    .order_by(Query.created_at.desc())
                    .all()
                )

            if not queries:
                return {"queries": [], "total": 0, "message": "No queries found"}

            formatted = []
            for q in queries:
                status = q.status.value if hasattr(q.status, "value") else str(q.status)
                category = q.category.value if hasattr(q.category, "value") else str(q.category)
                priority = q.priority.value if hasattr(q.priority, "value") else str(q.priority)

                entry = {
                    "title": q.title,
                    "status": status,
                    "category": category,
                    "priority": priority,
                    "description": q.description[:100],
                    "response_count": len(q.responses) if q.responses else 0,
                }

                # Include submitter name for TAs/instructors
                if user_role != "student" and q.student:
                    entry["submitted_by"] = q.student.full_name

                formatted.append(entry)

            return {
                "queries": formatted,
                "total": len(formatted),
                "message": f"Found {len(formatted)} total queries",
            }

        except Exception as e:
            logger.error("List queries failed: %s", e)
            return {"queries": [], "total": 0, "message": f"Error: {str(e)}"}

    # -- Tool: Web Search -----------------------------------------------------

    def _search_web(self, query: str) -> Dict[str, Any]:
        """Search the web using DuckDuckGo."""
        if not _WEB_SEARCH_AVAILABLE:
            return {"results": [], "message": "Web search not available (duckduckgo-search not installed)"}

        try:
            with DDGS() as ddgs:
                raw = list(ddgs.text(
                    keywords=query, max_results=WEB_SEARCH_MAX_RESULTS, backend="api",
                ))

            if not raw:
                return {"results": [], "message": "No web results found"}

            formatted = []
            for r in raw:
                title = r.get("title", "")
                snippet = r.get("body", "")
                url = r.get("href", "")
                formatted.append({"title": title, "snippet": snippet, "url": url})
                self._sources.append({"type": "web", "title": title, "url": url})

            return {
                "results": formatted,
                "total_found": len(formatted),
                "message": f"Found {len(formatted)} web results",
            }

        except Exception as e:
            logger.error("Web search failed: %s", e)
            return {"results": [], "message": f"Web search error: {str(e)}"}

    # -- Tool: Course Info ----------------------------------------------------

    def _get_course_info(self, info_type: str = "courses") -> Dict[str, Any]:
        """Get course enrollment, quiz scores, or resource info for the student."""
        try:
            from app.models.course import Course
            from app.models.user_course import UserCourse

            info_type = info_type.lower().strip()

            if info_type == "courses":
                enrollments = (
                    self.db.query(Course)
                    .join(UserCourse, UserCourse.course_id == Course.id)
                    .filter(UserCourse.user_id == self.user.id)
                    .all()
                )
                if not enrollments:
                    return {"results": [], "message": "No course enrollments found"}

                formatted = []
                for c in enrollments:
                    formatted.append({
                        "name": c.name,
                        "description": (c.description or "")[:200],
                        "quiz_count": len(c.quizzes) if c.quizzes else 0,
                    })
                    self._sources.append({"type": "course", "title": c.name})
                return {"results": formatted, "total": len(formatted), "message": f"Enrolled in {len(formatted)} courses"}

            elif info_type == "quizzes":
                from app.models.quiz import Quiz
                from app.models.quiz_attempt import QuizAttempt

                # Get quizzes from enrolled courses
                course_ids = (
                    self.db.query(UserCourse.course_id)
                    .filter(UserCourse.user_id == self.user.id)
                    .all()
                )
                cids = [c[0] for c in course_ids]
                quizzes = self.db.query(Quiz).filter(Quiz.course_id.in_(cids), Quiz.is_published == True).all() if cids else []

                formatted = []
                for q in quizzes[:10]:
                    attempt = (
                        self.db.query(QuizAttempt)
                        .filter(QuizAttempt.quiz_id == q.id, QuizAttempt.user_id == self.user.id)
                        .order_by(QuizAttempt.attempted_at.desc())
                        .first()
                    )
                    entry = {
                        "title": q.title,
                        "course": q.course.name if q.course else "Unknown",
                        "attempted": attempt is not None,
                    }
                    if attempt:
                        entry["score"] = attempt.score
                        entry["total_marks"] = attempt.total_marks
                        entry["percentage"] = round(attempt.score / max(attempt.total_marks, 1) * 100, 1)
                    formatted.append(entry)
                    self._sources.append({"type": "quiz", "title": q.title})

                return {"results": formatted, "total": len(formatted), "message": f"Found {len(formatted)} quizzes"}

            elif info_type == "resources":
                from app.models.resource import Resource
                resources = (
                    self.db.query(Resource)
                    .filter(Resource.is_active == True)
                    .order_by(Resource.created_at.desc())
                    .limit(10).all()
                )
                formatted = [
                    {
                        "title": r.title,
                        "type": r.resource_type.value if hasattr(r.resource_type, "value") else str(r.resource_type),
                        "description": (r.description or "")[:150],
                    }
                    for r in resources
                ]
                for r in resources:
                    self._sources.append({"type": "resource", "title": r.title})
                return {"results": formatted, "total": len(formatted), "message": f"Found {len(formatted)} resources"}

            else:
                return {"results": [], "message": f"Unknown info_type '{info_type}'. Use 'courses', 'quizzes', or 'resources'."}

        except ImportError as e:
            return {"results": [], "message": f"Required module not available: {e}"}
        except Exception as e:
            logger.error("Course info lookup failed: %s", e)
            return {"results": [], "message": f"Error: {str(e)}"}

    # -- Helpers --------------------------------------------------------------

    def _get_user_categories(self) -> List[Optional[CategoryEnum]]:
        """Map user role to relevant knowledge base categories."""
        role = self.user.role.value if hasattr(self.user.role, "value") else self.user.role
        role_map = {
            "student": [CategoryEnum.COURSES, CategoryEnum.ASSIGNMENTS, CategoryEnum.QUIZZES],
            "ta": [CategoryEnum.COURSES, CategoryEnum.QUERIES, CategoryEnum.ASSIGNMENTS],
            "instructor": [CategoryEnum.COURSES, CategoryEnum.PLACEMENT, CategoryEnum.ADMISSION],
            "admin": list(CategoryEnum),
        }
        return role_map.get(role, [None])
