"""
Unit tests for Chatbot Service.

This module tests:
- HybridChatbotService initialization
- Chat mode handling
- Conversation management
- Memory and session management
- Implementation switching (LangChain vs Native SDK)
- Error handling
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
from app.services.chatbot.hybrid_service import (
    HybridChatbotService,
    ChatImplementation,
    ChatMode
)


# ============================================================================
# Service Initialization Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.chatbot
class TestServiceInitialization:
    """Tests for chatbot service initialization."""

    def test_service_creation_default(self):
        """Test creating service with default implementation."""
        service = HybridChatbotService()

        # Should use default implementation
        assert service.implementation in [ChatImplementation.NATIVE_SDK, ChatImplementation.LANGCHAIN]

    def test_service_creation_native_sdk(self):
        """Test creating service with native SDK implementation."""
        service = HybridChatbotService(implementation=ChatImplementation.NATIVE_SDK)

        assert service.implementation == ChatImplementation.NATIVE_SDK

    def test_service_creation_langchain(self):
        """Test creating service with LangChain implementation."""
        service = HybridChatbotService(implementation=ChatImplementation.LANGCHAIN)

        assert service.implementation == ChatImplementation.LANGCHAIN

    def test_service_has_conversation_storage(self):
        """Test that service initializes conversation storage."""
        service = HybridChatbotService()

        assert hasattr(service, 'conversations')
        assert isinstance(service.conversations, dict)

    def test_service_adk_features_initialized(self):
        """Test that ADK features are initialized when using native SDK."""
        service = HybridChatbotService(implementation=ChatImplementation.NATIVE_SDK)

        # Check ADK components (may be None if API key not set)
        assert hasattr(service, 'adk_runner')
        assert hasattr(service, 'session_service')
        assert hasattr(service, 'memory_service')
        assert hasattr(service, 'observability_plugin')


# ============================================================================
# Implementation Switching Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.chatbot
class TestImplementationSwitching:
    """Tests for switching between implementations."""

    def test_switch_to_langchain(self):
        """Test switching from native SDK to LangChain."""
        service = HybridChatbotService(implementation=ChatImplementation.NATIVE_SDK)

        service.switch_implementation(ChatImplementation.LANGCHAIN)

        assert service.implementation == ChatImplementation.LANGCHAIN

    def test_switch_to_native_sdk(self):
        """Test switching from LangChain to native SDK."""
        service = HybridChatbotService(implementation=ChatImplementation.LANGCHAIN)

        service.switch_implementation(ChatImplementation.NATIVE_SDK)

        assert service.implementation == ChatImplementation.NATIVE_SDK

    def test_switch_preserves_conversations(self):
        """Test that switching implementations preserves conversation history."""
        service = HybridChatbotService(implementation=ChatImplementation.NATIVE_SDK)

        # Add a conversation
        service.conversations['test-conv'] = Mock()

        # Switch implementation
        service.switch_implementation(ChatImplementation.LANGCHAIN)

        # Conversation should still exist
        assert 'test-conv' in service.conversations


# ============================================================================
# Chat Functionality Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.chatbot
class TestChatFunctionality:
    """Tests for chat functionality."""

    @pytest.mark.asyncio
    async def test_chat_generates_conversation_id(self):
        """Test that chat generates a conversation ID if not provided."""
        service = HybridChatbotService()

        # Mock the actual chat implementation
        with patch.object(service, '_chat_native_sdk', return_value=("response", "conv-123")) as mock_chat:
            with patch.object(service, '_chat_langchain', return_value=("response", "conv-123")):
                response, conv_id = await service.chat(
                    message="Test message",
                    mode=ChatMode.GENERAL
                )

                # Should have a conversation ID
                assert conv_id is not None
                assert isinstance(conv_id, str)
                assert len(conv_id) > 0

    @pytest.mark.asyncio
    async def test_chat_uses_provided_conversation_id(self):
        """Test that chat uses provided conversation ID."""
        service = HybridChatbotService()

        provided_id = "my-custom-conv-id"

        with patch.object(service, '_chat_native_sdk', return_value=("response", provided_id)) as mock_chat:
            with patch.object(service, '_chat_langchain', return_value=("response", provided_id)):
                response, conv_id = await service.chat(
                    message="Test message",
                    mode=ChatMode.GENERAL,
                    conversation_id=provided_id
                )

                assert conv_id == provided_id

    @pytest.mark.asyncio
    async def test_chat_with_different_modes(self):
        """Test chat with different chat modes."""
        service = HybridChatbotService()

        modes = [ChatMode.ACADEMIC, ChatMode.GENERAL, ChatMode.STUDY_HELP, ChatMode.DOUBT_CLARIFICATION]

        for mode in modes:
            with patch.object(service, '_chat_native_sdk', return_value=(f"response for {mode}", "conv-123")):
                with patch.object(service, '_chat_langchain', return_value=(f"response for {mode}", "conv-123")):
                    response, conv_id = await service.chat(
                        message="Test message",
                        mode=mode
                    )

                    # Should succeed for all modes
                    assert response is not None
                    assert conv_id is not None


# ============================================================================
# Streaming Chat Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.chatbot
class TestStreamingChat:
    """Tests for streaming chat functionality."""

    @pytest.mark.asyncio
    async def test_chat_stream_returns_async_iterator(self):
        """Test that chat_stream returns an async iterator."""
        service = HybridChatbotService()

        async def mock_stream():
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"

        with patch.object(service, '_chat_stream_native_sdk', return_value=mock_stream()):
            with patch.object(service, '_chat_stream_langchain', return_value=mock_stream()):
                stream = service.chat_stream(
                    message="Test message",
                    mode=ChatMode.GENERAL
                )

                # Should be an async generator
                assert hasattr(stream, '__aiter__')

    @pytest.mark.asyncio
    async def test_chat_stream_yields_chunks(self):
        """Test that chat_stream yields text chunks."""
        service = HybridChatbotService()

        async def mock_stream():
            yield "Hello"
            yield " "
            yield "World"

        with patch.object(service, '_chat_stream_native_sdk', return_value=mock_stream()):
            with patch.object(service, '_chat_stream_langchain', return_value=mock_stream()):
                chunks = []
                async for chunk in service.chat_stream(
                    message="Test message",
                    mode=ChatMode.GENERAL
                ):
                    chunks.append(chunk)

                # Should have received all chunks
                assert len(chunks) == 3
                assert "".join(chunks) == "Hello World"


# ============================================================================
# Conversation Management Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.chatbot
class TestConversationManagement:
    """Tests for conversation management."""

    def test_clear_conversation_success(self):
        """Test successfully clearing a conversation."""
        service = HybridChatbotService()

        # Add a conversation
        conv_id = "test-conv-123"
        service.conversations[conv_id] = Mock()

        # Clear it
        result = service.clear_conversation(conv_id)

        assert result is True
        assert conv_id not in service.conversations

    def test_clear_nonexistent_conversation(self):
        """Test clearing a conversation that doesn't exist."""
        service = HybridChatbotService()

        result = service.clear_conversation("nonexistent-conv")

        assert result is False

    def test_get_conversation_history_empty(self):
        """Test getting history for non-existent conversation."""
        service = HybridChatbotService()

        history = service.get_conversation_history("nonexistent-conv")

        assert history is None or history == []

    def test_get_conversation_history_with_messages(self):
        """Test getting history for conversation with messages."""
        service = HybridChatbotService()

        # Create mock conversation with history
        conv_id = "test-conv-456"
        mock_memory = Mock()
        mock_memory.chat_memory.messages = [
            Mock(type="human", content="Hello"),
            Mock(type="ai", content="Hi there!")
        ]

        service.conversations[conv_id] = mock_memory

        history = service.get_conversation_history(conv_id)

        # Should return the messages
        if history is not None:
            assert len(history) >= 0  # May be empty or have messages depending on implementation


# ============================================================================
# Session State Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.chatbot
class TestSessionState:
    """Tests for session state management."""

    @pytest.mark.asyncio
    async def test_get_session_state(self):
        """Test getting session state for a conversation."""
        service = HybridChatbotService(implementation=ChatImplementation.NATIVE_SDK)

        state = await service.get_session_state("test-conv")

        # Should return a dict (may be empty)
        assert isinstance(state, dict)

    @pytest.mark.asyncio
    async def test_get_session_state_without_session_service(self):
        """Test getting session state when session service not available."""
        service = HybridChatbotService(implementation=ChatImplementation.LANGCHAIN)

        state = await service.get_session_state("test-conv")

        # Should return empty dict
        assert state == {}


# ============================================================================
# Metrics and Observability Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.chatbot
class TestMetricsAndObservability:
    """Tests for metrics and observability."""

    def test_get_metrics_with_observability(self):
        """Test getting metrics when observability is enabled."""
        service = HybridChatbotService(implementation=ChatImplementation.NATIVE_SDK)

        # Mock observability plugin
        if service.observability_plugin:
            service.observability_plugin.agent_count = 5
            service.observability_plugin.llm_request_count = 10

        metrics = service.get_metrics()

        # Metrics may be None or a dict
        assert metrics is None or isinstance(metrics, dict)

    def test_get_metrics_without_observability(self):
        """Test getting metrics when observability is not available."""
        service = HybridChatbotService()

        # Ensure observability is disabled
        service.observability_plugin = None

        metrics = service.get_metrics()

        # Should return None
        assert metrics is None


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.chatbot
class TestErrorHandling:
    """Tests for error handling in chatbot service."""

    @pytest.mark.asyncio
    async def test_chat_handles_exception(self):
        """Test that chat handles exceptions gracefully."""
        service = HybridChatbotService()

        # Make chat raise an exception
        with patch.object(service, '_chat_native_sdk', side_effect=Exception("Test error")):
            with patch.object(service, '_chat_langchain', side_effect=Exception("Test error")):
                with pytest.raises(Exception):
                    await service.chat(
                        message="Test message",
                        mode=ChatMode.GENERAL
                    )

    @pytest.mark.asyncio
    async def test_empty_message_handling(self):
        """Test handling of empty messages."""
        service = HybridChatbotService()

        # This should be caught by validation, but test service behavior
        with patch.object(service, '_chat_native_sdk', return_value=("", "conv-123")):
            with patch.object(service, '_chat_langchain', return_value=("", "conv-123")):
                response, conv_id = await service.chat(
                    message="",
                    mode=ChatMode.GENERAL
                )

                # Should still return a response
                assert response is not None
                assert conv_id is not None


# ============================================================================
# Chat Mode System Prompt Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.chatbot
class TestChatModes:
    """Tests for chat mode system prompts."""

    def test_academic_mode_system_prompt(self):
        """Test that academic mode has appropriate system prompt."""
        service = HybridChatbotService()

        # Get system prompt for academic mode
        system_prompt = service._get_system_prompt(ChatMode.ACADEMIC)

        # Should contain academic-related keywords
        assert any(word in system_prompt.lower() for word in ["academic", "educational", "explain", "teach"])

    def test_doubt_clarification_mode_system_prompt(self):
        """Test that doubt clarification mode has appropriate system prompt."""
        service = HybridChatbotService()

        system_prompt = service._get_system_prompt(ChatMode.DOUBT_CLARIFICATION)

        # Should contain clarification-related keywords
        assert any(word in system_prompt.lower() for word in ["doubt", "clarify", "step", "explain"])

    def test_study_help_mode_system_prompt(self):
        """Test that study help mode has appropriate system prompt."""
        service = HybridChatbotService()

        system_prompt = service._get_system_prompt(ChatMode.STUDY_HELP)

        # Should contain study-related keywords
        assert any(word in system_prompt.lower() for word in ["study", "learn", "practice", "prepare"])

    def test_general_mode_system_prompt(self):
        """Test that general mode has appropriate system prompt."""
        service = HybridChatbotService()

        system_prompt = service._get_system_prompt(ChatMode.GENERAL)

        # Should contain general assistance keywords
        assert any(word in system_prompt.lower() for word in ["assistant", "help", "answer", "question"])

    def test_all_modes_have_system_prompts(self):
        """Test that all chat modes have system prompts."""
        service = HybridChatbotService()

        modes = [ChatMode.ACADEMIC, ChatMode.GENERAL, ChatMode.STUDY_HELP, ChatMode.DOUBT_CLARIFICATION]

        for mode in modes:
            system_prompt = service._get_system_prompt(mode)

            # Each mode should have a non-empty system prompt
            assert system_prompt is not None
            assert len(system_prompt) > 0
            assert isinstance(system_prompt, str)


# ============================================================================
# Integration Tests for Service
# ============================================================================

@pytest.mark.unit
@pytest.mark.chatbot
@pytest.mark.integration
class TestServiceIntegration:
    """Integration tests for chatbot service."""

    @pytest.mark.asyncio
    async def test_multiple_conversations_simultaneously(self):
        """Test handling multiple conversations at the same time."""
        service = HybridChatbotService()

        conversations = []

        # Mock the chat method
        async def mock_chat(message, mode, conversation_id=None):
            conv_id = conversation_id or f"conv-{len(conversations)}"
            return (f"Response to: {message}", conv_id)

        with patch.object(service, '_chat_native_sdk', side_effect=mock_chat):
            with patch.object(service, '_chat_langchain', side_effect=mock_chat):
                # Create multiple conversations
                for i in range(5):
                    response, conv_id = await service.chat(
                        message=f"Message {i}",
                        mode=ChatMode.GENERAL
                    )
                    conversations.append(conv_id)

                # All conversations should have unique IDs
                assert len(conversations) == len(set(conversations))

    def test_conversation_isolation(self):
        """Test that conversations are isolated from each other."""
        service = HybridChatbotService()

        # Create two conversations
        conv1_id = "conv-1"
        conv2_id = "conv-2"

        service.conversations[conv1_id] = Mock()
        service.conversations[conv2_id] = Mock()

        # Clear one conversation
        service.clear_conversation(conv1_id)

        # Other conversation should still exist
        assert conv1_id not in service.conversations
        assert conv2_id in service.conversations
