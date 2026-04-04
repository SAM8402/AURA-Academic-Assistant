
<template>
  <div v-if="hasError" class="min-h-screen flex items-center justify-center" style="background-color: var(--page-bg);">
    <div class="text-center p-8 animate-fade-in-scale">
      <div class="w-16 h-16 mx-auto mb-6 rounded-full flex items-center justify-center" style="background-color: var(--error-bg);">
        <svg class="w-8 h-8" style="color: var(--error-text);" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>
      </div>
      <h2 class="text-2xl font-bold mb-2" style="color: var(--text-primary);">Something went wrong</h2>
      <p class="mb-6" style="color: var(--text-secondary);">An unexpected error occurred. Please try again.</p>
      <div class="flex gap-3 justify-center">
        <button @click="goHome" class="px-5 py-2.5 rounded-lg font-medium transition-colors duration-200 cursor-pointer" style="background-color: var(--bg-tertiary); color: var(--text-primary);">Go Home</button>
        <button @click="retry" class="px-5 py-2.5 rounded-lg font-medium text-white transition-colors duration-200 cursor-pointer" style="background-color: var(--accent-blue);">Retry</button>
      </div>
    </div>
  </div>
  <router-view v-else v-slot="{ Component }">
    <transition name="page" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue'
import { useRouter } from 'vue-router'

// Load theme LAST to override all other CSS
import './styles/theme.css'

const router = useRouter()
const hasError = ref(false)

onErrorCaptured((err) => {
  console.error('App error:', err)
  hasError.value = true
  return false
})

const goHome = () => {
  hasError.value = false
  router.push('/')
}

const retry = () => {
  hasError.value = false
  window.location.reload()
}
</script>

<style>
.page-enter-active,
.page-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
