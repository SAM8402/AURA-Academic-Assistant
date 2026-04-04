<template>
  <div class="flex h-screen" :style="{ color: 'var(--text-primary)' }">
    <!-- Sidebar -->
    <Sidebar />

    <!-- Main Section -->
    <div class="flex flex-col flex-grow main-theme ml-[250px]" :style="{ color: 'var(--text-primary)' }">
      <HeaderBar v-if="!isOnBreak" />

      <!-- Main Body -->
      <div class="flex flex-grow overflow-hidden main-theme" :style="{ color: 'var(--text-primary)' }">
        <!-- Course Section -->
        <div class="p-6 flex-grow overflow-y-auto section-theme" :style="{ color: 'var(--text-primary)' }">
          <div class="flex flex-wrap justify-between items-center mb-6 gap-3">
              <div class="flex flex-wrap items-center gap-2 section-text" :style="{ color: 'var(--text-primary)' }">
              <i class="bi bi-journal-bookmark text-blue-600 text-lg"></i>
              <span class="font-semibold" :style="{ color: 'var(--text-primary)' }">{{ courses.length }} Active Courses</span>
              <span class="section-subtext" :style="{ color: 'var(--text-primary)' }">| {{ deadlineCount }} Deadlines This Week</span>
            </div>            <!-- Buttons -->
            <div class="flex flex-wrap gap-3 justify-end">
              <!-- Add Resource -->
                <button
              @click="showAddResource = true"
              class="px-3 py-1.5 border rounded-full text-sm font-medium transition add-resource-btn"
              :style="{ color: 'var(--text-primary)' }"
                >
              <i class="bi bi-collection me-1"></i> Add Resources
                </button>

                <!-- Study Break -->
                <button
                @click="showStudyBreak = true"
                class="px-3 py-1.5 border rounded-full text-sm font-medium transition study-break-btn"
                :style="{ color: 'var(--text-primary)' }"
                >
                <i class="bi bi-cup-hot me-1"></i>
                {{ isOnBreak ? `Break: ${formattedTime}` : 'Study Break' }}
                </button>
                </div>
                </div>

          <!-- Course Cards -->
            <div v-if="loadingCourses" class="text-center py-12">
            <div class="spinner-border spinner-border-sm text-primary"></div>
            <p class="text-muted mt-3">Loading your courses...</p>
            </div>
            <div v-else-if="courses.length === 0" class="text-center py-12">
            <p class="text-muted">No courses assigned yet. Check back soon!</p>
            </div>
            <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div
                v-for="course in courses"
                :key="course.id"
                class="rounded-3xl shadow hover:shadow-lg overflow-hidden transition card-theme flex flex-col h-full"
              >
                <img :src="getCourseImage(course.id)" class="w-full h-60 object-cover" />
                <div class="p-3 flex flex-col flex-1 gap-2" style="min-height: 180px;">
                  <div class="flex-1 space-y-1">
                    <h3 class="font-semibold card-title">{{ course.name }}</h3>
                    <p class="text-sm card-subtext line-clamp-2">{{ course.description }}</p>
                  </div>
                  <div class="flex flex-col gap-1 pt-2">
                    <div class="flex justify-between items-center gap-2">
                      <button
                        class="px-3 py-1 border rounded-full text-sm transition card-btn-blue"
                        @click="showComingSoon(course.id, 'Open')"
                      >
                        <i class="bi bi-play-circle me-1"></i> Open
                      </button>
                      <button
                        class="px-3 py-1 border rounded-full text-sm transition card-btn-green"
                        @click="showComingSoon(course.id, 'AI assistance')"
                      >
                        <i class="bi bi-robot me-1"></i> Ask AI
                      </button>
                    </div>
                    <p v-if="actionNotices[course.id]" class="text-xs section-subtext">{{ actionNotices[course.id] }}</p>
                  </div>
                </div>
              </div>
            </div>

          <!-- Resources Section -->
          <div class="mt-8">
            <h3 class="font-semibold text-gray-800 mb-3">My Resources</h3>
            <div v-if="loadingResources" class="text-center py-8">
              <div class="spinner-border spinner-border-sm text-primary"></div>
              <p class="text-muted mt-2">Loading resources...</p>
            </div>
            <div v-else-if="resources.length === 0" class="text-gray-400">No resources added yet.</div>

            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div v-for="res in resources" :key="res.id" class="card-theme p-4 rounded-2xl shadow flex flex-col gap-2">
                <div class="flex justify-between items-start">
                  <span class="text-sm font-semibold card-title">{{ res.title }}</span>
                  <div class="flex gap-2">
                    <button @click="togglePin(res.id)" class="text-sm hover:text-yellow-600 transition" :class="res.isPinned ? 'text-yellow-500' : 'text-gray-500'">
                      <i :class="res.isPinned ? 'bi bi-pin-angle-fill' : 'bi bi-pin-angle'" class="text-lg"></i>
                    </button>
                    <button @click="deleteResource(res.id)" class="text-sm text-red-600 hover:text-red-700 transition">
                      <i class="bi bi-trash text-lg"></i>
                    </button>
                  </div>
                </div>

                <!-- Document -->
                <div v-if="res.resource_type === 'document' && res.file_name" class="text-sm card-subtext">
                  📄
                  <a :href="getResourceUrl(res)" target="_blank" class="underline hover:text-blue-600">{{ res.file_name }}</a>
                </div>

                <!-- Image -->
                <div v-if="res.resource_type === 'image' && res.file_path" class="mb-1">
                  <img :src="getResourceUrl(res)" class="w-full h-32 object-cover rounded-lg" />
                </div>

                <!-- Link -->
                <div v-if="res.resource_type === 'link'" class="text-blue-600 text-sm break-all">
                  🔗 <a :href="res.url" target="_blank" class="underline hover:text-blue-800">{{ res.url }}</a>
                </div>

                <p class="text-xs card-subtext mt-auto">Added {{ new Date(res.created_at).toLocaleDateString() }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Panel -->
        <div class="w-[320px] border-l" :style="{ background: 'var(--color-bg-card)' }">
          <RightPanel 
            :pinnedResources="pinnedResources" 
            @view-pinned="openPinnedResources"
            @open-resource="openResourceFromPanel"
          />
        </div>
      </div>
    </div>

    <!-- Add Resource Modal -->
    <div
      v-if="showAddResource"
      class="fixed inset-0 flex items-center justify-center bg-black/40 z-50"
    >
      <div class="rounded-3xl shadow-lg w-full max-w-md p-6 relative modal-theme">
        <h3 class="text-xl font-semibold modal-title mb-4 flex items-center">
          <i class="bi bi-folder-plus me-2"></i> Add Resource
        </h3>

        <div class="space-y-4">
          <div>
            <label class="font-semibold block mb-1">Upload Document</label>
            <input type="file" accept=".pdf,.doc,.docx" class="w-full border rounded-lg p-2" ref="docInput" />
          </div>
          <div>
            <label class="font-semibold block mb-1">Upload Image</label>
            <input type="file" accept="image/*" class="w-full border rounded-lg p-2" ref="imgInput" />
          </div>
          <div>
            <label class="font-semibold block mb-1">Add Link</label>
            <input type="url" placeholder="https://example.com" class="w-full border rounded-lg p-2" ref="linkInput" />
          </div>
        </div>

        <div class="mt-6 flex justify-end gap-2">
          <button @click="showAddResource = false" class="px-4 py-2 rounded-full border hover:bg-gray-100">
            Cancel
          </button>
          <button @click="saveResource" class="px-4 py-2 rounded-full bg-blue-600 text-white hover:bg-blue-700">
            Save
          </button>
        </div>
      </div>
    </div>

    <!-- Study Break Modal -->
    <div
      v-if="showStudyBreak"
      class="fixed inset-0 flex items-center justify-center bg-black/40 z-50"
    >
      <div class="rounded-3xl shadow-lg w-full max-w-md p-6 modal-theme">
      <h3 class="text-xl font-semibold mb-4 flex items-center" style="color: var(--color-btn-yellow-text)">
        <i class="bi bi-cup-hot me-2"></i> Take a Break
      </h3>

      <p class="font-semibold mb-3 text-center" style="color: var(--color-text-primary)">Select your break duration:</p>
      <div class="grid grid-cols-2 gap-2 mb-3">
        <button v-for="mins in [5,10,15,30]" :key="mins"
        @click="startBreak(mins)"
        class="py-2 border rounded-lg transition"
        style="border-color: var(--color-btn-yellow-border); color: var(--color-btn-yellow-text); background: var(--color-btn-bg);"
        :style="{ borderColor: 'var(--color-btn-yellow-border)', color: 'var(--color-btn-yellow-text)' }">
        {{ mins }} min
        </button>
      </div>

      <div class="flex gap-2 items-center">
        <input
        v-model="customBreak"
        type="number"
        min="1"
        placeholder="Custom (min)"
        class="border rounded-lg p-2 flex-grow"
        style="border-color: var(--color-btn-border); background: var(--color-btn-bg); color: var(--color-text-primary);"
        />
        <button @click="startCustomBreak" class="px-4 py-2 rounded-lg transition"
        style="background: var(--color-btn-active-bg); color: var(--color-btn-active-text); border: 1px solid var(--color-btn-active-border);">
        Start
        </button>
      </div>

      <div class="mt-5 text-right">
        <button @click="showStudyBreak = false" class="transition" style="color: var(--color-text-secondary);">Close</button>
      </div>
      </div>
    </div>

    <!-- Full-Screen Break Overlay -->
    <div
      v-if="isOnBreak"
      class="fixed inset-0 bg-gradient-to-br from-yellow-400 via-orange-400 to-pink-400 flex flex-col items-center justify-center z-50 text-white transition"
    >
      <h1 class="text-5xl font-bold mb-3 animate-pulse">☕ Break Started</h1>
      <h2 class="text-2xl mb-6">Time Left: {{ formattedTime }}</h2>
      <button
        @click="endBreak"
        class="px-6 py-3 bg-red-600 rounded-full text-lg font-semibold hover:bg-red-700 transition"
      >
        End Break
      </button>
    </div>

    <!-- Pinned Resources Modal -->
    <div
      v-if="showPinnedModal"
      class="fixed inset-0 flex items-center justify-center bg-black/40 z-50"
    >
      <div class="rounded-3xl shadow-lg w-full max-w-2xl p-6 modal-theme max-h-[80vh] overflow-y-auto">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-xl font-semibold flex items-center">
            <i class="bi bi-pin-angle-fill text-yellow-500 me-2"></i> Pinned Resources
          </h3>
          <button @click="showPinnedModal = false" class="text-gray-500 hover:text-gray-700">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>

        <div v-if="pinnedResources.length === 0" class="text-center py-8 text-gray-400">
          <i class="bi bi-pin-angle text-4xl mb-2"></i>
          <p>No pinned resources yet</p>
          <p class="text-sm">Click the pin icon on any resource to pin it here</p>
        </div>

        <div v-else class="space-y-3">
          <div v-for="res in pinnedResources" :key="res.id" class="card-theme p-4 rounded-xl shadow flex items-start gap-3">
            <i class="bi bi-pin-angle-fill text-yellow-500 text-lg mt-1"></i>
            <div class="flex-1">
              <h4 class="font-semibold card-title mb-1">{{ res.title }}</h4>
              <div v-if="res.resource_type === 'document'" class="text-sm card-subtext">
                📄 {{ res.file_name }}
              </div>
              <div v-if="res.resource_type === 'link'" class="text-sm text-blue-600 break-all">
                🔗 <a :href="res.url" target="_blank" class="underline hover:text-blue-800">{{ res.url }}</a>
              </div>
              <p class="text-xs card-subtext mt-1">Added {{ new Date(res.created_at).toLocaleDateString() }}</p>
            </div>
            <div class="flex gap-2">
              <button @click="togglePin(res.id)" class="text-sm text-yellow-500 hover:text-yellow-600">
                <i class="bi bi-pin-angle-fill"></i>
              </button>
              <a v-if="getResourceUrl(res)" :href="getResourceUrl(res)" target="_blank" class="text-sm text-blue-500 hover:text-blue-600">
                <i class="bi bi-box-arrow-up-right"></i>
              </a>
            </div>
          </div>
        </div>

        <div class="mt-6 text-right">
          <button @click="showPinnedModal = false" class="px-4 py-2 rounded-full border hover:bg-gray-100">
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { useThemeStore } from '@/stores/theme';
import { useUserStore } from '@/stores/user'
import Sidebar from '@/components/layout/StudentLayout/SideBar.vue'
import HeaderBar from '@/components/layout/StudentLayout/HeaderBar.vue'
import RightPanel from '@/components/layout/StudentLayout/RightPanel.vue'
import { getMyCoures } from '@/api/courses'
import * as studentResourcesAPI from '@/api/studentResources'

import algorithms from '@/assets/algorithms.jpg'
import systems from '@/assets/systems.jpg'
import linearAlgebra from '@/assets/linear-algebra.jpg'
import worldHistory from '@/assets/world-history.jpg'

const courseImages = {
  1: algorithms,
  2: systems,
  3: linearAlgebra,
  4: worldHistory,
}

export default {
  components: { Sidebar, HeaderBar, RightPanel },
  setup() {
    const themeStore = useThemeStore();
    const userStore = useUserStore();
    return { themeStore, userStore };
  },
  data() {
    return {
      showAddResource: false,
      showStudyBreak: false,
      isOnBreak: false,
      loadingCourses: true,
      loadingResources: false,
      courses: [],
      deadlineCount: 0,
      breakTime: 0,
      breakTimer: null,
      customBreak: '',
      resources: [],
      pinnedResources: [],
      showPinnedModal: false,
      actionNotices: {},
      actionTimers: {},
    }
  },
  computed: {
    formattedTime() {
      const m = Math.floor(this.breakTime / 60)
      const s = this.breakTime % 60
      return `${m}:${s.toString().padStart(2, '0')}`
    },
    pinnedCount() {
      return this.resources.filter(r => r.isPinned).length
    },
  },
  async mounted() {
    await this.loadUserCourses()
    this.loadResources()
  },
  methods: {
    async loadUserCourses() {
      try {
        this.loadingCourses = true
        this.courses = await getMyCoures()
        this.deadlineCount = 0 // TODO: Calculate from course assignments
      } catch (error) {
        console.error('Failed to load courses:', error)
        this.courses = []
      } finally {
        this.loadingCourses = false
      }
    },
    getCourseImage(courseId) {
      return courseImages[courseId] || algorithms
    },
    async saveResource() {
      const docInput = this.$refs.docInput?.files?.[0];
      const imgInput = this.$refs.imgInput?.files?.[0];
      const linkInput = this.$refs.linkInput?.value?.trim();

      if (!docInput && !imgInput && !linkInput) {
        alert('Please add a document, image, or link');
        return;
      }

      try {
        this.loadingResources = true;

        if (docInput) {
          await studentResourcesAPI.uploadDocument(docInput);
        }

        if (imgInput) {
          await studentResourcesAPI.uploadImage(imgInput);
        }

        if (linkInput) {
          await studentResourcesAPI.addLink(linkInput);
        }

        await this.loadResources();
        this.showAddResource = false;

        if (this.$refs.docInput) this.$refs.docInput.value = '';
        if (this.$refs.imgInput) this.$refs.imgInput.value = '';
        if (this.$refs.linkInput) this.$refs.linkInput.value = '';
      } catch (error) {
        console.error('Failed to save resource:', error);
        alert('Failed to save resource. Please try again.');
      } finally {
        this.loadingResources = false;
      }
    },
    startBreak(mins) {
      this.showStudyBreak = false
      this.isOnBreak = true
      this.breakTime = mins * 60
      this.breakTimer = setInterval(() => {
        if (this.breakTime > 0) this.breakTime--
        else {
          this.endBreak()
          alert('Break over! Time to study again!')
        }
      }, 1000)
    },
    startCustomBreak() {
      const mins = parseInt(this.customBreak)
      if (!mins || mins <= 0) return alert('Enter a valid number!')
      this.startBreak(mins)
      this.customBreak = ''
    },
    endBreak() {
      clearInterval(this.breakTimer)
      this.isOnBreak = false
      this.breakTime = 0
    },
    async loadResources() {
      try {
        this.loadingResources = true
        const data = await studentResourcesAPI.getMyResources()
        this.resources = data.map(r => ({
          ...r,
          isPinned: r.is_pinned || false
        }))
        this.pinnedResources = this.resources.filter(r => r.isPinned)
      } catch (error) {
        console.error('Failed to load resources:', error)
        this.resources = []
        this.pinnedResources = []
      } finally {
        this.loadingResources = false
      }
    },
    getResourceUrl(resource) {
      if (resource.resource_type === 'link') {
        return resource.url;
      }
      if (resource.file_path) {
        return studentResourcesAPI.getDownloadUrl(resource.id);
      }
      return null;
    },
    async deleteResource(resourceId) {
      if (!confirm('Are you sure you want to delete this resource?')) {
        return;
      }

      try {
        await studentResourcesAPI.deleteResource(resourceId);
        await this.loadResources();
      } catch (error) {
        console.error('Failed to delete resource:', error);
        alert('Failed to delete resource. Please try again.');
      }
    },
    async togglePin(resourceId) {
      try {
        const updated = await studentResourcesAPI.togglePinResource(resourceId)
        
        // Update local state
        const resource = this.resources.find(r => r.id === resourceId)
        if (resource) {
          resource.isPinned = updated.is_pinned
        }
        
        // Update pinned resources list
        this.pinnedResources = this.resources.filter(r => r.isPinned)
      } catch (error) {
        console.error('Failed to toggle pin:', error)
        alert('Failed to update pin status. Please try again.')
      }
    },
    openPinnedResources() {
      this.showPinnedModal = true
    },
    openResourceFromPanel(resource) {
      const url = this.getResourceUrl(resource)
      if (url) {
        window.open(url, '_blank')
      }
    },
    showComingSoon(courseId, label) {
      if (this.actionTimers[courseId]) clearTimeout(this.actionTimers[courseId])
      const message = `${label} coming soon`
      this.actionNotices = { ...this.actionNotices, [courseId]: message }
      this.actionTimers = {
        ...this.actionTimers,
        [courseId]: setTimeout(() => {
          const { [courseId]: _, ...restNotices } = this.actionNotices
          this.actionNotices = restNotices
          const { [courseId]: __, ...restTimers } = this.actionTimers
          this.actionTimers = restTimers
        }, 2000),
      }
    },
  },
}
</script>

<style>
.main-theme {
  background: var(--page-bg);
  color: var(--color-text-primary);
  transition: background 0.3s, color 0.3s;
}
.section-theme {
  background: var(--color-bg-section);
  color: var(--color-text-primary);
  transition: background 0.3s, color 0.3s;
}
.section-text {
  color: var(--color-text-primary);
}
.section-subtext {
  color: var(--color-text-secondary);
}
.filter-btn {
  border-color: var(--color-btn-border);
  background: var(--color-btn-bg);
  color: var(--color-btn-text);
}
.filter-btn-active {
  background: var(--color-btn-active-bg);
  color: var(--color-btn-active-text);
  border-color: var(--color-btn-active-border);
}
.filter-btn-inactive {
  background: var(--color-btn-bg);
  color: var(--color-btn-text);
  border-color: var(--color-btn-border);
}
.add-resource-btn {
  border-color: var(--color-btn-green-border);
  color: var(--color-btn-green-text);
  background: var(--color-btn-bg);
}
.study-break-btn {
  border-color: var(--color-btn-yellow-border);
  color: var(--color-btn-yellow-text);
  background: var(--color-btn-bg);
}
.card-theme {
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  transition: background 0.3s, color 0.3s;
}
.card-content-theme {
  background: var(--color-bg-card);
  color: var(--color-text-primary);
}
.card-title {
  color: var(--color-text-primary);
}
.card-subtext {
  color: var(--color-text-secondary);
}
.card-btn-blue {
  border-color: var(--color-btn-blue-border);
  color: var(--color-btn-blue-text);
  background: var(--color-btn-bg);
}
.card-btn-green {
  border-color: var(--color-btn-green-border);
  color: var(--color-btn-green-text);
  background: var(--color-btn-bg);
}
.card-status {
  color: var(--color-status-text);
  background: var(--color-status-bg);
}
.right-panel-theme {
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  border-color: var(--color-border);
}
.modal-theme {
  background: var(--color-bg-card);
  color: var(--color-text-primary);
}
</style>
