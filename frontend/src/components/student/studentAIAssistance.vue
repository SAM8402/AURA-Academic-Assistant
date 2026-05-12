<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { useThemeStore } from '@/stores/theme'
import Sidebar from '@/components/layout/StudentLayout/SideBar.vue'
import BottomBar from '@/components/layout/StudentLayout/BottomBar.vue'
import ChatBubble from '@/components/shared/ChatBubble.vue'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import { sendEnhancedChatMessage, sendEnhancedChatMessageStream, sendRAGChatMessageStream, getChatbotStatus } from '@/api/chatbot'

// State
const messages = ref([])
const userInput = ref('')
const isLoading = ref(false)
const conversationId = ref(null)
const chatMode = ref('academic')
const chatMessagesContainer = ref(null)
const isChatbotAvailable = ref(true)
const useDirectRag = ref(false)
const totalKbSourcesUsed = ref(0)
const latestSources = ref([])

const themeStore = useThemeStore()

// Typewriter effect — buffers chunks and renders char-by-char
const _typewriterQueue = ref('')
let _typewriterTimer = null
const CHAR_DELAY_MS = 30 // ms per character (~33 chars/sec, smooth typing feel)

function startTypewriter(messageIndex) {
  if (_typewriterTimer) return // already running
  _typewriterTimer = setInterval(() => {
    if (_typewriterQueue.value.length > 0) {
      messages.value[messageIndex].content += _typewriterQueue.value.charAt(0)
      _typewriterQueue.value = _typewriterQueue.value.slice(1)
      scrollToBottom()
    }
  }, CHAR_DELAY_MS)
}

function stopTypewriter(messageIndex) {
  clearInterval(_typewriterTimer)
  _typewriterTimer = null
  // Flush remaining buffer immediately
  if (_typewriterQueue.value.length > 0) {
    messages.value[messageIndex].content += _typewriterQueue.value
    _typewriterQueue.value = ''
    scrollToBottom()
  }
}

// Suggested prompts
const suggestedPrompts = [
  'Summarize last CS 301 lecture',
  'Explain Dijkstra with example',
  'Draft study plan for finals',
  'Help me understand recursion'
]

// Initialize with welcome message
onMounted(async () => {
  try {
    await getChatbotStatus()
    isChatbotAvailable.value = true
  } catch (error) {
    console.error('Chatbot not available:', error)
    isChatbotAvailable.value = false
  }

  messages.value.push({
    type: 'assistant',
    content: 'Welcome! Ask about deadlines, resources, or concepts. I can summarize lectures and draft study plans.',
    timestamp: new Date()
  })
})

// Send message
const sendMessage = async () => {
  const messageText = userInput.value.trim()
  if (!messageText) return

  messages.value.push({
    type: 'user',
    content: messageText,
    timestamp: new Date()
  })

  userInput.value = ''
  await nextTick()
  scrollToBottom()
  isLoading.value = true

  const loadingMessageIndex = messages.value.length
  messages.value.push({
    type: 'assistant',
    content: 'Analyzing your question...',
    isLoading: true,
    timestamp: new Date()
  })

  let streamError = null
  let receivedFirstContent = false
  _typewriterQueue.value = '' // Reset queue

  // Handler for incoming chunks — filters status events from content
  const handleChunk = (chunk) => {
    // Status events update the loading indicator
    if (chunk.startsWith('__STATUS__')) {
      const statusText = chunk.slice('__STATUS__'.length)
      if (!receivedFirstContent) {
        messages.value[loadingMessageIndex].content = statusText
      }
      return
    }

    // First real content — swap loading message for streaming response
    if (!receivedFirstContent) {
      receivedFirstContent = true
      messages.value[loadingMessageIndex] = {
        type: 'assistant',
        content: '',
        timestamp: new Date()
      }
      startTypewriter(loadingMessageIndex)
    }

    _typewriterQueue.value += chunk
  }

  if (useDirectRag.value) {
    startTypewriter(loadingMessageIndex)
    // For RAG, swap loading immediately (no status events from RAG pipeline)
    messages.value[loadingMessageIndex] = {
      type: 'assistant',
      content: '',
      timestamp: new Date()
    }
    receivedFirstContent = true

    await sendRAGChatMessageStream({
      message: messageText,
      conversation_id: conversationId.value,
      onChunk: (chunk) => {
        _typewriterQueue.value += chunk
      },
      onMeta: (meta) => {
        if (meta.sources) {
          latestSources.value = meta.sources
          totalKbSourcesUsed.value = meta.sources.length
        }
      },
      onDone: () => {
        stopTypewriter(loadingMessageIndex)
        if (!conversationId.value) {
          conversationId.value = `rag-${Date.now().toString(36)}`
        }
      },
      onError: (error) => {
        stopTypewriter(loadingMessageIndex)
        streamError = error
      }
    })
  } else {
    await sendEnhancedChatMessageStream({
      message: messageText,
      mode: chatMode.value,
      conversation_id: conversationId.value,
      use_knowledge_base: true,
      onChunk: handleChunk,
      onDone: () => {
        stopTypewriter(loadingMessageIndex)
        if (!conversationId.value) {
          conversationId.value = `conv-${Date.now().toString(36)}`
        }
      },
      onError: (error) => {
        stopTypewriter(loadingMessageIndex)
        streamError = error
      }
    })
  }

  if (streamError) {
    messages.value[loadingMessageIndex] = {
      type: 'assistant',
      content: 'Sorry, I encountered an error. Please try again.',
      isError: true,
      timestamp: new Date()
    }
  }

  isLoading.value = false
  await nextTick()
  scrollToBottom()
}

const useSuggestedPrompt = (prompt) => {
  userInput.value = prompt
  sendMessage()
}

const scrollToBottom = () => {
  if (chatMessagesContainer.value) {
    chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight
  }
}

const handleKeyDown = (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

const clearChat = () => {
  messages.value = [{
  type: 'assistant',
  content: 'Conversation cleared. How can I help you today?',
  timestamp: new Date()
  }]
  conversationId.value = null
  totalKbSourcesUsed.value = 0
  latestSources.value = []
}

const changeChatMode = (mode) => {
  chatMode.value = mode
}

const onBottomBarSend = async ({ message, file }) => {
  if (!message?.trim()) return;
  userInput.value = message.trim();
  await sendMessage();
}

// Format timestamp for display
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = timestamp instanceof Date ? timestamp : new Date(timestamp)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="h-screen w-full flex" :style="{ background: 'var(--page-bg)' }">
    <!-- Sidebar -->
    <Sidebar class="fixed top-0 left-0 h-screen w-48 z-20" />

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col ml-[250px] min-w-0">
      <!-- Mode Selection Header -->
      <header class="sticky top-0 z-10 px-9 py-3 border-b" :style="{ background: 'var(--bg-primary)', borderColor: 'var(--border-light)' }">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <h1 class="text-lg font-semibold" :style="{ color: 'var(--text-primary)' }">
              AI Assistant
              <span class="text-sm font-normal ml-2" :style="{ color: 'var(--text-tertiary)' }">
                {{ chatMode.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()) }}
              </span>
            </h1>
          </div>

          <!-- Clear Chat Button -->
          <button
            @click="clearChat"
            class="px-3 py-1.5 rounded-md transition-colors duration-200 text-sm font-medium flex items-center gap-2 whitespace-nowrap cursor-pointer min-h-[44px]"
            :style="{ color: 'var(--accent-red)' }"
            @mouseenter="$event.target.style.backgroundColor = 'var(--bg-hover)'"
            @mouseleave="$event.target.style.backgroundColor = 'transparent'"
            aria-label="Clear chat conversation"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Clear Chat
          </button>
        </div>
      </header>

      <!-- Content -->
      <div class="flex-1 flex overflow-hidden">
        <!-- Central Chat Section -->
        <section class="flex flex-col flex-1 overflow-hidden relative">
          <div ref="chatMessagesContainer" class="flex-1 overflow-y-auto px-5 py-3 space-y-4">
            <!-- Message Loop -->
            <div class="space-y-3">
              <ChatBubble
                v-for="(message, index) in messages"
                :key="index"
                :message="message"
                :isUser="message.type === 'user'"
                :isDark="themeStore.currentTheme === 'dark'"
              />
            </div>

            <!-- Empty state when only welcome message -->
            <EmptyState
              v-if="messages.length === 1"
              title="Start a conversation"
              description="Ask AURA about deadlines, resources, or concepts. I can summarize lectures and draft study plans."
            >
              <template #icon>
                <svg class="w-8 h-8" :style="{ color: 'var(--text-muted)' }" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </template>
            </EmptyState>

            <!-- Spacer to prevent bottom bar overlap -->
            <div class="h-32"></div>
          </div>

          <!-- Fixed Bottom Bar for message input -->
          <BottomBar @send="onBottomBarSend" />
        </section>

        <!-- Right Sidebar -->
        <aside
          class="w-80 flex-shrink-0 flex flex-col gap-5 p-4 overflow-y-auto border-l"
          :style="{ maxHeight: 'calc(100vh - 140px)', borderColor: 'var(--border-light)', background: 'var(--bg-secondary)' }"
        >
          <!-- Current Mode -->
          <div class="rounded-2xl shadow p-5 border" :style="{ background: 'var(--card-bg)', borderColor: 'var(--card-border)' }">
            <h3 class="text-base font-semibold mb-4" :style="{ color: 'var(--text-primary)' }">Engine Mode</h3>
            <div class="grid grid-cols-2 gap-3">
              <button
                v-for="mode in [
                  { key: 'academic', label: 'Academic' },
                  { key: 'study_help', label: 'Study Help' },
                  { key: 'doubt_clarification', label: 'Doubt Clarification' },
                  { key: 'general', label: 'General' }
                ]"
                :key="mode.key"
                @click="changeChatMode(mode.key)"
                :class="[
                  'px-2 py-3 rounded-lg text-xs transition-all duration-200 text-center min-h-[44px] flex items-center justify-center border-2 cursor-pointer font-medium',
                ]"
                :style="chatMode === mode.key
                  ? { backgroundColor: 'var(--accent-blue)', borderColor: 'var(--accent-blue)', color: '#ffffff' }
                  : { backgroundColor: 'var(--card-bg)', borderColor: 'var(--border-default)', color: 'var(--text-secondary)' }"
              >
                {{ mode.label }}
              </button>
            </div>
            <p class="text-xs mt-4" :style="{ color: 'var(--text-tertiary)' }">
              <span v-if="chatMode === 'academic'">Get clear, educational explanations with examples.</span>
              <span v-else-if="chatMode === 'doubt_clarification'">Step-by-step help to clarify your doubts.</span>
              <span v-else-if="chatMode === 'study_help'">Study strategies, time management, and learning techniques.</span>
              <span v-else>General helpful responses for any question.</span>
            </p>
          </div>

          <!-- Direct RAG Toggle -->
          <div class="rounded-2xl shadow p-5 border" :style="{ background: 'var(--card-bg)', borderColor: 'var(--card-border)' }">
            <h3 class="text-base font-semibold mb-3" :style="{ color: 'var(--text-primary)' }">Query Strategy</h3>
            <div class="flex gap-2">
              <button
                @click="useDirectRag = false"
                class="flex-1 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-200 border-2 cursor-pointer min-h-[44px]"
                :style="!useDirectRag
                  ? { backgroundColor: 'var(--accent-blue)', borderColor: 'var(--accent-blue)', color: '#ffffff' }
                  : { backgroundColor: 'var(--card-bg)', borderColor: 'var(--border-default)', color: 'var(--text-secondary)' }"
              >
                Agentic
              </button>
              <button
                @click="useDirectRag = true"
                class="flex-1 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-200 border-2 cursor-pointer min-h-[44px]"
                :style="useDirectRag
                  ? { backgroundColor: 'var(--accent-blue)', borderColor: 'var(--accent-blue)', color: '#ffffff' }
                  : { backgroundColor: 'var(--card-bg)', borderColor: 'var(--border-default)', color: 'var(--text-secondary)' }"
              >
                Direct RAG
              </button>
            </div>
            <p class="text-xs mt-3" :style="{ color: 'var(--text-tertiary)' }">
              <span v-if="useDirectRag">Fast, direct RAG pipeline without tool calls. Best for factual Q&A.</span>
              <span v-else>Full agentic mode with function calling, web search, and query lookups.</span>
            </p>
          </div>

          <!-- Suggested Prompts -->
          <div class="rounded-2xl shadow p-5 border" :style="{ background: 'var(--card-bg)', borderColor: 'var(--card-border)' }">
            <h3 class="text-base font-semibold mb-3" :style="{ color: 'var(--text-primary)' }">Suggested Prompts</h3>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="(prompt, index) in suggestedPrompts"
                :key="index"
                @click="useSuggestedPrompt(prompt)"
                class="text-xs px-3 py-2 rounded-full transition-all duration-200 border cursor-pointer min-h-[36px]"
                :style="{
                  backgroundColor: 'var(--bg-tertiary)',
                  color: 'var(--text-primary)',
                  borderColor: 'var(--border-default)'
                }"
                :disabled="isLoading"
                @mouseenter="$event.target.style.backgroundColor = 'var(--bg-hover)'"
                @mouseleave="$event.target.style.backgroundColor = 'var(--bg-tertiary)'"
              >
                {{ prompt }}
              </button>
            </div>
            <p class="text-xs mt-3" :style="{ color: 'var(--text-tertiary)' }">
              Click to use these prompts or type your own question.
            </p>
          </div>

          <!-- Knowledge Sources Used -->
          <div v-if="totalKbSourcesUsed > 0" class="rounded-2xl shadow p-5 border" :style="{ background: 'var(--card-bg)', borderColor: 'var(--card-border)' }">
            <h3 class="text-base font-semibold mb-3" :style="{ color: 'var(--text-primary)' }">Sources Referenced</h3>
            <div class="flex flex-col gap-2">
              <div
                v-for="(src, i) in latestSources.slice(0, 5)"
                :key="i"
                class="flex items-center gap-2 text-xs px-3 py-2 rounded-lg"
                :style="{ backgroundColor: 'var(--bg-tertiary)' }"
              >
                <svg class="w-3.5 h-3.5 flex-shrink-0" :style="{ color: 'var(--accent-blue)' }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
                <span :style="{ color: 'var(--text-primary)' }">{{ src.title || src.source_title || 'Document' }}</span>
              </div>
            </div>
          </div>

          <!-- Conversation Info -->
          <div class="rounded-2xl shadow p-5 border" :style="{ background: 'var(--card-bg)', borderColor: 'var(--card-border)' }">
            <h3 class="text-base font-semibold mb-3" :style="{ color: 'var(--text-primary)' }">Conversation</h3>
            <div class="flex flex-col gap-2 text-sm">
              <div class="flex items-center justify-between">
                <span class="font-medium" :style="{ color: 'var(--text-secondary)' }">Messages:</span>
                <span class="font-semibold" :style="{ color: 'var(--text-primary)' }">{{ messages.length }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="font-medium" :style="{ color: 'var(--text-secondary)' }">KB Sources:</span>
                <span class="font-semibold" :style="{ color: 'var(--text-primary)' }">{{ totalKbSourcesUsed }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="font-medium" :style="{ color: 'var(--text-secondary)' }">Status:</span>
                <span
                  class="font-semibold px-2 py-1 rounded-full text-xs"
                  :style="isChatbotAvailable
                    ? { backgroundColor: 'var(--success-bg)', color: 'var(--success-text)' }
                    : { backgroundColor: 'var(--error-bg)', color: 'var(--error-text)' }"
                >
                  {{ isChatbotAvailable ? 'Connected' : 'Disconnected' }}
                </span>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  </div>
</template>

<style scoped>
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background-color: var(--border-default);
  border-radius: 6px;
}
::-webkit-scrollbar-thumb:hover {
  background-color: var(--border-dark);
}

textarea {
  min-height: 48px;
  line-height: 1.5;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}
.animate-bounce {
  animation: bounce 1s infinite;
}
</style>
