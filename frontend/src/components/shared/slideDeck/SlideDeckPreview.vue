<template>
  <div class="flex min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
    <!-- Loading State -->
    <div v-if="!config" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <svg class="animate-spin h-12 w-12 text-blue-500 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p class="text-slate-300 mt-4 text-lg">Loading slide deck...</p>
      </div>
    </div>

    <!-- Main Content (only render when config is loaded) -->
    <template v-else>
      <main class="flex-1 p-6">
        <!-- Header -->
        <div class="mb-4 flex items-center justify-between bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 py-3 px-4 rounded-lg shadow-xl border border-slate-700">
          <div class="flex items-center gap-4">
            <button
              @click="handleBackToConfig"
              class="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-black rounded-lg font-bold transition-all flex items-center gap-2"
            >
              ← Back to Config
            </button>
            <div>
              <h1 class="font-extrabold text-xl tracking-tight text-white">
                {{ config.title }}
              </h1>
              <p class="text-slate-400 text-xs">
                {{ config.numSlides }} slides • {{ config.topics.join(', ') }}
              </p>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <button
              @click="saveDraft"
              :disabled="saving"
              class="px-3 py-2 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-black rounded-lg font-bold transition-all flex items-center gap-2 text-sm"
            >
              💾 {{ saving ? 'Saving...' : 'Save Draft' }}
            </button>
            <button
              @click="handleExport('pptx')"
              :disabled="loading || slides.length === 0"
              class="px-3 py-2 bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-black rounded-lg font-bold transition-all text-sm"
            >
              📊 PPTX
            </button>
            <button
              @click="handleExport('pdf')"
              :disabled="loading || slides.length === 0"
              class="px-3 py-2 bg-red-500 hover:bg-red-600 disabled:opacity-50 text-black rounded-lg font-bold transition-all text-sm"
            >
              🖨️ PDF
            </button>
          </div>
        </div>

        <!-- Main Content Area -->
        <div class="flex gap-4 h-[calc(100vh-120px)]">
          
          <!-- Left Sidebar -->
          <aside class="w-80 bg-slate-800 rounded-xl shadow-2xl border border-slate-700 p-4 overflow-y-auto space-y-4">
            
            <!-- Slide Navigation Bar (Top of Sidebar) -->
            <div class="bg-slate-700 rounded-lg p-3 space-y-2">
              <div class="flex items-center gap-2">
                <button
                  @click="moveSlide(-1)"
                  :disabled="currentIndex === 0"
                  class="flex-1 px-2 py-1 bg-slate-600 hover:bg-slate-500 disabled:opacity-30 text-black rounded text-sm font-bold transition-all"
                >
                  ← Prev
                </button>
                <div class="flex-1 text-center text-white text-xs font-semibold">Slide {{ currentIndex + 1 }}/{{ slides.length }}</div>
                <button
                  @click="moveSlide(1)"
                  :disabled="currentIndex === slides.length - 1"
                  class="flex-1 px-2 py-1 bg-slate-600 hover:bg-slate-500 disabled:opacity-30 text-black rounded text-sm font-bold transition-all"
                >
                  Next →
                </button>
              </div>
              <div class="flex gap-1">
                <button
                  @click="addSlide"
                  class="flex-1 px-2 py-1 bg-green-500 hover:bg-green-600 text-black rounded text-xs font-bold transition-all"
                >
                  ➕ Add
                </button>
                <button
                  @click="removeSlide(currentIndex)"
                  :disabled="slides.length <= 1"
                  class="flex-1 px-2 py-1 bg-red-500 hover:bg-red-600 disabled:opacity-30 text-black rounded text-xs font-bold transition-all"
                >
                  ✕ Delete
                </button>
              </div>
            </div>

            <!-- Slide Outline -->
            <div class="bg-slate-700 rounded-lg p-3">
              <h3 class="text-sm font-bold text-black mb-2">Slides Outline</h3>
              <div class="space-y-1 max-h-48 overflow-y-auto">
                <div
                  v-for="(slide, idx) in slides"
                  :key="idx"
                  @click="currentIndex = idx"
                  :class="[
                    'p-2 rounded cursor-pointer transition-all text-xs',
                    currentIndex === idx
                      ? 'bg-blue-600 text-white font-semibold'
                      : 'bg-slate-600 text-black hover:bg-slate-500'
                  ]"
                >
                  <div class="font-semibold">Slide {{ idx + 1 }}</div>
                  <div class="truncate text-black">{{ slide.title }}</div>
                </div>
              </div>
            </div>

            <!-- Slide Properties -->
            <div class="bg-slate-700 rounded-lg p-3 space-y-3">
              <h3 class="text-sm font-bold text-black">Properties</h3>
              
              <!-- Formatting Toolbar -->
              <div>
                <label class="text-xs font-bold text-black mb-1 block">Text Formatting</label>
                <div class="flex items-center gap-1">
                  <button
                    @click="applyFormat('bold')"
                    class="px-2 py-1 bg-slate-600 hover:bg-slate-500 text-black rounded text-xs font-bold transition-all"
                  >
                    B
                  </button>
                  <button
                    @click="applyFormat('italic')"
                    class="px-2 py-1 bg-slate-600 hover:bg-slate-500 text-black rounded text-xs italic transition-all"
                  >
                    I
                  </button>
                  <button
                    @click="applyFormat('underline')"
                    class="px-2 py-1 bg-slate-600 hover:bg-slate-500 text-black rounded text-xs underline transition-all"
                  >
                    U
                  </button>
                </div>
              </div>

              <!-- Layout Selection -->
              <div>
                <label class="text-xs font-bold text-black mb-1 block">Layout</label>
                <select
                  v-model="currentSlide.layout"
                  @change="updateSlide"
                  class="w-full px-2 py-1 bg-slate-600 text-black rounded border border-slate-500 focus:outline-none text-xs"
                >
                  <option value="title">Title Slide</option>
                  <option value="content">Content</option>
                  <option value="two-column">Two Column</option>
                  <option value="image">Image Focus</option>
                </select>
              </div>

              <!-- Background Color -->
              <div>
                <label class="text-xs font-bold text-black mb-1 block">Background</label>
                <div class="grid grid-cols-4 gap-1">
                  <button
                    v-for="color in ['white', 'slate-50', 'blue-50', 'gradient']"
                    :key="color"
                    :style="getBgColorStyle(color)"
                    class="h-6 rounded border-2 transition-all relative"
                    >
                    <span class="absolute inset-0 flex items-center justify-center text-[10px] text-black">
                        {{ color }}
                    </span>
                    </button>
                </div>
              </div>

              <!-- Content Stats -->
              <div>
                <p class="text-xs font-bold text-black mb-1">Content Stats</p>
                <div class="space-y-1 text-xs">
                  <div class="flex justify-between text-black">
                    <span>Words:</span>
                    <span class="font-semibold">{{ contentStats.words }}</span>
                  </div>
                  <div class="flex justify-between text-black">
                    <span>Characters:</span>
                    <span class="font-semibold">{{ contentStats.characters }}</span>
                  </div>
                  <div
                    v-if="contentWarning"
                    class="mt-2 p-2 bg-yellow-900 border border-yellow-700 rounded text-yellow-200 text-xs"
                  >
                    ⚠️ {{ contentWarning }}
                  </div>
                </div>
              </div>
            </div>
          </aside>

          <!-- Canvas Area -->
          <div class="flex-1 flex items-center justify-center bg-slate-900/50 rounded-xl p-2 overflow-auto">
            <!-- Loading State -->
            <div v-if="loading" class="text-center">
              <svg class="animate-spin h-12 w-12 text-blue-500 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <p class="text-slate-400 mt-4">Generating preview...</p>
            </div>

            <!-- Slide Display -->
            <div
              v-else-if="currentSlide"
              class="w-full h-full aspect-[16/9] bg-white rounded-lg shadow-2xl border-2 border-blue-500 flex flex-col overflow-hidden"
            >
              <!-- Slide Content Area -->
              <div class="flex-1 p-12 flex flex-col overflow-hidden">
                <!-- Title (rendered as HTML with markdown support) -->
                <div class="text-3xl font-bold text-slate-900 mb-3 pb-2 border-b-2 border-slate-200 break-words leading-tight flex-shrink-0" v-html="renderMarkdown(currentSlide.title)"></div>

                <!-- Content and Graph Container - Split Layout when graph present -->
                <div v-if="currentSlide.graph_image" class="flex-1 flex gap-4 min-h-0 mt-3">
                  <!-- Content Column (40% width) -->
                  <div class="w-2/5 flex flex-col overflow-hidden">
                    <p class="text-xs font-semibold text-black mb-2 uppercase tracking-wide">Content</p>
                    <div class="flex-1 text-sm text-slate-700 overflow-y-auto pr-2 prose prose-sm max-w-none" v-html="renderMarkdown(currentSlide.content)"></div>
                  </div>
                  
                  <!-- Graph Column (60% width) -->
                  <div class="w-3/5 flex flex-col overflow-hidden">
                    <p class="text-xs font-semibold text-black mb-2 uppercase tracking-wide">Graph</p>
                    <div class="flex-1 flex flex-col gap-1 min-h-0">
                      <!-- Graph with Axis Info on Right -->
                      <div class="flex-1 flex gap-2 min-h-0">
                        <!-- Graph Image -->
                        <div class="flex-1 flex items-center justify-center overflow-hidden bg-slate-50 rounded border border-slate-200">
                          <img
                            :src="currentSlide.graph_image"
                            class="w-full h-full object-contain p-2"
                            alt="Chart"
                          />
                        </div>
                        
                        <!-- Compact Axis Info Panel (Right side) -->
                        <div v-if="currentSlide.graph_data" class="w-24 flex flex-col gap-1 text-xs">
                          <!-- X-Axis -->
                          <div v-if="currentSlide.graph_data.x_axis" class="bg-blue-50 border border-blue-200 rounded p-1.5">
                            <p class="font-semibold text-blue-900 text-xs mb-0.5">X-Axis</p>
                            <div class="text-slate-700 space-y-0.5 text-xs">
                              <div class="break-words">
                                <span class="font-semibold">{{ currentSlide.graph_data.x_axis.label }}</span>
                              </div>
                              <div v-if="currentSlide.graph_data.x_axis.unit" class="text-slate-600 text-xs">
                                {{ currentSlide.graph_data.x_axis.unit }}
                              </div>
                            </div>
                          </div>
                          
                          <!-- Y-Axis -->
                          <div v-if="currentSlide.graph_data.y_axis" class="bg-green-50 border border-green-200 rounded p-1.5">
                            <p class="font-semibold text-green-900 text-xs mb-0.5">Y-Axis</p>
                            <div class="text-slate-700 space-y-0.5 text-xs">
                              <div class="break-words">
                                <span class="font-semibold">{{ currentSlide.graph_data.y_axis.label }}</span>
                              </div>
                              <div v-if="currentSlide.graph_data.y_axis.unit" class="text-slate-600 text-xs">
                                {{ currentSlide.graph_data.y_axis.unit }}
                              </div>
                              <div v-if="currentSlide.graph_data.y_axis.min_value !== null && currentSlide.graph_data.y_axis.max_value !== null" class="text-slate-600 text-xs">
                                [{{ formatNumber(currentSlide.graph_data.y_axis.min_value) }}, {{ formatNumber(currentSlide.graph_data.y_axis.max_value) }}]
                              </div>
                            </div>
                          </div>
                          
                          <!-- Validation Status (Compact) -->
                          <div v-if="currentSlide.graph_data.validation" class="bg-slate-100 border border-slate-300 rounded p-1.5">
                            <div v-if="currentSlide.graph_data.validation.is_valid" class="text-xs text-green-700 font-semibold">
                              ✅ Valid
                            </div>
                            <div v-else class="text-xs text-yellow-700 font-semibold">
                              ⚠️ Check
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Content Only (when no graph) -->
                <div v-else class="flex-1 text-lg text-slate-700 p-2 rounded overflow-y-auto prose prose-sm max-w-none mt-3" v-html="renderMarkdown(currentSlide.content)"></div>
              </div>

              <!-- Slide Number -->
              <div class="bg-slate-100 px-6 py-2 text-center border-t border-slate-200 text-sm text-black font-semibold">
                Slide {{ currentIndex + 1 }} of {{ slides.length }}
              </div>
            </div>

            <!-- No Slides Available -->
            <div v-else class="text-center text-slate-400">
              <p class="text-lg">No slides available</p>
              <button
                @click="addSlide"
                class="mt-4 px-6 py-3 bg-blue-500 hover:bg-blue-600 text-black rounded-lg font-bold"
              >
                Create First Slide
              </button>
            </div>
          </div>
        </div>

        <!-- Chart Dialog -->
        <div
          v-if="showChartDialog"
          class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
        >
          <div class="bg-white rounded-xl shadow-2xl p-6 max-w-md w-full mx-4">
            <h2 class="text-xl font-bold text-slate-900 mb-4">Insert Chart</h2>
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-semibold text-slate-700 mb-2">Chart Type</label>
                <select
                  v-model="chartDialog.type"
                  class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="bar">Bar Chart</option>
                  <option value="line">Line Chart</option>
                  <option value="pie">Pie Chart</option>
                  <option value="scatter">Scatter Plot</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-semibold text-slate-700 mb-2">Chart Title</label>
                <input
                  v-model="chartDialog.title"
                  type="text"
                  class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="e.g., Performance Metrics"
                />
              </div>
              <div class="flex gap-2 pt-4">
                <button
                  @click="showChartDialog = false"
                  class="flex-1 px-4 py-2 bg-slate-400 text-black rounded-lg font-bold hover:bg-slate-500 transition-all"
                >
                  Cancel
                </button>
                <button
                  @click="generateGraph"
                  class="flex-1 px-4 py-2 bg-blue-500 text-black rounded-lg font-bold hover:bg-blue-600 transition-all"
                >
                  Insert
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Theme Selector Dialog -->
        <div
          v-if="showThemeSelector"
          class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
        >
          <div class="bg-white rounded-xl shadow-2xl p-6 max-w-2xl w-full mx-4">
            <h2 class="text-2xl font-bold text-slate-900 mb-2">Choose Export Theme</h2>
            <p class="text-sm text-slate-600 mb-6">Select a theme for your exported presentation</p>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <!-- Professional Theme -->
              <div
                @click="selectedTheme = 'professional'"
                :class="[
                  'cursor-pointer p-4 border-2 rounded-lg transition-all',
                  selectedTheme === 'professional' ? 'border-blue-500 bg-blue-50' : 'border-slate-300 hover:border-slate-400'
                ]"
              >
                <div class="flex items-center justify-between mb-2">
                  <h3 class="font-bold text-lg text-slate-900">Professional</h3>
                  <div class="w-5 h-5 rounded-full border-2" :class="selectedTheme === 'professional' ? 'bg-blue-500 border-blue-500' : 'border-slate-300'"></div>
                </div>
                <div class="flex gap-2 mb-2">
                  <div class="w-8 h-8 rounded bg-white border border-slate-300"></div>
                  <div class="w-8 h-8 rounded" style="background: #1F4E78"></div>
                  <div class="w-8 h-8 rounded" style="background: #4472C4"></div>
                </div>
                <p class="text-sm text-slate-600">Navy blue and white with Calibri font. Clean and corporate.</p>
              </div>

              <!-- Modern Theme -->
              <div
                @click="selectedTheme = 'modern'"
                :class="[
                  'cursor-pointer p-4 border-2 rounded-lg transition-all',
                  selectedTheme === 'modern' ? 'border-blue-500 bg-blue-50' : 'border-slate-300 hover:border-slate-400'
                ]"
              >
                <div class="flex items-center justify-between mb-2">
                  <h3 class="font-bold text-lg text-slate-900">Modern</h3>
                  <div class="w-5 h-5 rounded-full border-2" :class="selectedTheme === 'modern' ? 'bg-blue-500 border-blue-500' : 'border-slate-300'"></div>
                </div>
                <div class="flex gap-2 mb-2">
                  <div class="w-8 h-8 rounded" style="background: #F8F9FA"></div>
                  <div class="w-8 h-8 rounded" style="background: #0D6EFD"></div>
                  <div class="w-8 h-8 rounded" style="background: #6F42C1"></div>
                </div>
                <p class="text-sm text-slate-600">Bright blue with light gray. Contemporary and fresh.</p>
              </div>

              <!-- Colorful Theme -->
              <div
                @click="selectedTheme = 'colorful'"
                :class="[
                  'cursor-pointer p-4 border-2 rounded-lg transition-all',
                  selectedTheme === 'colorful' ? 'border-blue-500 bg-blue-50' : 'border-slate-300 hover:border-slate-400'
                ]"
              >
                <div class="flex items-center justify-between mb-2">
                  <h3 class="font-bold text-lg text-slate-900">Colorful</h3>
                  <div class="w-5 h-5 rounded-full border-2" :class="selectedTheme === 'colorful' ? 'bg-blue-500 border-blue-500' : 'border-slate-300'"></div>
                </div>
                <div class="flex gap-2 mb-2">
                  <div class="w-8 h-8 rounded" style="background: #FFF8F0"></div>
                  <div class="w-8 h-8 rounded" style="background: #DC3545"></div>
                  <div class="w-8 h-8 rounded" style="background: #FD7E14"></div>
                </div>
                <p class="text-sm text-slate-600">Red and orange on peach. Vibrant and energetic.</p>
              </div>

              <!-- Dark Theme -->
              <div
                @click="selectedTheme = 'dark'"
                :class="[
                  'cursor-pointer p-4 border-2 rounded-lg transition-all',
                  selectedTheme === 'dark' ? 'border-blue-500 bg-blue-50' : 'border-slate-300 hover:border-slate-400'
                ]"
              >
                <div class="flex items-center justify-between mb-2">
                  <h3 class="font-bold text-lg text-slate-900">Dark</h3>
                  <div class="w-5 h-5 rounded-full border-2" :class="selectedTheme === 'dark' ? 'bg-blue-500 border-blue-500' : 'border-slate-300'"></div>
                </div>
                <div class="flex gap-2 mb-2">
                  <div class="w-8 h-8 rounded" style="background: #212529"></div>
                  <div class="w-8 h-8 rounded" style="background: #FFC107"></div>
                  <div class="w-8 h-8 rounded" style="background: #20C997"></div>
                </div>
                <p class="text-sm text-slate-600">Yellow and teal on dark gray. Bold and striking.</p>
              </div>

              <!-- Minimalist Theme -->
              <div
                @click="selectedTheme = 'minimalist'"
                :class="[
                  'cursor-pointer p-4 border-2 rounded-lg transition-all',
                  selectedTheme === 'minimalist' ? 'border-blue-500 bg-blue-50' : 'border-slate-300 hover:border-slate-400'
                ]"
              >
                <div class="flex items-center justify-between mb-2">
                  <h3 class="font-bold text-lg text-slate-900">Minimalist</h3>
                  <div class="w-5 h-5 rounded-full border-2" :class="selectedTheme === 'minimalist' ? 'bg-blue-500 border-blue-500' : 'border-slate-300'"></div>
                </div>
                <div class="flex gap-2 mb-2">
                  <div class="w-8 h-8 rounded" style="background: #FAFAFA"></div>
                  <div class="w-8 h-8 rounded" style="background: #000000"></div>
                  <div class="w-8 h-8 rounded" style="background: #909090"></div>
                </div>
                <p class="text-sm text-slate-600">Black and white. Simple and elegant.</p>
              </div>
            </div>

            <div class="flex gap-3">
              <button
                @click="showThemeSelector = false"
                class="flex-1 px-4 py-3 bg-slate-400 text-black rounded-lg font-bold hover:bg-slate-500 transition-all"
              >
                Cancel
              </button>
              <button
                @click="confirmExport('pptx')"
                class="flex-1 px-4 py-3 bg-orange-500 text-black rounded-lg font-bold hover:bg-orange-600 transition-all flex items-center justify-center gap-2"
              >
                📊 Export PPTX
              </button>
              <button
                @click="confirmExport('pdf')"
                class="flex-1 px-4 py-3 bg-red-500 text-black rounded-lg font-bold hover:bg-red-600 transition-all flex items-center justify-center gap-2"
              >
                🖨️ Export PDF
              </button>
            </div>
          </div>
        </div>
      </main>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useSlideDeckStore } from '@/stores/slideDeck'
import TASidebar from '@/components/layout/TaLayout/TASidebar.vue'
import InstructorSidebar from '@/components/layout/InstructorLayout/InstructorSideBar.vue'
import { generateSlideDeck, saveSlideDeck, getSlideDeck, exportToPPTX, exportToPDF } from '@/api/slideDeck'

const router = useRouter()
const userStore = useUserStore()
const slideDeckStore = useSlideDeckStore()

const props = defineProps({
  role: {
    type: String,
    default: 'instructor'
  },
  deckId: {
    type: String,
    default: null
  }
})

const role = computed(() => props.role)
const taSidebar = TASidebar
const instructorSidebar = InstructorSidebar

// State
const config = ref(null)
const slides = ref([])
const currentIndex = ref(0)
const loading = ref(true)
const saving = ref(false)
const editorFont = ref('sans')
const editorAlign = ref('left')
const showChartDialog = ref(false)
const chartDialog = ref({ type: 'bar', title: '' })
const savedDeckId = ref(null)
const selectedTheme = ref('professional')
const showThemeSelector = ref(false)

// Get config or load existing deck from Pinia store
onMounted(async () => {
  try {
    // If deckId is provided, load existing deck
    if (props.deckId) {
      try {
        const deckResponse = await getSlideDeck(props.deckId)
        // Load existing deck data
        slides.value = deckResponse.slides || []
        config.value = {
          title: deckResponse.title,
          description: deckResponse.description,
          courseId: deckResponse.course_id,
          numSlides: deckResponse.slides?.length || 0,
          topics: [], // Not available from existing deck
          format: 'presentation',
          includeGraphs: false,
          graphTypes: []
        }
        loading.value = false
      } catch (err) {
        console.error('Failed to load existing deck:', err)
        router.push({
          name: role.value === 'ta' ? 'TaSlideDeckViewer' : 'InstructorSlideDeckViewer'
        })
      }
      return
    }

    // Otherwise, load config from store (new generation flow)
    config.value = slideDeckStore.getConfig()
    
    if (!config.value) {
      console.error('No config found in store')
      router.push({
        name: role.value === 'ta' ? 'TaSlideDeckConfig' : 'InstructorSlideDeckConfig'
      })
      return
    }

    if (config.value) {
      generatePreview()
    }
  } catch (err) {
    console.error('Failed to load config:', err)
    router.push({
      name: role.value === 'ta' ? 'TaSlideDeckConfig' : 'InstructorSlideDeckConfig'
    })
  }
})

// Generate preview slides
const generatePreview = async () => {
  loading.value = true
  try {
    const response = await generateSlideDeck({
      course_id: config.value.courseId,
      title: config.value.title,
      description: config.value.description,
      topics: config.value.topics,
      num_slides: config.value.numSlides,
      format: config.value.format,
      include_graphs: config.value.includeGraphs,
      graph_types: config.value.graphTypes
    })

    slides.value = response.slides.map(slide => ({
      ...slide,
      layout: 'content',
      background: 'white',
      notes: ''
    }))
  } catch (err) {
    console.error('Failed to generate slides:', err)
    alert('Failed to generate preview. Please try again.')
  } finally {
    loading.value = false
  }
}

// Current slide
const currentSlide = computed(() => slides.value[currentIndex.value])

// Content stats
const contentStats = computed(() => {
  if (!currentSlide.value) return { characters: 0, words: 0, lines: 0 }
  const text = `${currentSlide.value.title} ${currentSlide.value.content}`
  return {
    characters: text.length,
    words: text.split(/\s+/).filter(w => w.length > 0).length,
    lines: text.split('\n').length
  }
})

// Content warning
const contentWarning = computed(() => {
  if (!currentSlide.value) return null
  const text = `${currentSlide.value.title} ${currentSlide.value.content}`
  if (text.length > 1000) return 'Content exceeds recommended length for 16:9 format'
  if (text.split('\n').length > 10) return 'Too many lines. Consider breaking into multiple slides.'
  return null
})

// Add slide
const addSlide = () => {
  slides.value.push({
    title: `Slide ${slides.value.length + 1}`,
    content: 'Your content here...',
    layout: 'content',
    background: 'white',
    notes: '',
    graph_image: null
  })
  currentIndex.value = slides.value.length - 1
}

// Remove slide
const removeSlide = (index) => {
  if (slides.value.length > 1) {
    slides.value.splice(index, 1)
    if (currentIndex.value >= slides.value.length) {
      currentIndex.value = slides.value.length - 1
    }
  }
}

// Move slide
const moveSlide = (direction) => {
  const newIndex = currentIndex.value + direction
  if (newIndex >= 0 && newIndex < slides.value.length) {
    ;[slides.value[currentIndex.value], slides.value[newIndex]] = [
      slides.value[newIndex],
      slides.value[currentIndex.value]
    ]
    currentIndex.value = newIndex
  }
}

// Update slide
const updateSlide = () => {
  // Reactive update
}

// Apply formatting
const applyFormat = (format) => {
  // Format implementation
  console.log('Apply format:', format)
}

// Insert chart
const insertChart = () => {
  if (currentSlide.value) {
    currentSlide.value.graph_image = `data:image/svg+xml,...` // Placeholder
    updateSlide()
  }
  showChartDialog.value = false
}

// Get background color style
const getBgColorStyle = (color) => {
  const styles = {
    white: 'background-color: white',
    'slate-50': 'background-color: #f8fafc',
    'blue-50': 'background-color: #eff6ff',
    gradient: 'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
  }
  return styles[color] || styles.white
}

// Back to config
const handleBackToConfig = () => {
  // Config is already in store, just navigate back
  router.push({
    name: role.value === 'ta' ? 'TaSlideDeckConfig' : 'InstructorSlideDeckConfig'
  })
}

// Save draft
const saveDraft = async () => {
  saving.value = true
  try {
    const response = await saveSlideDeck({
      title: config.value.title,
      description: config.value.description,
      course_id: config.value.courseId,
      slides: slides.value,
      format: config.value.format
    })
    
    // Store the deck ID for export functionality
    if (response && response.id) {
      savedDeckId.value = response.id
    }
    
    alert('Draft saved successfully!')
    // Redirect to My Slide Decks page
    router.push({ name: 'MySlideDeck' })
  } catch (err) {
    console.error('Failed to save draft:', err)
    alert('Failed to save draft.')
  } finally {
    saving.value = false
  }
}

// Format number for display (2 decimal places)
const formatNumber = (value) => {
  if (value === null || value === undefined) return 'N/A'
  if (typeof value !== 'number') return value
  // Show integers without decimals, decimals with up to 2 places
  return Number.isInteger(value) ? value.toString() : value.toFixed(2)
}

// Render markdown to HTML
const renderMarkdown = (text) => {
  if (!text) return ''
  
  let html = text
  
  // Escape HTML special characters first
  html = html
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
  
  // Headers
  html = html.replace(/^### (.*?)$/gm, '<h3 class="text-xl font-bold mt-3 mb-2">$1</h3>')
  html = html.replace(/^## (.*?)$/gm, '<h2 class="text-2xl font-bold mt-4 mb-2">$1</h2>')
  html = html.replace(/^# (.*?)$/gm, '<h1 class="text-3xl font-bold mt-4 mb-2">$1</h1>')
  
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold">$1</strong>')
  html = html.replace(/__([^_]+)__/g, '<strong class="font-bold">$1</strong>')
  
  // Italic
  html = html.replace(/\*(.*?)\*/g, '<em class="italic">$1</em>')
  html = html.replace(/_([^_]+)_/g, '<em class="italic">$1</em>')
  
  // Code blocks
  html = html.replace(/```(.*?)```/gs, '<pre class="bg-slate-100 p-3 rounded my-2 overflow-x-auto"><code class="text-sm font-mono">$1</code></pre>')
  
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code class="bg-slate-100 px-1 py-0.5 rounded text-red-600 font-mono text-sm">$1</code>')
  
  // Bullet lists
  html = html.replace(/^\* (.*?)$/gm, '<li class="ml-4">$1</li>')
  html = html.replace(/^\- (.*?)$/gm, '<li class="ml-4">$1</li>')
  html = html.replace(/(<li.*?<\/li>)/s, '<ul class="list-disc my-2">$1</ul>')
  html = html.replace(/<\/ul>\n<ul/g, '')
  
  // Numbered lists
  html = html.replace(/^\d+\. (.*?)$/gm, '<li class="ml-4">$1</li>')
  
  // Line breaks to paragraphs
  html = html.split('\n\n').map(para => {
    if (para.includes('<')) return para
    return `<p class="my-2">${para}</p>`
  }).join('')
  
  // Line breaks within paragraphs
  html = html.replace(/\n(?!<)/g, '<br />')
  
  return html
}

// Export
const handleExport = async (format) => {
  // Check if deck is saved
  const deckId = savedDeckId.value || props.deckId
  
  if (!deckId) {
    alert('Please save the deck first before exporting.')
    return
  }
  
  // Show theme selector
  showThemeSelector.value = true
  
  // Wait for theme selection (handled by separate function)
  // This will be called from the theme selector dialog
}

const confirmExport = async (format) => {
  const deckId = savedDeckId.value || props.deckId
  
  if (!deckId) return
  
  try {
    showThemeSelector.value = false
    
    if (format === 'pptx') {
      await exportToPPTX(deckId, selectedTheme.value)
    } else if (format === 'pdf') {
      await exportToPDF(deckId, selectedTheme.value)
    }
  } catch (error) {
    console.error(`Export failed:`, error)
    alert(`Failed to export as ${format.toUpperCase()}. ${error.message || 'Please try again.'}`)
  }
}
</script>

<style scoped>
/* Custom scrollbar */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #475569;
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: #64748b;
}

/* 16:9 Aspect Ratio */
.aspect-\[16\/9\] {
  aspect-ratio: 16 / 9;
}

/* Text alignment classes */
.text-left {
  text-align: left;
}
.text-center {
  text-align: center;
}
.text-right {
  text-align: right;
}
</style>