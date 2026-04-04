<template>
  <div class="flex h-screen overflow-hidden" :style="{ color: 'var(--text-primary)' }">
    <!-- Sidebar -->
    <Sidebar class="sticky top-0 h-screen flex-shrink-0" />

    <!-- Main Content -->
    <div class="flex-1 flex flex-col ml-[250px]" :style="{ background: 'var(--page-bg)' }">
      <!-- Header -->
      <HeaderBar class="sticky top-0 z-50" searchPlaceholder="Ask a question..." />

      <!-- Page content -->
      <div class="flex flex-1 overflow-hidden">
        <!-- Center: Chat Area -->
        <section class="flex-1 flex flex-col relative" :style="{ background: 'var(--color-bg-card)' }">
          <!-- Scrollable Conversation -->
          <div class="flex-1 overflow-y-auto p-6 pb-28">
            <div v-if="messages.length === 0" class="flex flex-col items-center justify-center h-full text-center">
              <div class="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                <svg class="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <h3 class="text-xl font-semibold mb-2" :style="{ color: 'var(--text-primary)' }">Start a New Query</h3>
              <p class="max-w-md" :style="{ color: 'var(--text-primary)' }">
                Ask a question about your coursework, assignments, or concepts. Our AI assistant and instructors are here to help!
              </p>
            </div>

            <!-- Messages -->
            <div v-else class="space-y-6 max-w-4xl mx-auto">
              <ChatBubble
                v-for="(msg, index) in messages"
                :key="index"
                :message="{ content: msg.content, timestamp: msg.timestamp, file: msg.file }"
                :isUser="msg.type === 'user'"
                :isDark="themeStore.currentTheme === 'dark'"
              />

              <!-- Typing Indicator (theme-aware) -->
              <div v-if="isTyping" class="flex items-start gap-4">
                <div class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0" :style="{ backgroundColor: 'var(--color-accent, #2563eb)', color: 'white' }">
                  <span class="font-semibold text-sm text-white">AI</span>
                </div>
                <div class="flex-1">
                  <div class="text-xs font-semibold mb-1 text-purple-900">AI Assistant</div>
                  <div class="inline-block px-4 py-3 rounded-2xl rounded-tl-sm" :style="{ background: 'var(--color-bg-card)' }">
                    <div class="flex gap-1">
                      <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                      <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                      <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Right: Recent Chats Panel -->
        <aside class="w-64 overflow-y-auto flex-shrink-0" :style="{ background: 'var(--color-bg-card)', borderLeft: '1px solid var(--color-border)' }">
          <div class="p-4">
            <div class="flex items-center justify-between mb-4">
              <h3 class="font-bold text-lg">Recent Chats</h3>
              <button
                @click="startNewChat"
                class="p-1.5 rounded-lg hover:bg-gray-100 transition"
                title="New Chat"
              >
                <svg class="w-5 h-5" :style="{ color: 'var(--text-primary)' }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
              </button>
            </div>

            <div class="space-y-2">
              <div
                v-for="(chat, index) in recentChats"
                :key="index"
                @click="loadChat(chat)"
                class="p-3 rounded-xl border cursor-pointer transition"
                :style="currentChatId === chat.id ? { background: 'var(--color-highlight, var(--color-bg-card))', borderColor: 'var(--color-border)' } : { background: 'var(--color-bg-card)', borderColor: 'var(--color-border)' }"
              >
                <div class="font-semibold text-sm line-clamp-1 mb-1" :style="{ color: 'var(--color-text-primary)' }">{{ chat.title }}</div>
                <div class="text-xs line-clamp-2 mb-1" :style="{ color: 'var(--color-text-secondary)' }">{{ chat.preview }}</div>
                <div class="flex items-center justify-between text-xs" :style="{ color: 'var(--color-text-secondary)' }">
                  <span>{{ chat.time }}</span>
                  <span class="px-2 py-0.5 rounded-full" :class="chat.status === 'Open' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'">
                    {{ chat.status }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>

      <!-- Bottom Bar -->
      <BottomBar
        @send-message="handleSendMessage"
        @file-attached="handleFileAttached"
      />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useThemeStore } from '@/stores/theme'
import Sidebar from '@/components/layout/StudentLayout/SideBar.vue'
import HeaderBar from '@/components/layout/StudentLayout/HeaderBar.vue'
import BottomBar from '@/components/layout/StudentLayout/BottomBar.vue'
import ChatBubble from '@/components/shared/ChatBubble.vue'

const messages = ref([])
const isTyping = ref(false)
const currentChatId = ref(null)

const themeStore = useThemeStore()

const recentChats = ref([
  {
    id: 1,
    title: 'Dijkstra complexity help',
    preview: 'I implemented the algorithm but still see O(n²)...',
    time: '2h ago',
    status: 'Open',
    messages: []
  },
  {
    id: 2,
    title: 'Docker build error',
    preview: 'Getting permission denied on ARM machine...',
    time: 'Yesterday',
    status: 'Resolved',
    messages: []
  },
  {
    id: 3,
    title: 'Binary tree traversal',
    preview: 'Need help understanding in-order traversal...',
    time: '2d ago',
    status: 'Open',
    messages: []
  },
  {
    id: 4,
    title: 'SQL join queries',
    preview: 'Left join vs inner join explanation...',
    time: '3d ago',
    status: 'Resolved',
    messages: []
  }
])

const handleSendMessage = ({ message, file }) => {
  if (!message.trim() && !file) return

  // Add user message
  const timestamp = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  messages.value.push({
    type: 'user',
    content: message,
    file: file,
    timestamp: timestamp
  })

  // Simulate AI typing
  isTyping.value = true

  setTimeout(() => {
    isTyping.value = false
    messages.value.push({
      type: 'ai',
      content: generateAIResponse(message),
      timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    })

    // Auto-scroll to bottom
    setTimeout(() => {
      const chatContainer = document.querySelector('.overflow-y-auto')
      if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight
      }
    }, 100)
  }, 1500)
}

const handleFileAttached = (file) => {
  console.log('File attached:', file)
}

const generateAIResponse = (question) => {
  // Simple AI response simulation
  const responses = [
    "I understand your question. Let me help you with that. Based on the context you've provided, here's what I suggest...",
    "Great question! This is a common issue that many students face. Here's a detailed explanation...",
    "I can help you with this. Let's break down the problem step by step...",
    "That's an interesting query! Here's what you need to know about this topic..."
  ]
  return responses[Math.floor(Math.random() * responses.length)]
}

const startNewChat = () => {
  messages.value = []
  currentChatId.value = null
}

const loadChat = (chat) => {
  currentChatId.value = chat.id
  messages.value = chat.messages || []
}
</script>

<style scoped>
.line-clamp-1 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  line-clamp: 1;
  -webkit-line-clamp: 1;
  overflow: hidden;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  line-clamp: 2;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-0.5rem);
  }
}

.animate-bounce {
  animation: bounce 1s infinite;
}
</style>