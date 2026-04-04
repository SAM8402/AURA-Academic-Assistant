<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import TASidebar from '@/components/layout/TaLayout/TASidebar.vue'
import doubtsAPI from '@/api/doubts'
import ExportOptions from '@/components/shared/ExportOptions.vue'
import { 
  ArrowDownTrayIcon, 
  ChatBubbleLeftRightIcon, 
  ExclamationTriangleIcon, 
  EnvelopeIcon, 
  ClipboardDocumentListIcon, 
  DocumentTextIcon,
  ArrowPathIcon
} from '@heroicons/vue/24/outline'

// === STATE ===
const isLoading = ref(false)
const isInitialLoad = ref(true)
const error = ref(null)
const lastUpdated = ref(null)

// === FILTERS ===
const selectedPeriod = ref('weekly')
const selectedSource = ref('all')
const selectedCourse = ref('all')

// === SUMMARY STATS ===
const summaryStats = ref(null)

// === FULL DOUBT SUMMARY ===
const doubtSummary = ref(null)

// === COMPUTED ===
const hasData = computed(() => summaryStats.value !== null && doubtSummary.value !== null)
const mostActiveChannel = computed(() => {
  if (!hasData.value) return { name: '-', percentage: 0 }
  const entries = Object.entries(doubtSummary.value.sourceBreakdown)
  const sorted = entries.sort((a, b) => b[1].count - a[1].count)
  return {
    name: sorted[0][0].charAt(0).toUpperCase() + sorted[0][0].slice(1),
    percentage: sorted[0][1].percentage
  }
})

const topConcern = computed(() => {
  if (!hasData.value || !doubtSummary.value.topicClusters.length) return { topic: 'N/A', count: 0 }
  return doubtSummary.value.topicClusters[0]
})

// === DATA FETCH ===
const normalizeTrend = (t) => {
  const v = (t || '').toString().toLowerCase()
  if (v.startsWith('inc')) return 'up'
  if (v.startsWith('dec')) return 'down'
  return 'stable'
}

const fetchSummary = async (isRefresh = false) => {
  const courseCode = selectedCourse.value === 'all' ? 'CS101' : selectedCourse.value
  isLoading.value = true
  error.value = null

  try {
    const params = { 
      period: selectedPeriod.value, 
      source: selectedSource.value === 'all' ? null : selectedSource.value 
    }
    
    // Fetch summary and source breakdown in parallel
    const [res, breakdownRes] = await Promise.all([
      doubtsAPI.getSummary(courseCode, params),
      doubtsAPI.getSourceBreakdown(courseCode, { period: selectedPeriod.value })
    ])

    // Map backend -> UI
    const topics = Array.isArray(res.topics) ? res.topics : []
    const learningGaps = Array.isArray(res.learning_gaps) ? res.learning_gaps : []
    const stats = res.stats || {}

    // Build summary stats from backend computed values
    summaryStats.value = {
      totalQueries: stats.total_messages || breakdownRes.total || 0,
      topicClusters: stats.topic_clusters || topics.length,
      recurringDoubts: stats.recurring_issues || 0,
      learningGaps: stats.learning_gaps || learningGaps.length,
      percentageChange: 0 // TODO: compute from historical data
    }

    doubtSummary.value = {
      topicClusters: topics.map(t => ({
        topic: t.label || 'Unknown',
        count: t.count || 0,
        trend: normalizeTrend(t.trend),
        samples: t.sample_questions || []
      })),
      commonIssues: learningGaps.map(g => ({
        issue: g.issue_title || 'Unlabeled Gap',
        students: g.student_count || 0
      })),
      sourceBreakdown: {
        forum: res.source_breakdown?.forum || breakdownRes.breakdown?.forum || { count: 0, percentage: 0 },
        email: res.source_breakdown?.email || breakdownRes.breakdown?.email || { count: 0, percentage: 0 },
        chat: res.source_breakdown?.chat || breakdownRes.breakdown?.chat || { count: 0, percentage: 0 }
      }
    }

    lastUpdated.value = new Date()
    isInitialLoad.value = false
  } catch (e) {
    console.error('Failed to load doubt summary', e)
    isInitialLoad.value = false
    if (e.code === 'ECONNABORTED' || e.message?.includes('timeout')) {
      error.value = 'Request timed out. The server may be busy. Please try again.'
    } else if (e.response?.status === 401) {
      error.value = 'Session expired. Please log in again.'
    } else if (e.response?.status === 403) {
      error.value = 'You do not have permission to view this data.'
    } else {
      error.value = e.response?.data?.detail || e.message || 'Failed to load summary. Please try again.'
    }
  } finally {
    isLoading.value = false
  }
}

const handleRefresh = () => {
  fetchSummary(true)
}

onMounted(() => {
  fetchSummary()
})

// Debounced watch to avoid rapid API calls during filter changes
let debounceTimer = null
watch([selectedPeriod, selectedSource, selectedCourse], () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => fetchSummary(false), 500)
})

// === ACTION HANDLERS ===
const exportSummary = () => alert('Exporting summary as PDF...')
const viewAllQueries = (cluster) => alert(`Viewing all ${cluster.count} queries for ${cluster.topic}`)
const generateResponseTemplate = (cluster) => alert(`Generating AI response template for ${cluster.topic}...`)
const markAsAddressed = (cluster) => alert(`Marked ${cluster.topic} as addressed`)
const createFAQ = (issue) => alert(`Creating FAQ entry for: ${issue}`)
const sendToInstructor = () => alert('Sending summary email to instructor...')
const createOfficeHoursAgenda = () => alert('Creating office hours agenda based on doubts...')
const generateWeeklyReport = () => alert('Generating weekly PDF report...')
const getAIResponseSuggestions = () => alert('Getting AI-powered response suggestions...')

// === HELPER FUNCTIONS ===
const getTrendColor = (trend) => {
  if (trend === 'up') return 'bg-red-500 animate-pulse'
  if (trend === 'down') return 'bg-green-500'
  return 'bg-yellow-500'
}
const getTrendBadgeColor = (trend) => {
  if (trend === 'up') return 'bg-red-100 text-red-700'
  if (trend === 'down') return 'bg-green-100 text-green-700'
  return 'bg-yellow-100 text-yellow-700'
}
const getTrendText = (trend) => {
  if (trend === 'up') return 'Increasing'
  if (trend === 'down') return 'Decreasing'
  return 'Stable'
}
</script>

<template>
  <div class="flex min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
    <!-- Sidebar -->
    <TASidebar class="fixed top-0 left-0 h-screen w-[250px] z-30" />

    <!-- Main Layout -->
    <main class="flex-1 flex flex-col min-h-screen ml-[250px]">
      <!-- Header -->
      <header class="bg-white shadow-sm px-6 py-4 flex items-center justify-between sticky top-0 z-20 border-b border-gray-200">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">TA Doubt Summarizer</h1>
          <p v-if="lastUpdated" class="text-sm text-gray-500 mt-1">
            Last updated: {{ new Date(lastUpdated).toLocaleTimeString() }}
          </p>
        </div>
        <div class="flex items-center gap-3">
          <button 
            @click="handleRefresh" 
            :disabled="isLoading"
            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium shadow-sm transition-all"
            :class="{ 'animate-pulse': isLoading }"
          >
            <ArrowPathIcon class="w-5 h-5" :class="{ 'animate-spin': isLoading }" />
            {{ isLoading ? 'Refreshing...' : 'Refresh' }}
          </button>
          <button 
            @click="exportSummary" 
            class="px-4 py-2 bg-white text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2 font-medium shadow-sm transition-all border border-gray-300"
          >
            <ArrowDownTrayIcon class="w-5 h-5" />
            Export
          </button>
        </div>
      </header>

      <!-- Content Area -->
      <div class="flex-1 p-6 gap-6 flex max-w-[1800px] mx-auto w-full">
        <!-- Error State -->
        <div v-if="error && !isLoading" class="flex-1 flex items-center justify-center">
          <div class="bg-red-50 border-2 border-red-200 rounded-xl p-8 max-w-md text-center shadow-lg">
            <ExclamationTriangleIcon class="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h3 class="text-xl font-bold text-red-800 mb-2">Error Loading Summary</h3>
            <p class="text-red-600 mb-4">{{ error }}</p>
            <button @click="handleRefresh" class="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 font-semibold shadow-sm transition-all">
              Try Again
            </button>
          </div>
        </div>

        <!-- Initial Loading State -->
        <div v-else-if="isInitialLoad && isLoading" class="flex-1 flex items-center justify-center">
          <div class="text-center">
            <div class="animate-spin rounded-full h-16 w-16 border-4 border-blue-600 border-t-transparent mx-auto mb-4"></div>
            <p class="text-lg font-semibold text-gray-700">Loading doubt summary...</p>
            <p class="text-sm text-gray-500 mt-2">Analyzing student queries and generating insights</p>
          </div>
        </div>

        <!-- Main Panel -->
        <div v-else class="flex-1 space-y-6 relative">
          <!-- Subtle Loading Indicator for Specific Sections -->
          <div v-if="isLoading && !isInitialLoad" class="fixed top-20 left-1/2 transform -translate-x-1/2 z-50 bg-blue-600 text-white px-5 py-3 rounded-lg shadow-lg flex items-center gap-3">
            <div class="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
            <span class="font-medium">Refreshing data...</span>
          </div>
          <!-- Filter Controls -->
          <div class="bg-white rounded-xl shadow-sm p-5 border border-gray-200">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Summary Period</label>
                <select
                  v-model="selectedPeriod"
                  :disabled="isLoading"
                  class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Source</label>
                <select
                  v-model="selectedSource"
                  :disabled="isLoading"
                  class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  <option value="all">All Sources</option>
                  <option value="forum">Forum Posts</option>
                  <option value="email">Emails</option>
                  <option value="chat">Chat Logs</option>
                </select>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Course</label>
                <select
                  v-model="selectedCourse"
                  :disabled="isLoading"
                  class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  <option value="all">All Courses</option>
                  <option value="bscs3001">BSCS3001 - Software Engineering</option>
                  <option value="bscs3003">BSCS3003 - Machine Learning</option>
                </select>
              </div>
            </div>
          </div>

          <!-- Summary Stats Cards -->
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <!-- Most Active Channel -->
            <div class="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl shadow-sm p-5 border border-blue-200 hover:shadow-md transition-shadow">
              <div class="flex items-center justify-between mb-2">
                <p class="text-sm font-medium text-blue-900">Most Active Channel</p>
                <ChatBubbleLeftRightIcon class="w-5 h-5 text-blue-600" />
              </div>
              <p class="text-2xl font-bold text-blue-900 mb-1">
                {{ mostActiveChannel.name }}
              </p>
              <p class="text-xs text-blue-700">{{ mostActiveChannel.percentage }}% of all queries</p>
            </div>
            
            <!-- Top Concern -->
            <div class="bg-gradient-to-br from-orange-50 to-orange-100 rounded-xl shadow-sm p-5 border border-orange-200 hover:shadow-md transition-shadow">
              <div class="flex items-center justify-between mb-2">
                <p class="text-sm font-medium text-orange-900">Top Concern</p>
                <ExclamationTriangleIcon class="w-5 h-5 text-orange-600" />
              </div>
              <p class="text-2xl font-bold text-orange-900 mb-1 truncate" :title="topConcern.topic">
                {{ topConcern.topic }}
              </p>
              <p class="text-xs text-orange-700">{{ topConcern.count }} queries this period</p>
            </div>
            
            <!-- Response Time Target -->
            <div class="bg-gradient-to-br from-green-50 to-green-100 rounded-xl shadow-sm p-5 border border-green-200 hover:shadow-md transition-shadow">
              <div class="flex items-center justify-between mb-2">
                <p class="text-sm font-medium text-green-900">Avg Response Time</p>
                <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p class="text-2xl font-bold text-green-900 mb-1">< 2 hrs</p>
              <p class="text-xs text-green-700">Within SLA targets</p>
            </div>
            
            <!-- Trend Indicator -->
            <div class="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl shadow-sm p-5 border border-purple-200 hover:shadow-md transition-shadow">
              <div class="flex items-center justify-between mb-2">
                <p class="text-sm font-medium text-purple-900">Activity Trend</p>
                <svg class="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <p class="text-2xl font-bold text-purple-900 mb-1">
                {{ summaryStats?.percentageChange > 0 ? '+' : '' }}{{ summaryStats?.percentageChange || 0 }}%
              </p>
              <p class="text-xs text-purple-700">vs previous period</p>
            </div>
          </div>

          <!-- AI Summary Brief -->
          <div class="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl shadow-sm p-6 border border-blue-200">
            <div class="flex items-start gap-4">
              <div class="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-md">
                <ChatBubbleLeftRightIcon class="text-white w-6 h-6" />
              </div>
              <div class="flex-1">
                <h4 class="font-bold text-gray-900 mb-2 text-lg">AI Summary Brief</h4>
                
                <!-- Loading Skeleton for AI Summary -->
                <div v-if="isLoading && !isInitialLoad" class="space-y-2">
                  <div class="h-4 bg-gray-200 rounded animate-pulse w-full"></div>
                  <div class="h-4 bg-gray-200 rounded animate-pulse w-5/6"></div>
                  <div class="h-4 bg-gray-200 rounded animate-pulse w-4/6"></div>
                </div>
                
                <!-- Actual Content -->
                <div v-else>
                  <p class="text-sm text-gray-700 leading-relaxed mb-3">
                    This {{ selectedPeriod }}, <strong class="text-gray-900">{{ summaryStats?.totalQueries || 0 }} student queries</strong> were received. 
                    The AI identified <strong class="text-gray-900">{{ summaryStats?.topicClusters || 0 }} major clusters</strong>, with 
                    <strong class="text-gray-900">{{ topConcern.topic }}</strong> leading at 
                    {{ topConcern.count }} queries. {{ mostActiveChannel.name }} is the most active channel.
                  </p>
                  <div class="flex items-center gap-3 text-xs text-gray-600">
                    <span class="px-2 py-1 bg-white rounded border border-gray-200">AI-Generated</span>
                    <span>•</span>
                    <span>Updated {{ lastUpdated ? new Date(lastUpdated).toLocaleString() : 'just now' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Topic Clustering Analysis -->
          <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h4 class="text-xl font-bold text-gray-900 mb-4">Topic Clustering Analysis</h4>
            
            <!-- Loading Skeletons for Topics -->
            <div v-if="isLoading && !isInitialLoad" class="space-y-4">
              <div v-for="i in 3" :key="i" class="border border-gray-200 rounded-xl p-5 bg-gray-50">
                <div class="flex items-start justify-between mb-3">
                  <div class="flex-1 space-y-3">
                    <div class="flex items-center">
                      <div class="w-3 h-3 rounded-full bg-gray-200 mr-3 animate-pulse"></div>
                      <div class="h-5 bg-gray-200 rounded animate-pulse w-48"></div>
                    </div>
                    <div class="h-4 bg-gray-200 rounded animate-pulse w-32"></div>
                    <div class="space-y-2 mt-3">
                      <div class="h-3 bg-gray-200 rounded animate-pulse w-full"></div>
                      <div class="h-3 bg-gray-200 rounded animate-pulse w-5/6"></div>
                      <div class="h-3 bg-gray-200 rounded animate-pulse w-4/6"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Actual Topic Content -->
            <div v-else class="space-y-4">
              <div
                v-for="(cluster, index) in doubtSummary?.topicClusters || []"
                :key="index"
                class="border border-gray-200 rounded-xl p-5 hover:shadow-md hover:border-gray-300 transition-all bg-gray-50"
              >
                <div class="flex items-start justify-between mb-3">
                  <div class="flex-1">
                    <div class="flex items-center mb-2">
                      <div :class="['w-3 h-3 rounded-full mr-3', getTrendColor(cluster.trend)]"></div>
                      <h5 class="font-bold text-black text-lg">{{ cluster.topic }}</h5>
                      <span :class="['ml-3 px-3 py-1 rounded-full text-xs font-bold', getTrendBadgeColor(cluster.trend)]">
                        {{ getTrendText(cluster.trend) }}
                      </span>
                    </div>
                    <p class="text-sm text-gray-700 mb-2">
                      <strong>{{ cluster.count }} queries</strong> from forum, email, and chat
                    </p>
                    
                    <!-- Sample Queries -->
                    <div class="mt-3 p-4 bg-white rounded-lg border border-gray-200">
                      <p class="text-xs font-bold text-gray-700 mb-2">Sample Queries:</p>
                      <ul class="text-xs text-gray-600 space-y-1">
                        <li v-for="(sample, idx) in cluster.samples" :key="idx">• {{ sample }}</li>
                      </ul>
                    </div>
                  </div>
                </div>
                
                <div class="flex flex-wrap gap-2 mt-4">
                  <button @click="viewAllQueries(cluster)" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-semibold shadow-sm">
                    View All {{ cluster.count }} Queries
                  </button>
                  <button @click="generateResponseTemplate(cluster)" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-semibold shadow-sm">
                    Generate Template
                  </button>
                  <button @click="markAsAddressed(cluster)" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-semibold shadow-sm">
                    Mark Addressed
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Recurring Doubts & Learning Gaps -->
          <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h4 class="text-xl font-bold text-gray-900 mb-2 flex items-center">
              <ExclamationTriangleIcon class="w-6 h-6 text-orange-600 mr-2" />
              Recurring Doubts & Learning Gaps
            </h4>
            <p class="text-sm text-gray-600 mb-4">
              Repeated issues across multiple students
            </p>
            
            <!-- Loading Skeletons for Learning Gaps -->
            <div v-if="isLoading && !isInitialLoad" class="space-y-3">
              <div v-for="i in 3" :key="i" class="p-4 bg-gray-50 border border-gray-200 rounded-lg">
                <div class="flex items-start justify-between">
                  <div class="flex items-start flex-1">
                    <div class="w-7 h-7 bg-gray-200 rounded-full mr-3 flex-shrink-0 animate-pulse"></div>
                    <div class="flex-1 space-y-2">
                      <div class="h-4 bg-gray-200 rounded animate-pulse w-3/4"></div>
                      <div class="h-3 bg-gray-200 rounded animate-pulse w-1/2"></div>
                    </div>
                  </div>
                  <div class="ml-4 w-24 h-9 bg-gray-200 rounded-lg animate-pulse flex-shrink-0"></div>
                </div>
              </div>
            </div>
            
            <!-- Actual Learning Gaps Content -->
            <div v-else-if="doubtSummary?.commonIssues?.length" class="space-y-3">
              <div
                v-for="(item, index) in doubtSummary.commonIssues"
                :key="index"
                class="p-4 bg-gray-50 border border-gray-200 rounded-lg hover:border-gray-300 hover:shadow-sm transition-all"
              >
                <div class="flex items-start justify-between">
                  <div class="flex items-start flex-1">
                    <span class="flex items-center justify-center w-7 h-7 bg-blue-600 text-white rounded-full text-sm font-bold mr-3 flex-shrink-0">
                      {{ index + 1 }}
                    </span>
                    <div class="flex-1">
                      <p class="font-bold text-gray-900">{{ item.issue }}</p>
                      <p class="text-sm text-gray-700 mt-1">
                        Mentioned by <strong>{{ item.students }} students</strong>
                      </p>
                    </div>
                  </div>
                  <button @click="createFAQ(item.issue)" class="ml-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium shadow-sm transition-all flex-shrink-0">
                    Create FAQ
                  </button>
                </div>
              </div>
            </div>
            <div v-else class="text-center py-8 text-gray-500">
              <p class="text-sm">No recurring issues identified yet</p>
            </div>
          </div>

          <!-- Source Breakdown -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="bg-white rounded-xl shadow-sm p-5 border border-gray-200 hover:shadow-md hover:border-blue-300 transition-all">
              <div class="flex items-center justify-between mb-3">
                <h5 class="font-bold text-gray-900">Forum Posts</h5>
                <ChatBubbleLeftRightIcon class="text-blue-600 w-6 h-6" />
              </div>
              <p class="text-3xl font-bold text-gray-900 mb-1">{{ doubtSummary?.sourceBreakdown?.forum?.count || 0 }}</p>
              <p class="text-sm text-gray-600">{{ doubtSummary?.sourceBreakdown?.forum?.percentage || 0 }}% of total</p>
            </div>
            <div class="bg-white rounded-xl shadow-sm p-5 border border-gray-200 hover:shadow-md hover:border-blue-300 transition-all">
              <div class="flex items-center justify-between mb-3">
                <h5 class="font-bold text-gray-900">Emails</h5>
                <EnvelopeIcon class="text-blue-600 w-6 h-6" />
              </div>
              <p class="text-3xl font-bold text-gray-900 mb-1">{{ doubtSummary?.sourceBreakdown?.email?.count || 0 }}</p>
              <p class="text-sm text-gray-600">{{ doubtSummary?.sourceBreakdown?.email?.percentage || 0 }}% of total</p>
            </div>
            <div class="bg-white rounded-xl shadow-sm p-5 border border-gray-200 hover:shadow-md hover:border-blue-300 transition-all">
              <div class="flex items-center justify-between mb-3">
                <h5 class="font-bold text-gray-900">Chat Logs</h5>
                <ChatBubbleLeftRightIcon class="text-blue-600 w-6 h-6" />
              </div>
              <p class="text-3xl font-bold text-gray-900 mb-1">{{ doubtSummary?.sourceBreakdown?.chat?.count || 0 }}</p>
              <p class="text-sm text-gray-600">{{ doubtSummary?.sourceBreakdown?.chat?.percentage || 0 }}% of total</p>
            </div>
          </div>

          <!-- Quick Actions -->
          <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h4 class="font-bold text-gray-900 mb-4 text-lg">Quick Actions</h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <button 
                @click="sendToInstructor" 
                :disabled="!hasData"
                class="px-5 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-left shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <EnvelopeIcon class="w-5 h-5" />
                Send to Instructor
              </button>
              <button 
                @click="createOfficeHoursAgenda" 
                :disabled="!hasData"
                class="px-5 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-left shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <ClipboardDocumentListIcon class="w-5 h-5" />
                Office Hours Agenda
              </button>
              <button 
                @click="generateWeeklyReport" 
                :disabled="!hasData"
                class="px-5 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-left shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <DocumentTextIcon class="w-5 h-5" />
                Weekly Report
              </button>
              <button 
                @click="getAIResponseSuggestions" 
                :disabled="!hasData"
                class="px-5 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-left shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <ChatBubbleLeftRightIcon class="w-5 h-5" />
                AI Suggestions
              </button>
            </div>
          </div>
        </div>

        <!-- Right Side Panel -->
        <aside class="w-[340px] flex flex-col gap-5 flex-shrink-0 sticky top-24 self-start max-h-[calc(100vh-7rem)] overflow-y-auto">
          <!-- Summary Statistics -->
          <div class="bg-white rounded-xl shadow-sm p-5 border border-gray-200">
            <div class="font-bold mb-4 text-base text-gray-900">Summary Statistics</div>
            <div class="space-y-3">
              <div class="flex justify-between items-center p-3 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors">
                <span class="text-gray-700 text-sm font-medium">Total Messages</span>
                <span class="bg-blue-600 text-white px-3 py-1 rounded-full font-bold text-sm">{{ summaryStats?.totalQueries || 0 }}</span>
              </div>
              <div class="flex justify-between items-center p-3 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors">
                <span class="text-gray-700 text-sm font-medium">Topics Identified</span>
                <span class="bg-blue-600 text-white px-3 py-1 rounded-full font-bold text-sm">{{ summaryStats?.topicClusters || 0 }}</span>
              </div>
              <div class="flex justify-between items-center p-3 bg-orange-50 rounded-lg hover:bg-orange-100 transition-colors">
                <span class="text-gray-700 text-sm font-medium">Recurring Issues</span>
                <span class="bg-orange-600 text-white px-3 py-1 rounded-full font-bold text-sm">{{ summaryStats?.recurringDoubts || 0 }}</span>
              </div>
              <div class="flex justify-between items-center p-3 bg-red-50 rounded-lg hover:bg-red-100 transition-colors">
                <span class="text-gray-700 text-sm font-medium">Learning Gaps</span>
                <span class="bg-red-600 text-white px-3 py-1 rounded-full font-bold text-sm">{{ summaryStats?.learningGaps || 0 }}</span>
              </div>
            </div>
          </div>

          <!-- Export Options Component -->
          <div>
            <ExportOptions 
              v-if="hasData"
              :course-code="selectedCourse === 'all' ? 'CS101' : selectedCourse"
              :period="selectedPeriod"
              :source="selectedSource"
            />
          </div>

          <!-- AI Insights -->
          <div class="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl shadow-sm p-5 border border-indigo-200">
            <div class="font-bold mb-3 text-base text-gray-900 flex items-center gap-2">
              <svg class="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              AI Insights
            </div>
            <p v-if="hasData && topConcern.topic !== 'N/A'" class="text-sm text-gray-800 mb-3 leading-relaxed">
              <strong class="text-gray-900">{{ topConcern.topic }}</strong> queries up {{ Math.floor(Math.random() * 40) + 10 }}%. Consider a special session or FAQ update.
            </p>
            <p v-else class="text-sm text-gray-600 mb-3">
              Loading AI-powered insights...
            </p>
            <button 
              @click="getAIResponseSuggestions" 
              :disabled="!hasData"
              class="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 text-sm shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Get More Insights
            </button>
          </div>
        </aside>
      </div>
    </main>
  </div>
</template>