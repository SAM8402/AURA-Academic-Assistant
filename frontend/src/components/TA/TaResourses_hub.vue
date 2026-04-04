<template>
  <div class="flex">
    <!-- Sidebar -->
    <TASidebar class="fixed top-0 left-0 h-screen w-[250px]" />

    <!-- Main Content -->
    <main class="flex-1 flex flex-col min-h-screen ml-[250px] bg-gray-50">
      <!-- Header -->
      <TaHeaderBar />

      <!-- Page Content -->
      <div class="p-8 bg-gray-50 flex-1 overflow-y-auto">
        <!-- Page Title -->
        <h1 class="text-2xl font-semibold mb-6 text-[#0d1b2a]">Resource Hub</h1>

        <!-- Filter Buttons -->
        <div class="flex flex-wrap gap-3 mb-6">
          <button
            v-for="tag in mainTags"
            :key="tag"
            @click="filterTag = tag"
            :class="[
              'px-4 py-1 rounded-full border text-sm transition',
              filterTag === tag
                ? 'bg-[#0d1b2a] text-white border-[#0d1b2a]'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-100'
            ]"
          >
            {{ tag }}
          </button>
        </div>

        <!-- Search and Actions -->
        <div class="flex justify-between items-center mb-6 flex-wrap gap-3">
          <input
            type="text"
            v-model="searchQuery"
            placeholder="Search resources..."
            class="border border-gray-300 rounded-lg px-4 py-2 w-full sm:w-80 focus:outline-none focus:ring-2 focus:ring-[#0d1b2a]"
          />
          <div class="flex gap-3">
            <button class="bg-[#0d1b2a] text-white px-4 py-2 rounded-lg hover:bg-[#1b263b] transition">
              Add New Resource
            </button>
            <button class="border border-gray-300 px-4 py-2 rounded-lg hover:bg-gray-100">
              Request Resource
            </button>
          </div>
        </div>

        <!-- Resource Grid -->
        <div class="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          <div
            v-for="res in filteredResources"
            :key="res.title"
            class="bg-white rounded-2xl shadow-sm hover:shadow-md transition overflow-hidden border border-gray-200"
          >
            <img
              :src="res.image"
              alt="resource"
              class="h-40 w-full object-cover"
            />
            <div class="p-4">
              <span class="inline-block text-xs bg-blue-100 text-blue-600 px-2 py-1 rounded-full mb-2">
                {{ res.category }}
              </span>
              <h2 class="text-lg font-semibold mb-1 text-[#0d1b2a]">
                {{ res.title }}
              </h2>
              <p class="text-sm text-gray-600 mb-3">
                {{ res.description }}
              </p>
              <button class="text-[#0d1b2a] text-sm font-medium hover:underline">
                View Details
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import TASidebar from '@/components/layout/TaLayout/TASidebar.vue'
import TaHeaderBar from '@/components/layout/TaLayout/TaHeaderBar.vue'


const mainTags = [
  "All",
  "Mathematics",
  "Programming",
  "Soft Skills",
  "AI/ML",
  "Academic Writing",
  "Ethics",
  "Productivity",
  "Academic Tools",
];

const filterTag = ref("All");
const searchQuery = ref("");

const resources = ref([
  {
    title: "Introduction to Calculus",
    category: "Mathematics",
    description:
      "A comprehensive guide covering limits, derivatives, and integrals.",
    image:
      "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?auto=format&fit=crop&w=800&q=60",
  },
  {
    title: "Advanced Python for Data Science",
    category: "Programming",
    description:
      "Dive deep into Python’s data science ecosystem. Covers NumPy, pandas, and more.",
    image:
      "https://images.unsplash.com/photo-1519389950473-47ba0277781c?auto=format&fit=crop&w=800&q=60",
  },
  {
    title: "Effective Presentation Skills",
    category: "Soft Skills",
    description:
      "Learn how to deliver impactful academic presentations. Includes examples.",
    image:
      "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=800&q=60",
  },
  {
    title: "Research Paper Writing Workshop",
    category: "Academic Writing",
    description:
      "A step-by-step workshop on structuring, writing, and formatting research papers.",
    image:
      "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQkJYlua6ae6ulyv8kVUc-1GMG2kDIGDxyeHg&s",
  },
  {
    title: "Online Collaboration",
    category: "Productivity",
    description:
      "Explore various digital tools to enhance teamwork and communication.",
    image:
      "https://images.unsplash.com/photo-1521790797524-b2497295b8a0?auto=format&fit=crop&w=800&q=60",
  },
  {
    title: "Understanding Academic Ethics",
    category: "Ethics",
    description:
      "A crucial guide for IAs on upholding and promoting academic integrity.",
    image:
      "https://cdn.slidesharecdn.com/ss_thumbnails/ethicsinacademics-190811104515-thumbnail.jpg?width=640&height=640&fit=bounds",
  },
  {
    title: "Foundations of Machine Learning",
    category: "AI/ML",
    description: "An introductory video series on machine learning concepts.",
    image:
      "https://images.unsplash.com/photo-1555949963-aa79dcee981c?auto=format&fit=crop&w=800&q=60",
  },
  {
    title: "LaTeX for Academics",
    category: "Academic Tools",
    description:
      "Master LaTeX for typesetting high-quality academic documents and research papers.",
    image:
      "https://upload.wikimedia.org/wikipedia/commons/thumb/9/92/LaTeX_logo.svg/1200px-LaTeX_logo.svg.png",
  },
]);

const filteredResources = computed(() =>
  resources.value.filter(
    (r) =>
      (filterTag.value === "All" || r.category === filterTag.value) &&
      r.title.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
);
</script>

<style scoped>
/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 8px;
}
::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>
