<script setup>
import TASidebar from '@/components/layout/TaLayout/TASidebar.vue'
import TaHeaderBar from '@/components/layout/TaLayout/TaHeaderBar.vue'
import { CheckCircleIcon, UsersIcon, ClockIcon, ArrowTrendingUpIcon, PlusCircleIcon, ArrowRightOnRectangleIcon, ClipboardDocumentListIcon, ChatBubbleLeftRightIcon } from "@heroicons/vue/24/outline"

const metrics = [
  {
    label: 'Doubts Resolved',
    value: 24,
    sub: 'This week',
    icon: CheckCircleIcon,
    iconColor: 'text-green-500'
  },
  {
    label: 'Students Helped',
    value: 18,
    sub: 'This week',
    icon: UsersIcon,
    iconColor: 'text-blue-500'
  },
  {
    label: 'Avg Response Time',
    value: '45 mins',
    sub: 'Improved by 20%',
    icon: ClockIcon,
    iconColor: 'text-orange-500'
  },
  {
    label: 'Satisfaction Rate',
    value: '92%',
    sub: 'From student feedback',
    icon: ArrowTrendingUpIcon,
    iconColor: 'text-purple-500'
  }
]
const assignedCourses = [
  { name: 'Software Engineering', code: 'BSCS3001', students: 45 },
  { name: 'Machine Learning', code: 'BSCS3003', students: 38 }
]
const doubts = [
  { title: 'Help with Milestone 3 design patterns', student: 'John Student', code: 'BSCS3001', time: '30 mins ago', status: 'pending' },
  { title: 'Neural network convergence issue', student: 'Jane Doe', code: 'BSCS3003', time: '2 hours ago', status: 'answered' },
  { title: 'Database normalization clarification', student: 'Mike Smith', code: 'BSCS3001', time: '5 hours ago', status: 'pending' }
]
const escalations = [
  { title: 'Grade re-evaluation request', student: 'John Student', role: 'Instructor', date: '2024-10-30' },
  { title: 'Extension request for medical reasons', student: 'Sarah Lee', role: 'Admin', date: '2024-10-29' }
]
const announcements = [
  { headline: 'New Feature: AI Summarizer', description: 'The new doubt summarizer is now live! Explore its capabilities.' },
  { headline: 'System Maintenance', description: 'Scheduled maintenance on 15th May, 10 PM - 12 AM IST.' },
  { headline: 'Resource HUB Updates', description: "Latest academic papers for 'Advanced AI' course added." }
]


</script>

<template>
  <div class="flex min-h-screen bg-[#f8fafc]">
    <TASidebar />
    <main class="flex-1 ml-[250px]">
      <TaHeaderBar searchPlaceholder="Search dashboard, queries, resources" />

      <!-- Welcome Banner (flat style) -->
      <div class="px-8 pt-8">
        <div class="rounded-2xl w-full py-7 px-7 mb-7 shadow flex flex-col gap-1"
          style="background: linear-gradient(90deg, #9340ff 0%, #5e61ea 100%);">
          <h1 class="text-white font-black text-2xl md:text-3xl mb-2 flex items-center">
            Welcome back, TA! <span class="ml-3 text-2xl"></span>
          </h1>
          <p class="text-white text-lg">Here's your teaching activity overview</p>
        </div>
      </div>

      <div class="px-8 flex flex-col lg:flex-row gap-8">
        <!-- Main Section -->
        <div class="flex-1 flex flex-col gap-8  ">
          <!-- Professional Metric Cards Row -->
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-7 mb-2">
            <div v-for="card in metrics" :key="card.label"
              class="rounded-xl p-6 bg-white shadow-lg border border-gray-100 transition-transform hover:scale-105 hover:shadow-xl flex flex-col gap-2">
              <div class="flex items-center gap-3 mb-1">
                <component :is="card.icon" :class="[card.iconColor, 'h-6 w-6']" />
                <span class="font-semibold text-gray-700 text-[1rem]">{{ card.label }}</span>
              </div>
              <div class="flex items-end justify-between mt-3">
                <span class="text-3xl font-black text-slate-900">{{ card.value }}</span>
                <span class="ml-2 text-sm font-semibold text-gray-400">{{ card.sub }}</span>
              </div>
            </div>
          </div>

          <!-- Courses -->
          <div class="bg-white rounded-xl shadow p-6 mb-6">
            <div class="font-black text-lg mb-4 text-black">Assigned Courses</div>
            <div class="flex gap-8">
              <div v-for="course in assignedCourses" :key="course.code"
                class="flex-1 py-7 px-7 rounded-xl bg-[#f3f6fa] border border-gray-200 shadow-lg hover:shadow-xl transition group">
                <span class="font-bold text-blue-900 text-lg block mb-1">{{ course.name }}</span>
                <span class="text-sm text-gray-400 block mb-3">{{ course.code }}</span>
                <span class="block text-2xl font-black text-slate-900">{{ course.students }}</span>
                <span class="block text-base text-gray-700">Students</span>

              </div>
            </div>
          </div>

          <!-- Queries & Escalations -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="bg-white rounded-xl shadow p-6">
              <div class="font-black text-lg mb-3 text-black">Recent Student Doubts</div>
              <div v-for="dubt in doubts" :key="dubt.title" class="mb-4 pb-4 border-b last:border-b-0 last:pb-0">
                <div class="font-semibold text-blue-700">{{ dubt.title }}</div>
                <div class="text-xs text-gray-400">{{ dubt.student }} • {{ dubt.code }} • {{ dubt.time }}</div>
                <div class="flex items-center gap-2 mt-1">
                  <span :class="dubt.status === 'pending'
                    ? 'bg-orange-100 text-orange-600'
                    : 'bg-green-100 text-green-600'" class="px-3 py-0.5 rounded-full text-xs">{{ dubt.status
                    }}</span>
                  <button
                    class="ml-2 text-xs text-blue-700 hover:text-blue-900 font-semibold hover:underline transition">Respond</button>
                </div>
              </div>
            </div>
            <div class="bg-white rounded-xl shadow p-6">
              <div class="font-black text-lg mb-3 text-black">Escalated Queries</div>
              <div v-for="item in escalations" :key="item.title" class="mb-4 pb-4 border-b last:border-b-0 last:pb-0">
                <div class="font-semibold text-[#962424]">{{ item.title }}</div>
                <div class="text-xs text-gray-400">{{ item.student }} • Escalated to: {{ item.role }}</div>
                <div class="text-xs text-gray-400 mt-1">{{ item.date }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Sidebar -->
        <aside class="w-full lg:w-80 flex flex-col gap-6">
          <div class="bg-white rounded-xl shadow p-5">
            <div class="font-black mb-4 text-lg text-black">Quick Actions</div>
            <button
              class="flex items-center gap-2 w-full px-4 py-3 mb-2 rounded-lg bg-[#2563eb] text-white font-semibold shadow hover:bg-blue-600 hover:scale-105 transition">
              <PlusCircleIcon class="w-5 h-5" />
              Add New Resource
            </button>

            <button
              class="flex items-center gap-2 w-full px-4 py-3 mb-2 rounded-lg text-blue-700 bg-blue-50 hover:bg-blue-100 shadow-sm font-semibold transition hover:scale-105">
              <ClipboardDocumentListIcon class="w-5 h-5" /> Summarize Doubts
            </button>
            <button
              class="flex items-center gap-2 w-full px-4 py-3 mb-2 rounded-lg text-blue-700 bg-blue-50 hover:bg-blue-100 shadow-sm font-semibold transition hover:scale-105">
              <ChatBubbleLeftRightIcon class="w-5 h-5" /> View All Queries
            </button>
            <button
              class="flex items-center gap-2 w-full px-4 py-3 rounded-lg text-blue-700 bg-blue-50 hover:bg-blue-100 shadow-sm font-semibold transition hover:scale-105">
              <ArrowRightOnRectangleIcon class="w-5 h-5" /> Start Onboarding Session
            </button>
          </div>
          <div class="bg-white rounded-xl shadow p-5">
            <div class="font-black mb-3 text-lg text-black">Recent Announcements</div>
            <div v-for="ann in announcements" :key="ann.headline" class="mb-2">
              <div class="font-semibold text-blue-800">{{ ann.headline }}</div>
              <div class="text-xs text-gray-500">{{ ann.description }}</div>
            </div>
          </div>
        </aside>
      </div>
    </main>
  </div>
</template>
