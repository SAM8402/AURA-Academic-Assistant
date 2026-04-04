<script setup>
import { ref, onMounted } from 'vue'
import { api } from '@/api'
import { useThemeStore } from '@/stores/theme'
import Sidebar from '@/components/layout/TaLayout/TASidebar.vue'
import HeaderBar from '@/components/layout/TaLayout/TaHeaderBar.vue'

import {
  CheckCircleIcon,
  TrashIcon,
  EnvelopeIcon,
  Cog6ToothIcon,
  ClipboardDocumentListIcon,
  AcademicCapIcon,
  ChatBubbleLeftRightIcon,
  ClockIcon,
  ArrowRightOnRectangleIcon,
} from "@heroicons/vue/24/outline"

// Reactive state
const user = ref(null)
const profile = ref(null)
const isLoading = ref(true)
const isSaving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

// Initialize theme store
const themeStore = useThemeStore()

// Form data
const formData = ref({
  full_name: '',
  email: '',
  department: '',
  phone: '',
  bio: '',
  current_password: '',
  new_password: '',
  confirm_password: ''
})

// Fetch user profile
async function fetchProfile() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const response = await api.get('/auth/me')
    user.value = response.data
    
    // Populate form data
    formData.value.full_name = user.value.full_name || ''
    formData.value.email = user.value.email || ''
    formData.value.department = user.value.profile?.department || ''
    formData.value.phone = user.value.profile?.phone || ''
    formData.value.bio = user.value.profile?.bio || ''
    
    profile.value = user.value.profile || {}
  } catch (error) {
    console.error('Failed to load profile:', error)
    errorMessage.value = 'Failed to load profile data'
  } finally {
    isLoading.value = false
  }
}

// Update profile
async function updateProfile() {
  isSaving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  
  try {
    const updateData = {
      full_name: formData.value.full_name,
      email: formData.value.email
    }
    
    // Include password change if new password provided
    if (formData.value.new_password) {
      if (formData.value.new_password !== formData.value.confirm_password) {
        errorMessage.value = 'New passwords do not match'
        isSaving.value = false
        return
      }
      if (!formData.value.current_password) {
        errorMessage.value = 'Current password is required to change password'
        isSaving.value = false
        return
      }
      updateData.current_password = formData.value.current_password
      updateData.new_password = formData.value.new_password
    }
    
    const response = await api.put('/auth/me', updateData)
    user.value = response.data
    successMessage.value = 'Profile updated successfully!'
    
    // Clear password fields
    formData.value.current_password = ''
    formData.value.new_password = ''
    formData.value.confirm_password = ''
    
    // Auto-hide success message after 3 seconds
    setTimeout(() => {
      successMessage.value = ''
    }, 3000)
  } catch (error) {
    console.error('Failed to update profile:', error)
    errorMessage.value = error.response?.data?.detail || 'Failed to update profile'
  } finally {
    isSaving.value = false
  }
}

// Sign out
function signOut() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  window.location.href = '/login'
}

onMounted(() => {
  fetchProfile()
})
</script>

<template>
  <div class="flex min-h-screen bg-gray-50">
    <Sidebar class="fixed top-0 left-0 h-screen w-[250px]" />

    <main class="flex-1 p-8 ml-[250px] overflow-y-auto">
      <HeaderBar searchPlaceholder="Search students, courses, or threads" />

      <h2 class="font-bold text-2xl mb-6">TA Settings</h2>

      <!-- Loading State -->
      <div v-if="isLoading" class="text-center py-12">
        <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <p class="mt-4 text-gray-600">Loading profile...</p>
      </div>

      <!-- Error Message -->
      <div v-if="errorMessage" class="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg">
        {{ errorMessage }}
      </div>

      <!-- Success Message -->
      <div v-if="successMessage" class="mb-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg">
        {{ successMessage }}
      </div>

      <div v-if="!isLoading && user" class="grid grid-cols-12 gap-8">
        <!-- Left main content -->
        <div class="col-span-8 space-y-8">
          <!-- Profile Card -->
          <div
            class="bg-white rounded-2xl p-6 shadow cursor-pointer flex flex-col sm:flex-row items-start gap-8 hover:shadow-xl transition group"
          >
            <div class="flex flex-col items-center min-w-[120px]">
              <img
                :src="profile.avatar_url || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(user.full_name || user.email)"
                alt="Profile avatar"
                class="w-20 h-20 rounded-full object-cover border-4 border-blue-100 shadow mb-3 transition group-hover:scale-110"
              />
              <button
                class="px-4 py-1 bg-blue-100 text-blue-700 font-semibold rounded-lg text-xs hover:bg-blue-200 active:scale-95 transition"
              >Change avatar</button>
              <span
                class="mt-2 text-xs bg-green-100 text-green-800 rounded-full px-2 py-1 font-semibold"
              >{{ user.role.toUpperCase() }}</span>
            </div>

            <form @submit.prevent="updateProfile" class="flex-1 w-full grid grid-cols-1 gap-3">
              <div class="grid md:grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs text-gray-700 mb-1">Full name</label>
                  <input
                    type="text"
                    v-model="formData.full_name"
                    class="w-full border rounded-lg p-2 mb-3 focus:ring focus:border-blue-400 hover:border-blue-400 transition"
                    required
                  />
                  <label class="block text-xs text-gray-700 mb-1">Institute email</label>
                  <input
                    type="email"
                    v-model="formData.email"
                    class="w-full border rounded-lg p-2 mb-3 focus:ring focus:border-blue-400 hover:border-blue-400 transition"
                    required
                  />
                  <label class="block text-xs text-gray-700 mb-1">Department</label>
                  <input
                    type="text"
                    v-model="formData.department"
                    class="w-full border rounded-lg p-2 mb-3 focus:ring focus:border-blue-400 hover:border-blue-400 transition"
                    placeholder="e.g., Data Science"
                  />
                </div>
                <div class="flex flex-col items-start gap-3 justify-center">
                  <label class="hidden sm:block text-xs text-gray-700 mb-1">&nbsp;</label>
                  <button
                    type="submit"
                    :disabled="isSaving"
                    class="w-full py-2 flex items-center justify-center gap-2 bg-blue-500 text-white font-semibold rounded-lg shadow hover:bg-blue-600 active:scale-95 transition disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <CheckCircleIcon class="w-5 h-5" />
                    {{ isSaving ? 'Saving...' : 'Save changes' }}
                  </button>
                </div>
              </div>
            </form>
          </div>

          <!-- Password Change Section -->
          <div class="bg-white rounded-2xl p-6 shadow space-y-4 hover:shadow-lg transition">
            <div class="font-bold text-lg">Change Password</div>
            <div class="grid md:grid-cols-2 gap-4">
              <div>
                <label class="block text-xs text-gray-700 mb-1">Current Password</label>
                <input
                  type="password"
                  v-model="formData.current_password"
                  class="w-full border rounded-lg p-2 focus:ring focus:border-blue-400 hover:border-blue-400 transition"
                  placeholder="Enter current password"
                />
              </div>
              <div>
                <label class="block text-xs text-gray-700 mb-1">New Password</label>
                <input
                  type="password"
                  v-model="formData.new_password"
                  class="w-full border rounded-lg p-2 focus:ring focus:border-blue-400 hover:border-blue-400 transition"
                  placeholder="Enter new password"
                />
              </div>
              <div>
                <label class="block text-xs text-gray-700 mb-1">Confirm New Password</label>
                <input
                  type="password"
                  v-model="formData.confirm_password"
                  class="w-full border rounded-lg p-2 focus:ring focus:border-blue-400 hover:border-blue-400 transition"
                  placeholder="Confirm new password"
                />
              </div>
            </div>
            <button
              @click="updateProfile"
              :disabled="isSaving"
              class="px-6 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 active:scale-95 transition disabled:opacity-50"
            >
              Update Password
            </button>
          </div>

          <!-- Responsibilities -->
          <div class="bg-white rounded-2xl p-6 shadow space-y-2 hover:shadow-lg transition">
            <div class="font-bold mb-2">Responsibilities</div>
            <ul class="text-sm text-gray-700 space-y-2">
              <li class="flex items-center gap-2">
                <ClipboardDocumentListIcon class="w-4 h-4 text-blue-600" /> Grading and assignment
                review
              </li>
              <li class="flex items-center gap-2">
                <ChatBubbleLeftRightIcon class="w-4 h-4 text-blue-600" /> Student query resolution
              </li>
              <li class="flex items-center gap-2">
                <ClockIcon class="w-4 h-4 text-blue-600" /> Office hours and support sessions
              </li>
              <li class="flex items-center gap-2">
                <AcademicCapIcon class="w-4 h-4 text-blue-600" /> Assisting instructors with
                course materials
              </li>
            </ul>
          </div>

          <!-- Theme Preferences -->
          <div class="bg-white rounded-2xl p-6 shadow hover:shadow-lg transition">
            <div class="font-bold mb-4">Appearance Preferences</div>
            <div class="flex gap-6 flex-wrap">
              <div>
                <div class="text-xs mb-2 font-semibold text-gray-700">Theme</div>
                <div class="flex gap-2">
                  <button 
                    @click="themeStore.setTheme('light')"
                    :class="[
                      'border-2 rounded-lg px-4 py-2 transition active:scale-95 font-semibold',
                      themeStore.currentTheme === 'light' 
                        ? 'border-blue-600 bg-blue-50 text-blue-600 shadow-sm' 
                        : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50 bg-white text-gray-700'
                    ]"
                  >
                    Light
                  </button>
                  <button 
                    @click="themeStore.setTheme('dark')"
                    :class="[
                      'border-2 rounded-lg px-4 py-2 transition active:scale-95 font-semibold',
                      themeStore.currentTheme === 'dark' 
                        ? 'border-blue-600 bg-blue-50 text-blue-600 shadow-sm' 
                        : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50 bg-white text-gray-700'
                    ]"
                  >
                    Dark
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Statistics -->
          <div class="bg-white rounded-2xl p-6 shadow hover:shadow-lg transition">
            <div class="font-bold mb-4">TA Statistics</div>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div class="text-center p-4 bg-blue-50 rounded-lg">
                <div class="text-2xl font-bold text-blue-600">{{ profile.query_count || 0 }}</div>
                <div class="text-xs text-gray-600">Queries Handled</div>
              </div>
              <div class="text-center p-4 bg-green-50 rounded-lg">
                <div class="text-2xl font-bold text-green-600">{{ profile.resolved_count || 0 }}</div>
                <div class="text-xs text-gray-600">Resolved</div>
              </div>
              <div class="text-center p-4 bg-purple-50 rounded-lg">
                <div class="text-2xl font-bold text-purple-600">{{ profile.resource_count || 0 }}</div>
                <div class="text-xs text-gray-600">Resources</div>
              </div>
              <div class="text-center p-4 bg-orange-50 rounded-lg">
                <div class="text-2xl font-bold text-orange-600">{{ profile.reputation_score || 0 }}</div>
                <div class="text-xs text-gray-600">Reputation</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Sidebar (Right) -->
        <div class="col-span-4 space-y-6">
          <div class="bg-white rounded-2xl p-6 shadow hover:shadow-lg transition">
            <div class="font-bold">TA Summary</div>
            <div class="text-xs text-gray-700 mt-1">TA ID: <span class="font-mono">{{ user.id }}</span></div>
            <div class="text-xs text-gray-700">Email: {{ user.email }}</div>
            <div class="text-xs text-gray-700">Department: {{ formData.department || 'Not specified' }}</div>
            <div class="text-xs text-gray-700">Joined: {{ new Date(user.created_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) }}</div>
            <div class="text-xs text-gray-700 mt-2">
              Status: 
              <span :class="user.is_active ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'">
                {{ user.is_active ? 'Active' : 'Inactive' }}
              </span>
            </div>
          </div>

          <div class="bg-white rounded-2xl p-6 shadow hover:shadow-lg transition">
            <div class="font-bold mb-2">Shortcuts</div>
            <div class="space-y-2">
              <button
                class="flex items-center gap-2 w-full text-left text-sm hover:text-blue-700 hover:bg-blue-50 rounded-lg px-2 py-2 transition"
              >
                <Cog6ToothIcon class="w-4 h-4" />Manage Course Materials
              </button>
              <button
                class="flex items-center gap-2 w-full text-left text-sm hover:text-blue-700 hover:bg-blue-50 rounded-lg px-2 py-2 transition"
              >
                <EnvelopeIcon class="w-4 h-4" />Student Communication
              </button>
              <button
                class="flex items-center gap-2 w-full text-left text-sm hover:text-blue-700 hover:bg-blue-50 rounded-lg px-2 py-2 transition"
              >
                <CheckCircleIcon class="w-4 h-4" />Report Submission Status
              </button>
            </div>
          </div>

          <div class="bg-white rounded-2xl p-6 shadow hover:shadow-lg transition">
            <div class="font-bold mb-2">Session</div>
            <div class="text-xs text-gray-700">Last login: {{ new Date(user.updated_at || user.created_at).toLocaleString() }}</div>
            <button
              @click="signOut"
              class="mt-4 px-3 py-2 border border-blue-600 bg-blue-50 rounded-lg text-blue-700 font-semibold w-full flex items-center justify-center gap-2 hover:bg-blue-100 hover:border-blue-800 active:scale-95 transition"
            >
              <ArrowRightOnRectangleIcon class="w-5 h-5" />Sign out
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* All hover and focus effects are included via Tailwind classes */
</style>
