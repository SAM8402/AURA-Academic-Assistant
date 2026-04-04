import logging
import re
from urllib.parse import urlparse, parse_qs
from app.core.config import settings

# LangChain imports with fallback
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.prompts import PromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    ChatGoogleGenerativeAI = None
    PromptTemplate = None

# Import the library you have
try:
    import youtube_transcript_api
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

logger = logging.getLogger(__name__)

# Matches YouTube video IDs (11 chars, alphanumeric + dash/underscore)
VIDEO_ID_RE = re.compile(r"^[\w-]{11}$")


class VideoSummaryService:
    def __init__(self):
        self.llm = None
        self.yt_api = YouTubeTranscriptApi() if YouTubeTranscriptApi else None

        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain not installed. Video summary will not work.")
            return

        if settings.GOOGLE_API_KEY:
            try:
                self.llm = ChatGoogleGenerativeAI(
                    model=settings.GEMINI_MODEL,
                    google_api_key=settings.GOOGLE_API_KEY,
                    temperature=0.3
                )
            except Exception as e:
                logger.error(f"Failed to init LLM: {e}")

    def extract_video_id(self, url: str) -> str | None:
        """Extracts video ID from various YouTube URL formats.

        Supported formats:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/shorts/VIDEO_ID
        - https://youtube.com/v/VIDEO_ID
        - bare VIDEO_ID string
        """
        if not url or not isinstance(url, str):
            return None

        url = url.strip()

        try:
            parsed = urlparse(url)

            # No scheme -- could be a bare ID or missing https://
            if not parsed.scheme and not parsed.netloc:
                if VIDEO_ID_RE.match(url):
                    return url
                parsed = urlparse(f"https://{url}")
                if not parsed.netloc:
                    return None

            host = parsed.netloc.lower().removeprefix("www.")

            # Standard /watch?v=ID
            if "youtube" in host or "youtube-nocookie" in host:
                query_v = parse_qs(parsed.query).get("v")
                if query_v and VIDEO_ID_RE.match(query_v[0]):
                    return query_v[0]

                # /embed/ID or /v/ID or /shorts/ID
                path_parts = parsed.path.strip("/").split("/")
                if len(path_parts) >= 2 and path_parts[0] in ("embed", "v", "shorts"):
                    candidate = path_parts[1]
                    if VIDEO_ID_RE.match(candidate):
                        return candidate

            # youtu.be/ID
            if host in ("youtu.be", "www.youtu.be"):
                candidate = parsed.path.strip("/").split("?")[0]
                if VIDEO_ID_RE.match(candidate):
                    return candidate

            return None
        except Exception:
            logger.exception("Failed to parse video URL: %s", url)
            return None

    def get_transcript(self, video_id: str) -> str:
        """Fetches transcript from YouTube. Lists available transcripts first, then fetches."""
        if not self.yt_api:
            logger.error("YouTube Library not installed.")
            return None

        # First, list available transcripts to find the right language
        try:
            transcript_list = self.yt_api.list(video_id)
            available = list(transcript_list)
            if not available:
                logger.error("No transcripts available for video_id=%s", video_id)
                return None

            # Pick the first available transcript (prefer English variants)
            selected = None
            for t in available:
                lang = getattr(t, 'language_code', '') or str(t)
                if lang.startswith('en'):
                    selected = lang
                    break
            if not selected:
                # Use whatever is available
                selected = getattr(available[0], 'language_code', None) or str(available[0]).split('"')[1] if '"' in str(available[0]) else 'en'

            logger.info("Fetching transcript for video_id=%s, language=%s", video_id, selected)
            transcript_object = self.yt_api.fetch(video_id, languages=[selected])

            if isinstance(transcript_object, list):
                transcript_list = transcript_object
            elif hasattr(transcript_object, 'to_raw_data'):
                transcript_list = transcript_object.to_raw_data()
            else:
                transcript_list = transcript_object

            full_text = " ".join([t['text'] for t in transcript_list])
            logger.info("Transcript fetched successfully for video_id=%s (%d chars)", video_id, len(full_text))
            return full_text

        except Exception as e:
            logger.error("Transcript fetch failed for video_id=%s: %s", video_id, e)
            return None

    async def summarize_video(self, video_url: str) -> dict:
        if not video_url or not isinstance(video_url, str) or not video_url.strip():
            return {"error": "A valid YouTube URL is required"}

        if not self.llm:
            return {"error": "LLM not configured"}

        video_id = self.extract_video_id(video_url)
        if not video_id:
            return {"error": "Invalid YouTube URL"}

        transcript = self.get_transcript(video_id)

        if not transcript:
            return {"error": "No captions found for this video. Please try a video with captions/subtitles enabled."}

        # Limit transcript length to ~15k characters to fit Gemini's context window
        truncated_transcript = transcript[:15000]

        prompt = PromptTemplate.from_template("""
        You are an expert academic assistant. Summarize the following video transcript.
        
        **Transcript:**
        {text}
        
        **Instructions:**
        1. Provide a concise summary (3-5 sentences).
        2. List 3-5 key takeaways/bullet points.
        3. Mention the estimated difficulty level.
        4. **Further Learning:** Suggest 3 short, specific Google Search queries that the user should search to learn more about these topics. Format them as a bulleted list.
        
        Return the result in Markdown format.
        """)

        try:
            chain = prompt | self.llm
            result = await chain.ainvoke({"text": truncated_transcript})
            logger.info("Summary generated successfully for video_id=%s", video_id)
            return {"summary": result.content}
        except Exception as e:
            logger.error("Summary generation failed for video_id=%s: %s", video_id, e)
            return {"error": "An error occurred while generating the summary. Please try again later."}

video_summary_service = VideoSummaryService()
