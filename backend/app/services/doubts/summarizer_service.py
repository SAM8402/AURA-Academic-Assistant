import logging
from datetime import timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session

# --- 1. SETUP & IMPORTS ---
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import PromptTemplate
    from pydantic import BaseModel, Field
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseModel = object
    Field = lambda **kwargs: None
    ChatGoogleGenerativeAI = None
    JsonOutputParser = None
    PromptTemplate = None

# Config import
try:
    from config.settings import settings
except ImportError:
    import os
    class MockSettings:
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        GEMINI_MODEL = "gemini-2.5-flash"
    settings = MockSettings()

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# REAL IMPORTS (Person 1 + Person 2)
# -----------------------------------------------------------------------------
from app.models.doubts import DoubtUpload, DoubtMessage
from app.schemas.doubts import DoubtUploadCreate, WeeklySummaryResponse

# -----------------------------------------------------------------------------
# SERVICE
# -----------------------------------------------------------------------------

class DoubtSummarizerService:
    def __init__(self):
        """Initialize LLM with multi-model fallback + JSON parser."""
        self.llm = None
        self.parser = None

        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain not installed. Doubt summarizer will not work.")
            logger.warning("Install with: pip install langchain langchain-google-genai")
            return

        if not settings.GOOGLE_API_KEY or settings.GOOGLE_API_KEY == "your-google-api-key":
            logger.warning("[WARNING] Google API Key missing - LLM disabled.")
            return

        try:
            self.parser = JsonOutputParser(pydantic_object=WeeklySummaryResponse)
            self.llm = self._build_rag_llm()
            logger.info("DoubtSummarizerService initialized with multi-model fallback.")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")

    @staticmethod
    def _build_rag_llm():
        api_keys = [k.strip() for k in settings.GOOGLE_API_KEY.split(",") if k.strip()]
        if not api_keys:
            api_keys = [""]

        models = ["gemini-3.0-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash", "gemma-3-27b"]
        llms = []

        for model_name in models:
            for key in api_keys:
                llms.append(
                    ChatGoogleGenerativeAI(
                        model=model_name,
                        google_api_key=key,
                        temperature=0.1,
                        max_retries=1,
                    )
                )

        return llms[0].with_fallbacks(llms[1:])

    # -------------------------------------------------------------------------
    # Task 1 — Save Upload + Messages
    # -------------------------------------------------------------------------
    def create_doubt_upload(self, db: Session, upload_in: DoubtUploadCreate, user_id: int):
        """
        Saves the upload metadata and related messages into the database.
        """
        try:
            # Create upload
            new_upload = DoubtUpload(
                course_code=upload_in.course_code,
                source=upload_in.source,
                created_by_id=user_id
            )
            db.add(new_upload)
            db.commit()
            db.refresh(new_upload)

            # Create messages
            for msg in upload_in.messages:
                new_message = DoubtMessage(
                    upload_id=new_upload.id,
                    author_role=msg.get("author_role", "student"),
                    text=msg.get("text")
                )
                db.add(new_message)

            db.commit()
            return new_upload
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating doubt upload: {e}")
            raise

    # -------------------------------------------------------------------------
    # Task 2 — Fetch Recent Messages
    # -------------------------------------------------------------------------
    def get_recent_messages_for_course(
        self, 
        db: Session, 
        course_code: str, 
        limit: int = 100,
        period: str = None,
        source: str = None
    ) -> List[str]:
        """
        Fetch the most recent messages for a course with optional period and source filters.
        
        Args:
            period: 'daily', 'weekly', 'monthly', or None for all time
            source: 'forum', 'email', 'chat', or None for all sources
        """
        from datetime import datetime, timedelta

        try:
            query = (
                db.query(DoubtMessage.text)
                .join(DoubtUpload, DoubtMessage.upload_id == DoubtUpload.id)
                .filter(DoubtUpload.course_code == course_code)
            )

            # Apply period filter
            if period:
                now = datetime.now(timezone.utc)
                if period == 'daily':
                    start_date = now - timedelta(days=1)
                elif period == 'weekly':
                    start_date = now - timedelta(weeks=1)
                elif period == 'monthly':
                    start_date = now - timedelta(days=30)
                else:
                    start_date = None
                
                if start_date:
                    query = query.filter(DoubtUpload.created_at >= start_date)

            # Apply source filter
            if source and source != 'all':
                query = query.filter(DoubtUpload.source == source)

            rows = query.order_by(DoubtUpload.created_at.desc()).limit(limit).all()

            return [r[0] for r in rows]
        except Exception as e:
            logger.error(f"Error fetching recent messages for course {course_code}: {e}")
            return []

    # -------------------------------------------------------------------------
    # Task 3 — LLM Analysis (Summary + Topics + Insights)
    # -------------------------------------------------------------------------
    async def generate_summary_topics_insights(self, messages: List[str], course_code: str, include_stats: bool = False) -> Dict[str, Any]:
        """
        Sends messages to Gemini to generate structured summaries.
        
        Args:
            messages: List of doubt message texts
            course_code: Course identifier
            include_stats: If True, caller should add stats separately
        """

        if not self.llm:
            return {"error": "LLM not configured"}

        if not messages:
            return self._empty_state(course_code)

        prompt = PromptTemplate(
            template="""
You are an expert academic assistant analyzing student doubts and queries for the course "{course_code}".

You will receive a list of student doubt messages extracted from forums, emails, and chat channels.

## Your Task

Analyze all the messages below and produce a structured JSON report.

### Student Doubt Messages
{doubts_text}

## Analysis Instructions

1. **overall_summary**: Write a concise 3-5 sentence summary capturing the main themes, frequency of topics, and overall sentiment of the student doubts.

2. **topics**: Group the doubts into thematic clusters. For each topic, provide:
   - "name": A short descriptive topic name
   - "keywords": A list of 3-5 relevant keywords
   - "student_count": Approximate number of students asking about this topic
   - "severity": "low", "medium", or "high" based on urgency and frequency

3. **learning_gaps**: Identify specific conceptual misunderstandings or knowledge gaps evidenced by the doubts. For each gap:
   - "concept": The specific concept students are struggling with
   - "description": A brief explanation of the misunderstanding
   - "student_count": Estimated number of students affected
   - "suggested_action": A concrete recommendation for addressing this gap (e.g., extra tutorial, revised lecture notes, practice problems)

4. **insights**: Provide actionable observations for the teaching team:
   - Patterns in timing or context of doubts
   - Correlations between topics
   - Suggestions for proactive interventions
   - Any signs of common misconceptions that could be addressed in class

Return ONLY valid JSON matching the schema below. Do not include any text outside the JSON object.

{format_instructions}
            """,
            input_variables=["course_code", "doubts_text"],
            partial_variables={
                "format_instructions": self.parser.get_format_instructions()
            }
        )

        chain = prompt | self.llm | self.parser

        try:
            formatted = "\n".join([f"- {m}" for m in messages])
            result = await chain.ainvoke({
                "course_code": course_code,
                "doubts_text": formatted
            })
            
            # Calculate recurring issues: learning gaps mentioned by multiple students
            if isinstance(result, dict) and 'learning_gaps' in result:
                recurring_count = sum(1 for gap in result.get('learning_gaps', []) 
                                     if isinstance(gap, dict) and gap.get('student_count', 0) > 1)
                result['recurring_issues_count'] = recurring_count
            
            return result
        except Exception as e:
            logger.error(f"LLM Error during summary generation for {course_code}: {e}")
            return {"error": "An error occurred while generating the summary. Please try again later."}

    # -------------------------------------------------------------------------
    # Task 3.5 — Compute Enhanced Statistics
    # -------------------------------------------------------------------------
    def compute_summary_stats(self, db: Session, course_code: str, period: str = None, source: str = None) -> Dict[str, Any]:
        """
        Compute comprehensive statistics including message counts, unique uploads, and recurring issues.
        """
        from datetime import datetime, timedelta
        from sqlalchemy import func, distinct

        try:
            query = (
                db.query(
                    func.count(DoubtMessage.id).label('total_messages'),
                    func.count(distinct(DoubtUpload.id)).label('unique_uploads')
                )
                .join(DoubtUpload, DoubtMessage.upload_id == DoubtUpload.id)
                .filter(DoubtUpload.course_code == course_code)
            )

            # Apply period filter
            if period:
                now = datetime.now(timezone.utc)
                if period == 'daily':
                    start_date = now - timedelta(days=1)
                elif period == 'weekly':
                    start_date = now - timedelta(weeks=1)
                elif period == 'monthly':
                    start_date = now - timedelta(days=30)
                else:
                    start_date = None
                
                if start_date:
                    query = query.filter(DoubtUpload.created_at >= start_date)

            # Apply source filter
            if source and source != 'all':
                query = query.filter(DoubtUpload.source == source)

            result = query.first()

            return {
                'total_messages': result.total_messages if result else 0,
                'unique_uploads': result.unique_uploads if result else 0
            }
        except Exception as e:
            logger.error(f"Error computing summary stats for course {course_code}: {e}")
            return {'total_messages': 0, 'unique_uploads': 0}

    # -------------------------------------------------------------------------
    # Task 4 — Get Source Breakdown
    # -------------------------------------------------------------------------
    def get_source_breakdown(self, db: Session, course_code: str, period: str = None) -> Dict[str, Any]:
        """
        Get breakdown of doubts by source (forum, email, chat) with counts and percentages.
        """
        from datetime import datetime, timedelta
        from sqlalchemy import func

        try:
            query = (
                db.query(
                    DoubtUpload.source,
                    func.count(DoubtMessage.id).label('count')
                )
                .join(DoubtMessage, DoubtUpload.id == DoubtMessage.upload_id)
                .filter(DoubtUpload.course_code == course_code)
            )

            # Apply period filter
            if period:
                now = datetime.now(timezone.utc)
                if period == 'daily':
                    start_date = now - timedelta(days=1)
                elif period == 'weekly':
                    start_date = now - timedelta(weeks=1)
                elif period == 'monthly':
                    start_date = now - timedelta(days=30)
                else:
                    start_date = None
                
                if start_date:
                    query = query.filter(DoubtUpload.created_at >= start_date)

            results = query.group_by(DoubtUpload.source).all()

            # Calculate totals and percentages
            total = sum(r.count for r in results)
            breakdown = {}
            
            for result in results:
                source_name = result.source
                count = result.count
                percentage = round((count / total * 100), 1) if total > 0 else 0
                breakdown[source_name] = {
                    "count": count,
                    "percentage": percentage
                }

            # Ensure all sources are present (even if 0)
            for source in ['forum', 'email', 'chat']:
                if source not in breakdown:
                    breakdown[source] = {"count": 0, "percentage": 0}

            return {
                "total": total,
                "breakdown": breakdown
            }
        except Exception as e:
            logger.error(f"Error computing source breakdown for course {course_code}: {e}")
            return {"total": 0, "breakdown": {"forum": {"count": 0, "percentage": 0}, "email": {"count": 0, "percentage": 0}, "chat": {"count": 0, "percentage": 0}}}

    # -------------------------------------------------------------------------
    # Empty State
    # -------------------------------------------------------------------------
    def _empty_state(self, course_code: str):
        return {
            "course_code": course_code,
            "overall_summary": "No data.",
            "topics": [],
            "learning_gaps": [],
            "insights": []
        }


# GLOBAL INSTANCE
doubt_summarizer_service = DoubtSummarizerService()
