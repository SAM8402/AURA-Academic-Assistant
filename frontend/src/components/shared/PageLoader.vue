
<template>
  <div class="page-loader" :class="{ 'page-loader--fullscreen': fullscreen }">
    <div class="loader-content">
      <!-- Animated logo -->
      <div class="loader-logo">
        <div class="loader-ring"></div>
        <div class="loader-ring loader-ring--inner"></div>
        <span class="loader-letter">A</span>
      </div>

      <!-- Loading text -->
      <p v-if="text" class="loader-text">{{ text }}</p>

      <!-- Progress dots -->
      <div class="loader-dots">
        <span class="dot" v-for="i in 3" :key="i" :style="{ animationDelay: `${(i - 1) * 0.15}s` }"></span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  text: { type: String, default: 'Loading...' },
  fullscreen: { type: Boolean, default: false }
})
</script>

<style scoped>
.page-loader {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
}

.page-loader--fullscreen {
  position: fixed;
  inset: 0;
  z-index: 9998;
  background-color: var(--page-bg, #fff);
}

.loader-content {
  text-align: center;
}

.loader-logo {
  position: relative;
  width: 72px;
  height: 72px;
  margin: 0 auto 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loader-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 3px solid transparent;
  border-top-color: var(--accent-blue, #2563eb);
  animation: spin 1s linear infinite;
}

.loader-ring--inner {
  inset: 8px;
  border-top-color: var(--accent-purple, #7c3aed);
  animation-direction: reverse;
  animation-duration: 0.75s;
}

.loader-letter {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--accent-blue, #2563eb);
  z-index: 1;
}

.loader-text {
  color: var(--text-secondary, #495057);
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
}

.loader-dots {
  display: flex;
  gap: 6px;
  justify-content: center;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--accent-blue, #2563eb);
  animation: dot-pulse 1.2s ease-in-out infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes dot-pulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}
</style>
