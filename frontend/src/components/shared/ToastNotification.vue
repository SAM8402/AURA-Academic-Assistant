<script setup>
import { ref, computed, onUnmounted } from 'vue'

const props = defineProps({
  type: {
    type: String,
    default: 'info',
    validator: (v) => ['success', 'error', 'warning', 'info'].includes(v)
  },
  title: {
    type: String,
    default: ''
  },
  message: {
    type: String,
    required: true
  },
  duration: {
    type: Number,
    default: 5000
  },
  dismissible: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['dismiss'])

const visible = ref(true)
let timer = null

if (props.duration > 0) {
  timer = setTimeout(() => {
    dismiss()
  }, props.duration)
}

const dismiss = () => {
  visible.value = false
  clearTimeout(timer)
  emit('dismiss')
}

onUnmounted(() => {
  clearTimeout(timer)
})

const typeConfig = computed(() => {
  const configs = {
    success: {
      bg: 'var(--success-bg)',
      border: 'var(--accent-green)',
      iconColor: 'var(--accent-green)',
      iconPath: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z'
    },
    error: {
      bg: 'var(--error-bg)',
      border: 'var(--accent-red)',
      iconColor: 'var(--accent-red)',
      iconPath: 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z'
    },
    warning: {
      bg: 'var(--warning-bg)',
      border: 'var(--accent-yellow)',
      iconColor: 'var(--accent-yellow)',
      iconPath: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z'
    },
    info: {
      bg: 'var(--info-bg)',
      border: 'var(--accent-blue)',
      iconColor: 'var(--accent-blue)',
      iconPath: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
    }
  }
  return configs[props.type]
})
</script>

<template>
  <Transition name="toast">
    <div
      v-if="visible"
      class="flex items-start gap-3 p-4 rounded-lg border-l-4 shadow-lg max-w-sm w-full"
      :style="{
        backgroundColor: typeConfig.bg,
        borderLeftColor: typeConfig.border
      }"
      role="alert"
      aria-live="assertive"
    >
      <svg
        class="w-5 h-5 flex-shrink-0 mt-0.5"
        :style="{ color: typeConfig.iconColor }"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          :d="typeConfig.iconPath"
        />
      </svg>

      <div class="flex-1 min-w-0">
        <p
          v-if="title"
          class="text-sm font-semibold mb-0.5"
          :style="{ color: 'var(--text-primary)' }"
        >
          {{ title }}
        </p>
        <p
          class="text-sm"
          :style="{ color: 'var(--text-secondary)' }"
        >
          {{ message }}
        </p>
      </div>

      <button
        v-if="dismissible"
        @click="dismiss"
        class="flex-shrink-0 p-1 rounded transition-colors duration-200 cursor-pointer min-w-[28px] min-h-[28px] flex items-center justify-center"
        :style="{ color: 'var(--text-tertiary)' }"
        aria-label="Dismiss notification"
        @mouseenter="$event.target.style.backgroundColor = 'var(--bg-hover)'"
        @mouseleave="$event.target.style.backgroundColor = 'transparent'"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.toast-enter-active {
  animation: slideIn 0.3s ease-out;
}
.toast-leave-active {
  animation: slideOut 0.2s ease-in;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes slideOut {
  from {
    transform: translateX(0);
    opacity: 1;
  }
  to {
    transform: translateX(100%);
    opacity: 0;
  }
}
</style>
