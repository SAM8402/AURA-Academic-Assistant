<template>
  <div class="flex h-screen" :style="{ backgroundColor: 'var(--page-bg)', color: 'var(--text-primary)' }">
    <!-- Sidebar -->
    <Sidebar />

    <!-- Main Content -->
    <div class="flex flex-col flex-1 min-h-screen">
      <!-- HeaderBar with sidebar offset -->
      <div class="ml-[250px]">
        <HeaderBar />
      </div>

      <!-- Body Section -->
      <div class="d-flex flex-grow-1 overflow-hidden">
        <!-- Main content container -->
        <main class="flex-1 overflow-y-auto p-6 ml-[250px]">
          <!-- DASHBOARD PAGE -->
          <section v-show="activePage === 'dashboard'" class="space-y-6">
            <!-- Hero -->
            <div class="rounded-xl p-6 shadow" :style="{ background: 'linear-gradient(135deg, var(--accent-blue), var(--accent-purple))', color: '#ffffff' }">
              <h2 class="text-2xl font-bold mb-1">Welcome back, {{ userName }}!</h2>
              <p class="opacity-90">Here is what is happening with your academics today.</p>
            </div>

            <!-- Loading State -->
            <LoadingSpinner v-if="isLoading" :fullPage="true" text="Loading your dashboard..." size="lg" />

            <!-- Error State -->
            <div v-else-if="error" class="rounded-xl p-6 border" :style="{ backgroundColor: 'var(--error-bg)', borderColor: 'var(--accent-red)' }">
              <h3 class="font-semibold mb-2" :style="{ color: 'var(--error-text)' }">Error Loading Dashboard</h3>
              <p class="text-sm" :style="{ color: 'var(--text-secondary)' }">{{ error }}</p>
              <button
                @click="loadDashboardData"
                class="mt-4 px-4 py-2 rounded-lg text-white text-sm font-medium transition-opacity duration-200 cursor-pointer min-h-[44px]"
                :style="{ backgroundColor: 'var(--accent-red)' }"
                aria-label="Retry loading dashboard"
              >
                Retry
              </button>
            </div>

            <!-- Dashboard Content -->
            <template v-else>
              <!-- Stats -->
              <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div
                  v-for="stat in statCards"
                  :key="stat.label"
                  class="rounded-xl p-5 border"
                  :style="{ backgroundColor: 'var(--card-bg)', borderColor: 'var(--card-border)' }"
                >
                  <div class="flex items-center justify-between mb-2">
                    <div class="w-9 h-9 rounded-lg flex items-center justify-center" :style="{ backgroundColor: stat.iconBg }">
                      <svg class="w-5 h-5" :style="{ color: stat.iconColor }" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="stat.iconPath" />
                      </svg>
                    </div>
                    <span class="text-2xl font-bold" :style="{ color: 'var(--text-primary)' }">{{ stat.value }}</span>
                  </div>
                  <p class="text-sm" :style="{ color: 'var(--text-secondary)' }">{{ stat.label }}</p>
                  <p class="text-xs mt-1" :style="{ color: stat.subColor }">{{ stat.subLabel }}</p>
                </div>
              </div>

              <!-- Two-column area -->
              <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <!-- Recent Queries -->
                <div class="rounded-xl p-6 border" :style="{ backgroundColor: 'var(--card-bg)', borderColor: 'var(--card-border)' }">
                  <h3 class="text-lg font-semibold mb-4" :style="{ color: 'var(--text-primary)' }">My Recent Queries</h3>
                  <EmptyState
                    v-if="recentQueries.length === 0"
                    title="No queries yet"
                    description="Start asking questions to see your history here."
                  >
                    <template #icon>
                      <svg class="w-8 h-8" :style="{ color: 'var(--text-muted)' }" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </template>
                  </EmptyState>
                  <div v-else class="space-y-3">
                    <div
                      v-for="q in recentQueries"
                      :key="q.title"
                      class="flex items-start p-3 rounded-lg border"
                      :style="{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-light)' }"
                    >
                      <svg class="w-5 h-5 mr-3 mt-1 flex-shrink-0" :style="{ color: 'var(--accent-yellow)' }" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <div class="flex-1 min-w-0">
                        <p class="font-medium" :style="{ color: 'var(--text-primary)' }">{{ q.title }}</p>
                        <p class="text-sm" :style="{ color: 'var(--text-secondary)' }">{{ q.status }}</p>
                        <p class="text-xs mt-1" :style="{ color: 'var(--text-tertiary)' }">{{ formatDate(q.created_at) }}</p>
                      </div>
                      <span class="px-2 py-1 rounded text-xs flex-shrink-0" :class="getStatusClass(q.status)">
                        {{ q.status }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Top Knowledge Sources -->
                <div class="rounded-xl p-6 border" :style="{ backgroundColor: 'var(--card-bg)', borderColor: 'var(--card-border)' }">
                  <h3 class="text-lg font-semibold mb-4" :style="{ color: 'var(--text-primary)' }">Popular Resources</h3>
                  <EmptyState
                    v-if="topSources.length === 0"
                    title="No resources available"
                    description="Resources will appear here once added to the knowledge base."
                  >
                    <template #icon>
                      <svg class="w-8 h-8" :style="{ color: 'var(--text-muted)' }" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                      </svg>
                    </template>
                  </EmptyState>
                  <div v-else class="space-y-3">
                    <div
                      v-for="source in topSources"
                      :key="source.id"
                      class="flex items-start p-3 rounded-lg border"
                      :style="{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-light)' }"
                    >
                      <svg class="w-5 h-5 mr-3 mt-1 flex-shrink-0" :style="{ color: 'var(--accent-blue)' }" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <div class="flex-1 min-w-0">
                        <p class="font-medium" :style="{ color: 'var(--text-primary)' }">{{ source.title }}</p>
                        <p class="text-sm" :style="{ color: 'var(--text-secondary)' }">{{ source.category }}</p>
                        <p class="text-xs mt-1" :style="{ color: 'var(--text-tertiary)' }">{{ source.views || 0 }} views</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Knowledge Sources by Category -->
              <div class="rounded-xl p-6 border" :style="{ backgroundColor: 'var(--card-bg)', borderColor: 'var(--card-border)' }">
                <h3 class="text-lg font-semibold mb-4" :style="{ color: 'var(--text-primary)' }">Resources by Category</h3>
                <div v-if="sourcesByCategory.length === 0" class="text-center py-8">
                  <LoadingSpinner size="sm" text="Loading categories..." />
                </div>
                <div v-else class="space-y-4">
                  <div v-for="cat in sourcesByCategory" :key="cat.category">
                    <div class="flex items-center justify-between mb-2">
                      <div>
                        <p class="font-medium" :style="{ color: 'var(--text-primary)' }">{{ cat.category }}</p>
                        <p class="text-sm" :style="{ color: 'var(--text-tertiary)' }">{{ cat.count }} resources</p>
                      </div>
                      <button
                        @click="viewCategory(cat.category)"
                        class="text-sm font-medium transition-colors duration-200 cursor-pointer min-h-[44px] px-3 flex items-center"
                        :style="{ color: 'var(--accent-blue)' }"
                        @mouseenter="$event.target.style.opacity = '0.8'"
                        @mouseleave="$event.target.style.opacity = '1'"
                      >
                        View All
                        <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
                    </div>
                    <div class="w-full rounded-full h-2" :style="{ backgroundColor: 'var(--bg-tertiary)' }">
                      <div
                        class="h-2 rounded-full transition-all duration-500"
                        :style="{ width: getCategoryPercentage(cat.count) + '%', backgroundColor: 'var(--accent-blue)' }"
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </section>

          <!-- AI ASSISTANT PAGE -->
          <section v-show="activePage === 'ai-assistant'" class="h-full flex flex-col gap-4">
            <div class="rounded-xl p-4 border" :style="{ backgroundColor: 'var(--card-bg)', borderColor: 'var(--card-border)' }">
              <h3 class="font-semibold" :style="{ color: 'var(--text-primary)' }">Enhanced AI Assistant with Knowledge Base</h3>
              <p class="text-sm" :style="{ color: 'var(--text-secondary)' }">Ask questions and get answers from our knowledge base and AI.</p>
              <label class="inline-flex items-center mt-2 cursor-pointer">
                <input
                  type="checkbox"
                  v-model="useKnowledgeBase"
                  class="form-checkbox h-4 w-4 rounded"
                  :style="{ accentColor: 'var(--accent-blue)' }"
                />
                <span class="ml-2 text-sm" :style="{ color: 'var(--text-secondary)' }">Use Knowledge Base (RAG)</span>
              </label>
            </div>

            <div class="flex-1 rounded-xl p-4 flex flex-col border" :style="{ backgroundColor: 'var(--card-bg)', borderColor: 'var(--card-border)' }">
              <div id="chatMessages" class="flex-1 overflow-y-auto p-4 space-y-3">
                <div v-for="(m, i) in messages" :key="i"
                  :class="m.from === 'user' ? 'flex justify-end' : 'flex justify-start'">
                  <div
                    :class="['max-w-xs lg:max-w-md px-4 py-3 rounded-lg', m.from === 'user' ? 'text-white' : '']"
                    :style="m.from === 'user'
                      ? { backgroundColor: 'var(--accent-blue)', color: '#ffffff' }
                      : { backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)' }"
                  >
                    <p class="text-sm whitespace-pre-wrap">{{ m.text }}</p>
                    <div v-if="m.sources && m.sources.length > 0" class="mt-2 pt-2 border-t" :style="{ borderColor: 'var(--border-default)' }">
                      <p class="text-xs font-semibold mb-1" :style="{ color: 'var(--text-secondary)' }">Sources:</p>
                      <ul class="text-xs space-y-1" :style="{ color: 'var(--text-tertiary)' }">
                        <li v-for="source in m.sources" :key="source.title">
                          {{ source.title }} ({{ source.category }})
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>

                <!-- Typing indicator -->
                <div v-if="isTyping" class="flex justify-start">
                  <div class="px-4 py-3 rounded-lg" :style="{ backgroundColor: 'var(--bg-secondary)' }">
                    <div class="flex space-x-2">
                      <div class="w-2 h-2 rounded-full animate-bounce" :style="{ backgroundColor: 'var(--text-muted)' }"></div>
                      <div class="w-2 h-2 rounded-full animate-bounce" :style="{ backgroundColor: 'var(--text-muted)', animationDelay: '0.2s' }"></div>
                      <div class="w-2 h-2 rounded-full animate-bounce" :style="{ backgroundColor: 'var(--text-muted)', animationDelay: '0.4s' }"></div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="p-4 border-t" :style="{ borderColor: 'var(--border-default)' }">
                <div class="flex gap-2">
                  <input
                    v-model="chatInput"
                    @keyup.enter="sendMessage"
                    :disabled="isTyping"
                    placeholder="Ask a question..."
                    class="flex-1 px-4 py-2 rounded-lg border transition-colors duration-200 min-h-[44px]"
                    :style="{
                      backgroundColor: 'var(--input-bg)',
                      borderColor: 'var(--input-border)',
                      color: 'var(--input-text)'
                    }"
                  />
                  <button
                    @click="sendMessage"
                    :disabled="isTyping || !chatInput.trim()"
                    class="px-5 py-2 rounded-lg text-white text-sm font-medium transition-opacity duration-200 cursor-pointer min-h-[44px] disabled:opacity-50 disabled:cursor-not-allowed"
                    :style="{ backgroundColor: 'var(--accent-blue)' }"
                  >
                    {{ isTyping ? 'Sending...' : 'Send' }}
                  </button>
                </div>
              </div>
            </div>
          </section>

          <!-- KNOWLEDGE BASE PAGE -->
          <section v-show="activePage === 'knowledge-base'" class="space-y-6">
            <div class="rounded-xl p-6 border" :style="{ backgroundColor: 'var(--card-bg)', borderColor: 'var(--card-border)' }">
              <h3 class="text-lg font-semibold mb-4" :style="{ color: 'var(--text-primary)' }">Knowledge Base</h3>

              <!-- Search and Filter -->
              <div class="flex gap-4 mb-4">
                <input
                  v-model="knowledgeSearch"
                  @input="searchKnowledge"
                  placeholder="Search resources..."
                  class="flex-1 px-4 py-2 rounded-lg border transition-colors duration-200 min-h-[44px]"
                  :style="{
                    backgroundColor: 'var(--input-bg)',
                    borderColor: 'var(--input-border)',
                    color: 'var(--input-text)'
                  }"
                />
                <select
                  v-model="selectedCategory"
                  @change="filterByCategory"
                  class="px-4 py-2 rounded-lg border transition-colors duration-200 min-h-[44px]"
                  :style="{
                    backgroundColor: 'var(--input-bg)',
                    borderColor: 'var(--input-border)',
                    color: 'var(--input-text)'
                  }"
                >
                  <option value="">All Categories</option>
                  <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
                </select>
              </div>

              <!-- Knowledge Sources List -->
              <EmptyState
                v-if="knowledgeSources.length === 0"
                title="No resources found"
                description="Try adjusting your search or filter criteria."
              >
                <template #icon>
                  <svg class="w-8 h-8" :style="{ color: 'var(--text-muted)' }" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </template>
              </EmptyState>
              <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div
                  v-for="source in knowledgeSources"
                  :key="source.id"
                  class="rounded-lg p-4 border transition-shadow duration-200 cursor-pointer"
                  :style="{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-light)' }"
                  @click="viewSource(source)"
                  @mouseenter="$event.currentTarget.style.boxShadow = '0 4px 12px var(--card-shadow)'"
                  @mouseleave="$event.currentTarget.style.boxShadow = 'none'"
                  tabindex="0"
                  role="button"
                  :aria-label="'View ' + source.title"
                  @keyup.enter="viewSource(source)"
                >
                  <div class="flex items-start justify-between mb-2">
                    <h4 class="font-semibold text-sm" :style="{ color: 'var(--text-primary)' }">{{ source.title }}</h4>
                    <span class="text-xs px-2 py-1 rounded flex-shrink-0 ml-2" :style="{ backgroundColor: 'var(--info-bg)', color: 'var(--info-text)' }">
                      {{ source.category }}
                    </span>
                  </div>
                  <p class="text-sm line-clamp-2" :style="{ color: 'var(--text-secondary)' }">{{ source.description }}</p>
                  <p class="text-xs mt-2" :style="{ color: 'var(--text-tertiary)' }">{{ formatDate(source.created_at) }}</p>
                </div>
              </div>
            </div>
          </section>

          <!-- MY QUERIES PAGE -->
          <section v-show="activePage === 'my-queries'" class="space-y-6">
            <div class="rounded-xl p-6 border" :style="{ backgroundColor: 'var(--card-bg)', borderColor: 'var(--card-border)' }">
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-semibold" :style="{ color: 'var(--text-primary)' }">My Queries</h3>
                <button
                  class="px-4 py-2 rounded-lg text-white text-sm font-medium transition-opacity duration-200 cursor-pointer min-h-[44px]"
                  :style="{ backgroundColor: 'var(--accent-blue)' }"
                >
                  New Query
                </button>
              </div>

              <div v-if="userStats.recent_queries && userStats.recent_queries.length > 0" class="space-y-3">
                <div
                  v-for="query in userStats.recent_queries"
                  :key="query.title"
                  class="p-4 rounded-lg border"
                  :style="{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-light)' }"
                >
                  <div class="flex items-start justify-between">
                    <div class="flex-1">
                      <h4 class="font-semibold" :style="{ color: 'var(--text-primary)' }">{{ query.title }}</h4>
                      <p class="text-sm mt-1" :style="{ color: 'var(--text-secondary)' }">Status: {{ query.status }}</p>
                      <p class="text-xs mt-1" :style="{ color: 'var(--text-tertiary)' }">{{ formatDate(query.created_at) }}</p>
                    </div>
                    <span class="px-3 py-1 rounded text-sm flex-shrink-0" :class="getStatusClass(query.status)">
                      {{ query.status }}
                    </span>
                  </div>
                </div>
              </div>
              <EmptyState
                v-else
                title="No queries yet"
                description="Create your first query to get started."
                actionLabel="New Query"
              >
                <template #icon>
                  <svg class="w-8 h-8" :style="{ color: 'var(--text-muted)' }" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </template>
              </EmptyState>
            </div>
          </section>

          <!-- PROFILE PAGE -->
          <section v-show="activePage === 'profile'" class="space-y-6">
            <div class="rounded-xl p-6 border" :style="{ backgroundColor: 'var(--card-bg)', borderColor: 'var(--card-border)' }">
              <h3 class="text-lg font-semibold mb-4" :style="{ color: 'var(--text-primary)' }">My Profile</h3>
              <div class="space-y-4">
                <div v-for="field in profileFields" :key="field.label">
                  <label class="block text-sm font-medium mb-1" :style="{ color: 'var(--text-secondary)' }">{{ field.label }}</label>
                  <p :style="{ color: 'var(--text-primary)' }">{{ field.value }}</p>
                </div>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  </div>
</template>

<script setup>
import Sidebar from '@/components/layout/StudentLayout/SideBar.vue'
import HeaderBar from '@/components/layout/StudentLayout/HeaderBar.vue'
import LoadingSpinner from '@/components/shared/LoadingSpinner.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import { ref, onMounted, computed } from 'vue'
import { dashboardAPI, knowledgeAPI, tasksAPI, chatbotAPI } from '@/api'
import { useUserStore } from '@/stores/user'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()
const userStore = useUserStore()
const userName = computed(() => userStore.user?.full_name || 'Student')
const userEmail = computed(() => userStore.user?.email || '')
const userRole = computed(() => userStore.user?.role || 'student')

// Page state
const activePage = ref('dashboard')
const pageTitle = ref('Dashboard')

// Dashboard data
const isLoading = ref(false)
const error = ref(null)
const dashboardStats = ref({})
const userStats = ref({})
const topSources = ref([])
const recentQueries = ref([])
const activeTasksCount = ref(0)
const recentQueriesCount = ref(0)
const sourcesByCategory = ref([])

// Knowledge base
const knowledgeSources = ref([])
const knowledgeSearch = ref('')
const selectedCategory = ref('')
const categories = ref([])

// Chatbot
const messages = ref([
  { from: 'bot', text: "Hello! I am your AI Assistant powered by our knowledge base. How can I help you today?" },
])
const chatInput = ref('')
const isTyping = ref(false)
const useKnowledgeBase = ref(true)
const conversationId = ref(null)

// Computed stat cards for cleaner template
const statCards = computed(() => [
  {
    label: 'Available Resources',
    value: dashboardStats.value.total_knowledge_sources || 0,
    subLabel: 'Knowledge Base',
    subColor: 'var(--accent-green)',
    iconPath: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
    iconBg: 'var(--info-bg)',
    iconColor: 'var(--accent-blue)'
  },
  {
    label: 'My Queries',
    value: userStats.value.total_queries || 0,
    subLabel: 'All time',
    subColor: 'var(--accent-green)',
    iconPath: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
    iconBg: 'var(--success-bg)',
    iconColor: 'var(--accent-green)'
  },
  {
    label: 'Active Tasks',
    value: activeTasksCount.value || 0,
    subLabel: 'In Progress',
    subColor: 'var(--accent-green)',
    iconPath: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    iconBg: 'var(--warning-bg)',
    iconColor: 'var(--accent-purple)'
  },
  {
    label: 'Recent Queries',
    value: recentQueriesCount.value || 0,
    subLabel: 'This week',
    subColor: 'var(--accent-green)',
    iconPath: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
    iconBg: 'var(--warning-bg)',
    iconColor: 'var(--accent-yellow)'
  }
])

// Profile fields for cleaner template
const profileFields = computed(() => [
  { label: 'Full Name', value: userName.value },
  { label: 'Email', value: userEmail.value },
  { label: 'Role', value: userRole.value },
  { label: 'Total Queries', value: userStats.value.total_queries || 0 },
  { label: 'Active Tasks', value: userStats.value.active_tasks_count || 0 }
])

const getCategoryPercentage = (count) => {
  const total = dashboardStats.value.total_knowledge_sources || 1
  return Math.round((count / total) * 100)
}

const getStatusClass = (status) => {
  const statusMap = {
    'OPEN': 'status-open',
    'IN_PROGRESS': 'status-in-progress',
    'RESOLVED': 'status-resolved',
    'CLOSED': 'status-closed',
  }
  return statusMap[status] || 'status-closed'
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const showPage = (id) => {
  activePage.value = id
  const titleMap = {
    dashboard: 'Dashboard',
    'ai-assistant': 'AI Assistant',
    'knowledge-base': 'Knowledge Base',
    'my-queries': 'My Queries',
    forum: 'Discussion Forum',
    profile: 'Profile',
  }
  pageTitle.value = titleMap[id] || 'Aura'

  if (id === 'knowledge-base' && knowledgeSources.value.length === 0) {
    loadKnowledgeSources()
  }
}

const loadDashboardData = async () => {
  isLoading.value = true
  error.value = null

  try {
    const stats = await dashboardAPI.getStatistics()
    dashboardStats.value = stats

    const topSourcesData = await dashboardAPI.getTopSources({ limit: 5 })
    topSources.value = topSourcesData.sources || []

    const context = await chatbotAPI.getUserContext()
    userStats.value = context.user_context || {}
    recentQueries.value = userStats.value.recent_queries || []
    recentQueriesCount.value = recentQueries.value.length

    const taskStats = await tasksAPI.getStatistics()
    activeTasksCount.value = taskStats.in_progress_count || 0

    if (stats.sources_by_category) {
      sourcesByCategory.value = Object.entries(stats.sources_by_category).map(([category, count]) => ({
        category,
        count
      }))
    }

    const categoriesData = await knowledgeAPI.getCategories()
    categories.value = categoriesData.categories || []

  } catch (err) {
    console.error('Error loading dashboard:', err)
    error.value = err.message || 'Failed to load dashboard data. Please try again.'
  } finally {
    isLoading.value = false
  }
}

const loadKnowledgeSources = async () => {
  try {
    const params = { limit: 50 }
    if (knowledgeSearch.value) params.search = knowledgeSearch.value
    if (selectedCategory.value) params.category = selectedCategory.value

    const data = await knowledgeAPI.getSources(params)
    knowledgeSources.value = data.sources || []
  } catch (err) {
    console.error('Error loading knowledge sources:', err)
  }
}

const searchKnowledge = () => loadKnowledgeSources()
const filterByCategory = () => loadKnowledgeSources()

const viewCategory = (category) => {
  selectedCategory.value = category
  showPage('knowledge-base')
  loadKnowledgeSources()
}

const viewSource = (source) => {
  alert(`Viewing: ${source.title}\n\n${source.description}\n\nCategory: ${source.category}`)
}

const sendMessage = async () => {
  const text = chatInput.value.trim()
  if (!text || isTyping.value) return

  messages.value.push({ from: 'user', text })
  chatInput.value = ''
  isTyping.value = true

  try {
    const response = await chatbotAPI.sendEnhancedChatMessage({
      message: text,
      conversation_id: conversationId.value,
      use_knowledge_base: useKnowledgeBase.value,
      mode: 'academic'
    })

    conversationId.value = response.conversation_id

    messages.value.push({
      from: 'bot',
      text: response.answer,
      sources: response.sources || []
    })
  } catch (err) {
    console.error('Chat error:', err)
    messages.value.push({
      from: 'bot',
      text: 'Sorry, I encountered an error. Please try again.'
    })
  } finally {
    isTyping.value = false
    setTimeout(() => {
      const chatDiv = document.getElementById('chatMessages')
      if (chatDiv) chatDiv.scrollTop = chatDiv.scrollHeight
    }, 100)
  }
}

onMounted(() => {
  loadDashboardData()
})
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Status badge styles using theme variables */
.status-open {
  background-color: var(--warning-bg);
  color: var(--warning-text);
}
.status-in-progress {
  background-color: var(--info-bg);
  color: var(--info-text);
}
.status-resolved {
  background-color: var(--success-bg);
  color: var(--success-text);
}
.status-closed {
  background-color: var(--bg-tertiary);
  color: var(--text-tertiary);
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}
.animate-bounce {
  animation: bounce 1s infinite;
}
</style>
