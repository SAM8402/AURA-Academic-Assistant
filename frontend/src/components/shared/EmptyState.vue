<script setup>
defineProps({
  title: {
    type: String,
    default: 'Nothing here yet'
  },
  description: {
    type: String,
    default: ''
  },
  actionLabel: {
    type: String,
    default: ''
  }
})

defineEmits(['action'])
</script>

<template>
  <div
    class="flex flex-col items-center justify-center text-center py-12 px-6"
    role="status"
  >
    <!-- Icon slot -->
    <div
      class="w-16 h-16 rounded-full flex items-center justify-center mb-4"
      :style="{ backgroundColor: 'var(--bg-tertiary)' }"
    >
      <slot name="icon">
        <svg
          class="w-8 h-8"
          :style="{ color: 'var(--text-muted)' }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
            d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
          />
        </svg>
      </slot>
    </div>

    <h3
      class="text-lg font-semibold mb-1"
      :style="{ color: 'var(--text-primary)' }"
    >
      {{ title }}
    </h3>

    <p
      v-if="description"
      class="text-sm max-w-sm mb-4"
      :style="{ color: 'var(--text-tertiary)' }"
    >
      {{ description }}
    </p>

    <slot name="action">
      <button
        v-if="actionLabel"
        @click="$emit('action')"
        class="px-4 py-2 rounded-lg text-sm font-medium transition-opacity duration-200 cursor-pointer min-h-[44px]"
        :style="{
          backgroundColor: 'var(--accent-blue)',
          color: '#ffffff'
        }"
        @mouseenter="$event.target.style.opacity = '0.9'"
        @mouseleave="$event.target.style.opacity = '1'"
      >
        {{ actionLabel }}
      </button>
    </slot>
  </div>
</template>
