"""
Unit tests for Doubt Summarizer Service.
Covers:
- empty input handling
- missing LLM behavior
- successful mocked LLM output
- error propagation handling
"""

import pytest
from unittest.mock import patch, AsyncMock
from app.services.doubts.summarizer_service import doubt_summarizer_service

# Mock Data returned by LLM
MOCK_LLM_RESPONSE = {
    "course_code": "CS101",
    "overall_summary": "Students are struggling with recursion.",
    "topics": [
        {
            "label": "Recursion",
            "trend": "Increasing",
            "count": 5,
            "sample_questions": ["What is a base case?"]
        }
    ],
    "learning_gaps": [],
    "insights": ["Review base cases."]
}


@pytest.mark.unit
class TestDoubtSummarizerService:
    """Tests for Doubt Summarizer Service."""

    # ---------------------------------------------------------
    # 1. EMPTY INPUT TEST
    # ---------------------------------------------------------
    @pytest.mark.asyncio
    async def test_generate_summary_empty_input(self):
        messages = []  # empty
        course_code = "CS101"

        result = await doubt_summarizer_service.generate_summary_topics_insights(
            messages, course_code
        )

        assert result["course_code"] == "CS101"
        assert result["overall_summary"] == "No data."
        assert result["topics"] == []

    # ---------------------------------------------------------
    # 2. MISSING LLM TEST
    # ---------------------------------------------------------
    @pytest.mark.asyncio
    async def test_generate_summary_missing_llm(self):
        messages = ["hello"]
        course_code = "CS101"

        # Temporarily disable LLM
        original_llm = doubt_summarizer_service.llm
        doubt_summarizer_service.llm = None

        result = await doubt_summarizer_service.generate_summary_topics_insights(
            messages, course_code
        )

        # Restore LLM
        doubt_summarizer_service.llm = original_llm

        assert "LLM not configured" in result.get("error", "")

    # ---------------------------------------------------------
    # 3. SUCCESS CASE — MOCK LLM
    # ---------------------------------------------------------
    @pytest.mark.asyncio
    async def test_generate_summary_success_mocked(self):
        messages = ["What is recursion?", "Help with loops"]
        course_code = "CS101"

        with patch("app.services.doubt_summarizer_service.PromptTemplate") as mock_prompt:
            # Mock chain result (LLM output)
            mock_chain_instance = AsyncMock()
            mock_chain_instance.ainvoke.return_value = MOCK_LLM_RESPONSE

            # Make the pipe operator `|` return our chain instance
            mock_prompt.return_value.__or__.return_value.__or__.return_value = (
                mock_chain_instance
            )

            result = await doubt_summarizer_service.generate_summary_topics_insights(
                messages, course_code
            )

        assert result["course_code"] == "CS101"
        assert result["overall_summary"] == "Students are struggling with recursion."
        assert len(result["topics"]) == 1
        assert result["topics"][0]["label"] == "Recursion"

    # ---------------------------------------------------------
    # 4. ERROR HANDLING TEST
    # ---------------------------------------------------------
    @pytest.mark.asyncio
    async def test_error_handling_during_analysis(self):
        messages = ["any doubt"]
        course_code = "CS101"

        with patch("app.services.doubt_summarizer_service.PromptTemplate") as mock_prompt:
            mock_chain_instance = AsyncMock()
            mock_chain_instance.ainvoke.side_effect = Exception("Google AI is down")

            mock_prompt.return_value.__or__.return_value.__or__.return_value = (
                mock_chain_instance
            )

            result = await doubt_summarizer_service.generate_summary_topics_insights(
                messages, course_code
            )

        assert "Google AI is down" in result.get("error", "")
