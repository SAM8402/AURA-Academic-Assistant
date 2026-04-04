<template>
  <div class="flex min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
    <!-- Role-based sidebar -->
    <component :is="role === 'ta' ? taSidebar : instructorSidebar" class="fixed top-0 left-0 h-screen" />

    <main class="flex-1 ml-64 p-8">
      <div class="max-w-4xl mx-auto">
        <!-- Header -->
        <div class="mb-8">
          <h1 class="font-extrabold text-4xl tracking-tight text-slate-900 mb-2">
            Create Slide Deck
          </h1>
          <p class="text-slate-600 text-lg">
            Configure your presentation settings and topics
          </p>
        </div>

        <!-- Configuration Card -->
        <div class="bg-white rounded-2xl shadow-lg border border-slate-200 p-8">
          <form @submit.prevent="handleGeneratePreview" class="space-y-6">
            <!-- Course Selection -->
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-2">
                Course <span class="text-red-500">*</span>
              </label>
              <input
                v-model.number="config.courseId"
                type="number"
                required
                class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                placeholder="Enter course ID"
              />
            </div>

            <!-- Title -->
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-2">
                Presentation Title <span class="text-red-500">*</span>
              </label>
              <input
                v-model="config.title"
                type="text"
                required
                class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                placeholder="e.g., Introduction to Machine Learning"
              />
            </div>

            <!-- Description -->
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-2">
                Description (Optional)
              </label>
              <textarea
                v-model="config.description"
                rows="3"
                class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all resize-none"
                placeholder="Provide additional context or specific requirements..."
              ></textarea>
            </div>

            <!-- Format and Slides -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-semibold text-slate-700 mb-2">
                  Format
                </label>
                <select
                  v-model="config.format"
                  class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                >
                  <option value="presentation">Presentation (16:9)</option>
                  <option value="document">Document (A4)</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-semibold text-slate-700 mb-2">
                  Number of Slides <span class="text-red-500">*</span>
                </label>
                <input
                  v-model.number="config.numSlides"
                  type="number"
                  min="3"
                  max="30"
                  required
                  class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                />
              </div>
            </div>

            <!-- Graph Options -->
            <div class="bg-slate-50 rounded-lg p-6 border border-slate-200">
              <div class="flex items-center gap-3 mb-4">
                <input
                  type="checkbox"
                  id="includeGraphs"
                  v-model="config.includeGraphs"
                  class="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <label for="includeGraphs" class="text-sm font-semibold text-slate-700 cursor-pointer">
                  Include Charts & Graphs
                </label>
              </div>

              <transition name="slide-fade">
                <div v-if="config.includeGraphs" class="space-y-3">
                  <p class="text-xs text-slate-600 mb-3">Select chart types to include:</p>
                  <div class="grid grid-cols-2 gap-3">
                    <label
                      v-for="graphType in graphOptions"
                      :key="graphType"
                      class="flex items-center gap-2 p-3 bg-white border-2 border-slate-200 rounded-lg hover:border-blue-400 cursor-pointer transition-all"
                      :class="{ 'border-blue-500 bg-blue-50': config.graphTypes.includes(graphType) }"
                    >
                      <input
                        type="checkbox"
                        v-model="config.graphTypes"
                        :value="graphType"
                        class="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <span class="text-sm font-medium text-slate-700 capitalize">{{ graphType }}</span>
                    </label>
                  </div>
                </div>
              </transition>
            </div>

            <!-- Topics -->
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-2">
                Topics <span class="text-red-500">*</span>
              </label>
              
              <!-- Topic Tags -->
              <div v-if="config.topics.length" class="flex flex-wrap gap-2 mb-3">
                <span
                  v-for="(topic, index) in config.topics"
                  :key="index"
                  class="inline-flex items-center gap-2 px-3 py-2 bg-blue-100 text-blue-800 rounded-lg text-sm font-medium"
                >
                  {{ topic }}
                  <button
                    type="button"
                    @click="removeTopic(index)"
                    class="text-blue-600 hover:text-blue-800 font-bold"
                  >
                    ×
                  </button>
                </span>
              </div>

              <!-- Add Topic Input -->
              <div class="flex gap-2">
                <input
                  v-model="newTopic"
                  type="text"
                  @keyup.enter.prevent="addTopic"
                  class="flex-1 px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  placeholder="Type a topic and press Enter or click Add"
                />
                <button
                  type="button"
                  @click="addTopic"
                  class="px-6 py-3 bg-slate-200 text-slate-700 rounded-lg font-semibold hover:bg-slate-300 transition-all"
                >
                  Add
                </button>
                <button
                  v-if="config.topics.length"
                  type="button"
                  @click="config.topics = []"
                  class="px-6 py-3 bg-red-100 text-red-700 rounded-lg font-semibold hover:bg-red-200 transition-all"
                >
                  Clear All
                </button>
              </div>
              <p class="text-xs text-slate-500 mt-2">
                At least one topic is required. Add multiple topics to cover different aspects.
              </p>
            </div>

            <!-- Action Buttons -->
            <div class="flex items-center justify-between pt-6 border-t border-slate-200">
              <button
                type="button"
                @click="$router.back()"
                class="px-6 py-3 text-slate-600 hover:text-slate-800 font-semibold transition-all"
              >
                ← Back
              </button>
              <div class="flex flex-col items-end gap-2">
                <button
                  type="submit"
                  :disabled="loading || !isFormValid"
                  :class="{
                    'bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white shadow-lg hover:shadow-xl': isFormValid,
                    'bg-slate-300 text-slate-500 cursor-not-allowed': !isFormValid && !loading
                  }"
                  class="px-8 py-3 rounded-lg font-bold transition-all flex items-center gap-2 border-2 border-transparent hover:border-blue-400"
                >
                  <span v-if="loading">
                    <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </span>
                  <span v-if="loading">Generating...</span>
                  <span v-else>Generate Preview</span>
                  <span v-if="!loading" class="text-lg">→</span>
                </button>
                <span v-if="!isFormValid" class="text-xs text-red-600 font-medium">
                  ⚠️ Fill all required fields: Course, Title, Topics (min 1), and 3-30 slides
                </span>
              </div>
            </div>
          </form>
        </div>

        <!-- Error Display -->
        <div v-if="error" class="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p class="text-red-700 text-sm font-medium">{{ error }}</p>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import TASidebar from '@/components/layout/TaLayout/TASidebar.vue'
import InstructorSidebar from '@/components/layout/InstructorLayout/InstructorSideBar.vue'
import { useUserStore } from '@/stores/user'
import { useSlideDeckStore } from '@/stores/slideDeck'

const router = useRouter()
const userStore = useUserStore()
const slideDeckStore = useSlideDeckStore()

const role = computed(() => userStore.role)
const taSidebar = TASidebar
const instructorSidebar = InstructorSidebar

// Configuration state
const config = ref({
  courseId: null,
  title: '',
  description: '',
  format: 'presentation',
  numSlides: 10,
  topics: [],
  includeGraphs: false,
  graphTypes: []
})

const newTopic = ref('')
const loading = ref(false)
const error = ref(null)

const graphOptions = ['bar', 'line', 'pie', 'scatter']

// Form validation - comprehensive checks
const isFormValid = computed(() => {
  const hasValidCourse = config.value.courseId && config.value.courseId > 0
  const hasValidTitle = config.value.title && config.value.title.trim().length >= 3
  const hasValidSlides = config.value.numSlides >= 3 && config.value.numSlides <= 30
  const hasTopics = config.value.topics && config.value.topics.length > 0
  
  return hasValidCourse && hasValidTitle && hasValidSlides && hasTopics
})

// Add topic
const addTopic = () => {
  const topic = newTopic.value.trim()
  if (topic && !config.value.topics.includes(topic)) {
    config.value.topics.push(topic)
    newTopic.value = ''
  }
}

// Remove topic
const removeTopic = (index) => {
  config.value.topics.splice(index, 1)
}

// Generate preview and navigate
const handleGeneratePreview = async () => {
  if (!isFormValid.value) {
    error.value = 'Please fill in all required fields'
    return
  }

  loading.value = true
  error.value = null

  try {
    // Store config in Pinia for retrieval in Preview component
    slideDeckStore.setConfig(config.value)
    
    // Navigate to preview page (no params needed)
    router.push({
      name: role.value === 'ta' ? 'TaSlideDeckPreview' : 'InstructorSlideDeckPreview'
    })
  } catch (err) {
    error.value = err.message || 'Failed to generate preview'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.slide-fade-enter-active {
  transition: all 0.3s ease;
}
.slide-fade-leave-active {
  transition: all 0.2s ease;
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(-10px);
  opacity: 0;
}
</style>
