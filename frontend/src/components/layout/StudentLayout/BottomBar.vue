<template>
  <footer
    class="fixed bottom-0 left-[250px] right-80 z-[100] px-6 py-4 border-t"
    :style="{ background: 'var(--bg-primary)', borderColor: 'var(--border-default)' }"
  >
    <div class="flex items-end justify-center gap-3 w-full max-w-xl mx-auto">
      <!-- Main Input Container -->
      <div class="flex-1 relative">
        <!-- Auto-expanding Textarea -->
        <textarea
          v-model="message"
          placeholder="Message AURA..."
          rows="1"
          ref="textareaRef"
          @input="autoResize"
          @keydown.enter.exact.prevent="sendMessage"
          class="w-full resize-none rounded-2xl px-4 py-2.5 pr-12
                 leading-relaxed overflow-hidden
                 bg-[#dbeafe] border border-blue-300 shadow-sm
                 text-blue-900 placeholder:text-blue-800/60
                 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500
                 transition-all"
        ></textarea>

        <!-- Send Button (inside input) -->
        <button
          type="button"
          @click="sendMessage"
          class="absolute right-2 bottom-2 p-2 rounded-xl transition-all duration-200 flex items-center justify-center"
          :class="message.trim() ? 'text-blue-600 hover:bg-blue-50' : 'text-red-400 cursor-not-allowed'"
          :disabled="!message.trim()"
        >
          <PaperAirplaneIcon class="w-5 h-5" />
        </button>
      </div>

      <!-- Hidden File Input -->
      <input
        ref="fileInput"
        type="file"
        accept="image/*,.pdf,.doc,.docx,.txt"
        class="hidden"
        @change="handleFileUpload"
      />

      <!-- Paper Clip (Attach) -->
      <button
        type="button"
        class="p-2 rounded-xl transition-all duration-200 hover:bg-gray-100 flex-shrink-0"
        @click="triggerFilePicker"
        :style="{ color: 'var(--text-secondary)' }"
      >
        <PaperClipIcon class="w-5 h-5" />
      </button>
    </div>

    <!-- Attached File Preview -->
    <div
      v-if="attachedFile"
      class="absolute bottom-20 left-1/2 transform -translate-x-1/2 px-4 py-2 rounded-xl flex items-center gap-3 text-sm shadow-lg z-10"
      :style="{ background: 'var(--card-bg)', color: 'var(--text-primary)', border: '1px solid var(--border-default)', boxShadow: '0 4px 12px rgba(0,0,0,0.15)' }"
    >
      <PaperClipIcon class="w-4 h-4 text-blue-500" />
      <span class="truncate max-w-xs">{{ attachedFile.name }}</span>
      <button @click="removeAttachment" class="text-red-500 hover:text-red-700 font-semibold ml-2">
        ×
      </button>
    </div>
  </footer>
</template>

<script setup>
import { ref, nextTick } from "vue";
import { PaperClipIcon, PaperAirplaneIcon } from "@heroicons/vue/24/outline";

const message = ref("");
const attachedFile = ref(null);
const fileInput = ref(null);
const textareaRef = ref(null);

const triggerFilePicker = () => fileInput.value?.click();

const handleFileUpload = (event) => {
  attachedFile.value = event.target.files[0];
};

const removeAttachment = () => {
  attachedFile.value = null;
  if (fileInput.value) fileInput.value.value = "";
};

const emit = defineEmits(["send"]);

const sendMessage = () => {
  if (!message.value.trim()) return;
  emit("send", { message: message.value, file: attachedFile.value });
  message.value = "";
  attachedFile.value = null;
  nextTick(() => autoResize());
};

// Auto-resize logic
const autoResize = () => {
  const el = textareaRef.value;
  if (!el) return;
  el.style.height = "auto";
  el.style.height = el.scrollHeight + "px";
};
</script>

<style scoped>
footer {
  height: auto;
  min-height: 56px;
}

/* Limit textarea growth & keep it smooth */
textarea {
  max-height: 200px;
  line-height: 1.5;
}

/* Custom scrollbar for textarea */
textarea::-webkit-scrollbar {
  width: 4px;
}

textarea::-webkit-scrollbar-track {
  background: transparent;
}

textarea::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 2px;
}

textarea::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.3);
}

/* Smooth transitions */
button {
  transition: all 0.2s ease;
}
</style>
