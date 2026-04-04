<template>
  <div
    class="min-h-screen flex items-center justify-center p-6 relative overflow-hidden bg-gradient-to-br from-blue-500 via-indigo-500 to-purple-600 animate-gradientMove"
    :style="{ color: themeStore?.currentTheme === 'dark' ? 'white' : 'black' }"
  >
    <!-- Soft glowing overlay -->
    <div
      class="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,_var(--tw-gradient-stops))] from-indigo-500/40 via-transparent to-transparent animate-pulse-slow"
    ></div>

    <!-- Timer Card -->
    <div
      class="relative bg-white/90 backdrop-blur-lg shadow-2xl rounded-3xl p-8 w-full max-w-md flex flex-col items-center space-y-6 border border-gray-100 transition-transform duration-700 hover:scale-[1.02]"
      :style="{ color: themeStore?.currentTheme === 'dark' ? 'white' : 'black' }"
    >
      <h2 class="text-3xl font-bold" :style="{ color: themeStore?.currentTheme === 'dark' ? 'white' : 'black' }"> Study Break Timer</h2>
      <p class="text-center text-sm" :style="{ color: themeStore?.currentTheme === 'dark' ? 'white' : 'black' }">
        Focus. Breathe. Recharge.
      </p>

      <!-- Circular Progress Timer -->
      <div class="relative w-52 h-52">
        <svg class="w-full h-full transform -rotate-90">
          <circle
            class="text-gray-200"
            stroke-width="10"
            stroke="currentColor"
            fill="transparent"
            r="95"
            cx="104"
            cy="104"
          />
          <circle
            class="text-indigo-600 transition-all duration-300 ease-out"
            stroke-width="10"
            stroke-dasharray="597"
            :stroke-dashoffset="dashOffset"
            stroke-linecap="round"
            stroke="currentColor"
            fill="transparent"
            r="95"
            cx="104"
            cy="104"
          />
        </svg>

        <!-- Timer Text -->
        <div
          class="absolute inset-0 flex flex-col items-center justify-center text-center animate-fadeIn"
        >
          <span class="text-5xl font-bold" :style="{ color: themeStore?.currentTheme === 'dark' ? 'white' : 'black' }">
            {{ minutes.toString().padStart(2, '0') }}:{{ seconds
              .toString()
              .padStart(2, '0') }}
          </span>
          <span class="text-sm mt-1" :style="{ color: themeStore?.currentTheme === 'dark' ? 'white' : 'black' }">remaining</span>
        </div>
      </div>

      <!-- Buttons -->
      <div class="flex gap-3" :style="{ color: themeStore?.currentTheme === 'dark' ? 'white' : 'black' }">
        <button
          v-if="!isRunning"
          @click="startTimer"
          class="px-6 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition"
          :style="{ color: themeStore?.currentTheme === 'dark' ? 'white' : 'black' }"
        >
          Start
        </button>
        <button
          v-else
          @click="pauseTimer"
          class="px-6 py-2 bg-yellow-500 text-white font-medium rounded-lg hover:bg-yellow-600 transition"
          :style="{ color: themeStore?.currentTheme === 'dark' ? 'white' : 'black' }"
        >
          Pause
        </button>
        <button
          @click="resetTimer"
          class="px-6 py-2 bg-gray-200 font-medium rounded-lg hover:bg-gray-300 transition"
          :style="{ color: 'var(--color-text-primary)' }"
        >
          Reset
        </button>
      </div>

      <!-- Session Stats -->
      <div class="mt-4 text-center" :style="{ color: themeStore?.currentTheme === 'dark' ? 'white' : 'black' }">
        <p class="text-sm">
          Focus Sessions:
          <span class="font-semibold" :style="{ color: themeStore?.currentTheme === 'dark' ? 'white' : 'black' }">{{ sessions }}</span>
        </p>
      </div>

      <!-- Motivational Quote -->
      <div
        class="bg-indigo-50 rounded-xl p-3 text-center text-sm mt-4 animate-fadeIn delay-500"
        :style="{ color: themeStore?.currentTheme === 'dark' ? 'white' : 'black' }"
      >
        "{{ randomQuote }}"
      </div>
    </div>
  </div>
</template>

<script setup>
import { useThemeStore } from '@/stores/theme';
const themeStore = useThemeStore();
import { ref, computed, onUnmounted } from "vue";

const totalTime = 25 * 60; // 25 min default
const timeLeft = ref(totalTime);
const isRunning = ref(false);
const sessions = ref(0);
let timerInterval = null;

// Motivational quotes
const quotes = [
  "Small breaks make big focus possible.",
  "Reset your mind. Refocus your energy.",
  "Every short pause sharpens your clarity.",
  "The best work needs the best rest.",
  "You’re doing better than you think."
];
const randomQuote = quotes[Math.floor(Math.random() * quotes.length)];

const minutes = computed(() => Math.floor(timeLeft.value / 60));
const seconds = computed(() => timeLeft.value % 60);
const circumference = 2 * Math.PI * 95;
const dashOffset = computed(() => {
  const progress = timeLeft.value / totalTime;
  return circumference * (1 - progress);
});

function startTimer() {
  if (isRunning.value) return;
  isRunning.value = true;
  timerInterval = setInterval(() => {
    if (timeLeft.value > 0) timeLeft.value--;
    else {
      clearInterval(timerInterval);
      isRunning.value = false;
      sessions.value++;
      alert("Time’s up! Take a short break before your next session.");
      resetTimer();
    }
  }, 1000);
}

function pauseTimer() {
  isRunning.value = false;
  clearInterval(timerInterval);
}

function resetTimer() {
  clearInterval(timerInterval);
  isRunning.value = false;
  timeLeft.value = totalTime;
}

onUnmounted(() => clearInterval(timerInterval));
</script>

<style scoped>
@keyframes gradientMove {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}
.animate-gradientMove {
  background-size: 200% 200%;
  animation: gradientMove 8s ease infinite;
}
.animate-pulse-slow {
  animation: pulse 4s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% {
    opacity: 0.5;
  }
  50% {
    opacity: 0.8;
  }
}
.animate-fadeIn {
  animation: fadeIn 1s ease-in-out forwards;
}
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
</style>
