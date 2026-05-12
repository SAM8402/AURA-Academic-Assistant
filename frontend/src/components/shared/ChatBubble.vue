<script setup>
import { computed, ref } from 'vue'
import MarkdownIt from 'markdown-it'

const props = defineProps({
  message: { type: Object, required: true },
  isUser: { type: Boolean, default: false },
  isDark: { type: Boolean, default: false }
})

const copied = ref(false)

// Initialize markdown renderer
const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true
})

const renderedContent = computed(() => {
  if (props.message.isLoading || props.message.isError) {
    return props.message.content
  }
  return md.render(props.message.content || '')
})

const isLoading = computed(() => !!props.message.isLoading)
const isError = computed(() => !!props.message.isError)

const hasSources = computed(() => props.message.sources && props.message.sources.length > 0)
const kbCount = computed(() => props.message.knowledgeSourcesUsed || 0)

const bubbleClass = computed(() => {
  let base = 'rounded-2xl px-5 py-4 chat-bubble'
  if (isError.value) {
    base += ' chat-bubble-error'
  } else if (isLoading.value) {
    base += ' chat-bubble-loading'
  } else {
    base += ' chat-bubble-normal'
  }
  base += props.isDark ? ' blue-shadow' : ' default-shadow'
  return base
})

const userBubbleClass = computed(() => {
  let base = 'rounded-2xl px-5 py-3 text-sm chat-bubble-user'
  base += props.isDark ? ' blue-shadow' : ' default-shadow'
  return base
})

const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(props.message.content || '')
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    // Fallback
    const ta = document.createElement('textarea')
    ta.value = props.message.content || ''
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  }
}
</script>

<template>
  <div :class="['flex items-start', isUser ? 'justify-end' : '']">
    <template v-if="!isUser">
      <img
        src="https://randomuser.me/api/portraits/lego/2.jpg"
        class="w-10 h-10 rounded-full mr-2 mt-1 flex-shrink-0"
        alt="AI Assistant"
      />
      <div class="flex-1 max-w-3xl">
        <div :class="bubbleClass">
          <!-- Loading state -->
          <div v-if="isLoading" class="flex items-center gap-2">
            <div class="flex gap-1">
              <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
              <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></span>
              <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.4s"></span>
            </div>
            <span class="text-sm">{{ message.content }}</span>
          </div>
          <!-- Response content -->
          <div v-else>
            <div v-html="renderedContent"></div>
            <!-- Knowledge source indicator -->
            <div v-if="kbCount > 0" class="mt-3 pt-3 border-t" :style="{ borderColor: 'var(--border-light)' }">
              <div class="flex items-center gap-2 text-xs" :style="{ color: 'var(--text-tertiary)' }">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
                <span>{{ kbCount }} knowledge source(s) used</span>
              </div>
              <div v-if="hasSources" class="flex flex-wrap gap-1.5 mt-1.5">
                <span
                  v-for="(src, i) in message.sources.slice(0, 3)"
                  :key="i"
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                  :style="{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--accent-blue)' }"
                >
                  {{ src.title || src.source_title || 'Source' }}
                </span>
                <span v-if="message.sources.length > 3" class="text-xs" :style="{ color: 'var(--text-tertiary)' }">
                  +{{ message.sources.length - 3 }} more
                </span>
              </div>
            </div>
          </div>
        </div>
        <!-- Footer: timestamp + copy -->
        <div class="flex items-center justify-between mt-1">
          <span class="text-xs" :style="{ color: 'var(--text-tertiary)' }">
            {{ (message.timestamp && typeof message.timestamp === 'string') ? new Date(message.timestamp).toLocaleTimeString() : (message.timestamp ? message.timestamp.toLocaleTimeString() : '') }}
          </span>
          <button
            v-if="!isLoading && message.content"
            @click="copyToClipboard"
            class="text-xs flex items-center gap-1 px-2 py-0.5 rounded transition-colors"
            :style="{ color: 'var(--text-tertiary)' }"
            @mouseenter="$event.target.style.backgroundColor = 'var(--bg-hover)'"
            @mouseleave="$event.target.style.backgroundColor = 'transparent'"
          >
            <svg v-if="!copied" class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <svg v-else class="w-3.5 h-3.5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            {{ copied ? 'Copied!' : 'Copy' }}
          </button>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="flex flex-col items-end max-w-3xl">
        <div :class="userBubbleClass">{{ message.content }}</div>
        <span class="text-xs text-gray-400 mt-1 block">
          {{ (message.timestamp && typeof message.timestamp === 'string') ? new Date(message.timestamp).toLocaleTimeString() : (message.timestamp ? message.timestamp.toLocaleTimeString() : '') }}
        </span>
      </div>
      <img
        src="https://randomuser.me/api/portraits/men/36.jpg"
        class="w-10 h-10 rounded-full ml-2 mt-1 flex-shrink-0"
        alt="You"
      />
    </template>
  </div>
</template>

<style scoped>
@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}
.animate-bounce { animation: bounce 1s infinite; }

.blue-shadow {
  box-shadow: 0 2px 12px 0 rgba(37, 99, 235, 0.2), 0 1px 3px 0 rgba(37, 99, 235, 0.15);
}
.default-shadow {
  box-shadow: 0 2px 8px 0 rgba(0,0,0,0.08);
}

/* Theme-aware chat bubble styles */
.chat-bubble {
  background: var(--card-bg);
  color: var(--text-primary);
}

.chat-bubble-error {
  background: var(--error-bg);
  color: var(--error-text);
}

.chat-bubble-loading {
  background: var(--card-bg);
  color: var(--text-secondary);
}

.chat-bubble-normal {
  background: var(--card-bg);
  color: var(--text-primary);
}

.chat-bubble-user {
  background: var(--accent-blue);
  color: white;
}

/* Markdown content styling */
:deep(p) {
  margin-bottom: 0.5rem;
}

:deep(p:last-child) {
  margin-bottom: 0;
}

:deep(ul), :deep(ol) {
  margin-left: 1rem;
  margin-bottom: 0.5rem;
}

:deep(li) {
  margin-bottom: 0.25rem;
}

:deep(code) {
  background-color: rgba(0, 0, 0, 0.1);
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.875em;
}

:deep(pre) {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 0.75rem;
  border-radius: 0.375rem;
  overflow-x: auto;
  margin: 0.5rem 0;
}

:deep(pre code) {
  background-color: transparent;
  padding: 0;
}

:deep(blockquote) {
  border-left: 3px solid rgba(0, 0, 0, 0.2);
  padding-left: 0.75rem;
  margin: 0.5rem 0;
  font-style: italic;
}

:deep(strong) {
  font-weight: 600;
}

:deep(em) {
  font-style: italic;
}

:deep(a) {
  color: #3b82f6;
  text-decoration: underline;
}

:deep(a:hover) {
  color: #2563eb;
}
</style>
