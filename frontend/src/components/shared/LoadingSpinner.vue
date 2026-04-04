<script setup>
import { computed } from 'vue'

const props = defineProps({
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg'].includes(v)
  },
  color: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'white', 'gray'].includes(v)
  },
  text: {
    type: String,
    default: ''
  },
  fullPage: {
    type: Boolean,
    default: false
  }
})

const sizeClasses = computed(() => {
  const map = {
    sm: 'w-5 h-5 border-2',
    md: 'w-8 h-8 border-[3px]',
    lg: 'w-12 h-12 border-4'
  }
  return map[props.size]
})

const textSizeClasses = computed(() => {
  const map = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base'
  }
  return map[props.size]
})

const colorClasses = computed(() => {
  const map = {
    primary: 'border-[var(--border-light)] border-t-[var(--accent-blue)]',
    white: 'border-white/30 border-t-white',
    gray: 'border-[var(--border-light)] border-t-[var(--text-tertiary)]'
  }
  return map[props.color]
})
</script>

<template>
  <div
    :class="[
      'flex flex-col items-center justify-center gap-3',
      fullPage ? 'min-h-[200px]' : ''
    ]"
    role="status"
    aria-live="polite"
  >
    <div
      :class="['animate-spin rounded-full', sizeClasses, colorClasses]"
    ></div>
    <p
      v-if="text"
      :class="['font-medium', textSizeClasses]"
      :style="{ color: 'var(--text-secondary)' }"
    >
      {{ text }}
    </p>
    <span class="sr-only">Loading...</span>
  </div>
</template>

<style scoped>
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
</style>
