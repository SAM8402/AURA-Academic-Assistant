<script setup>
import { ref } from "vue";
import TASidebar from '@/components/layout/TaLayout/TASidebar.vue'
import TaHeaderBar from '@/components/layout/TaLayout/TaHeaderBar.vue';

const filters = ref({
  search: "",
  priority: "",
  topic: "",
  status: "",
  escalation: "",
});

const queries = ref([
  { id: "QRT001", topic: "Course Content: Module 3", student: "Priya Sharma", priority: "High", status: "Open", updated: "2024-07-28 10:30 AM" },
  { id: "QRT002", topic: "Assignment 2 Submission", student: "Rahul Singh", priority: "Medium", status: "Pending", updated: "2024-07-27 04:15 PM" },
  { id: "QRT003", topic: "Lab Session Query", student: "Anjali Gupta", priority: "Low", status: "Resolved", updated: "2024-07-27 11:00 AM" },
  { id: "QRT004", topic: "Exam Preparation Tips", student: "Amit Kumar", priority: "Medium", status: "Open", updated: "2024-07-26 09:45 AM" },
  { id: "QRT005", topic: "Grading Discrepancy", student: "Sneha Reddy", priority: "High", status: "Escalated", updated: "2024-07-26 02:00 PM" },
  { id: "QRT006", topic: "Project Proposal Feedback", student: "Vikram Patel", priority: "Medium", status: "Pending", updated: "2024-07-25 01:00 PM" },
  { id: "QRT007", topic: "Doubt on Theorem X", student: "Neha Verma", priority: "Medium", status: "Open", updated: "2024-07-28 09:00 AM" },
]);
</script>

<template>

    <!-- <TASidebar /> -->
    <div class="flex">
      <TASidebar class="fixed top-0 left-0 h-screen w-[250px]" />
      <main class="flex-1 flex flex-col min-h-screen ml-[250px] bg-gray-50">

      <TaHeaderBar searchPlaceholder="Search queries, students, topics" />

      <!-- MAIN DASHBOARD AREA BELOW HEADER -->
      <div class="flex flex-1 gap-8 px-8 py-7 ">
        <!-- Main dashboard (filters and table) -->
        <div class="flex-1 flex flex-col gap-6">
          <h1 class="text-2xl font-extrabold mb-2 text-black">Query Tracker</h1>
          <div class="bg-white rounded-xl shadow p-5 mb-2">
            <form class="flex flex-wrap gap-3 items-center">
              <input v-model="filters.search" type="search" placeholder="🔍 Search" class="px-3 py-2 border rounded-md text-sm bg-blue-50 focus:bg-white" />
              <select v-model="filters.priority" class="px-3 py-2 border rounded-md text-sm bg-blue-50 focus:bg-white">
                <option value="">Priority</option>
                <option>High</option>
                <option>Medium</option>
                <option>Low</option>
              </select>
              <select v-model="filters.topic" class="px-3 py-2 border rounded-md text-sm bg-blue-50 focus:bg-white">
                <option value="">Topic</option>
                <option>Module 3</option>
                <option>Assignment</option>
                <option>Lab</option>
              </select>
              <select v-model="filters.status" class="px-3 py-2 border rounded-md text-sm bg-blue-50 focus:bg-white">
                <option value="">Status</option>
                <option>Open</option>
                <option>Pending</option>
                <option>Resolved</option>
                <option>Escalated</option>
              </select>
              <select v-model="filters.escalation" class="px-3 py-2 border rounded-md text-sm bg-blue-50 focus:bg-white">
                <option value="">Escalation</option>
                <option>Yes</option>
                <option>No</option>
              </select>
              <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded-md text-sm mr-2 font-semibold hover:bg-blue-800">Apply Filters</button>
              <button type="button" class="px-4 py-2 bg-blue-50 text-blue-700 rounded-md text-sm hover:bg-blue-100">Clear Filters</button>
            </form>
          </div>
          <div class="bg-white rounded-xl shadow p-5">
            <div class="flex items-center justify-between mb-3">
              <h2 class="font-bold text-lg text-black">All Queries</h2>
              <button class="py-2 px-4 bg-blue-50 text-blue-700 rounded hover:bg-blue-100 text-xs font-medium border">Export Queries</button>
              <button class="py-2 px-4 bg-blue-50 text-blue-700 rounded hover:bg-blue-100 text-xs font-medium border">Summaries Queries</button>

            </div>
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b">
                  <th class="p-2 text-left font-semibold text-gray-400">Query ID</th>
                  <th class="p-2 text-left font-semibold text-gray-400">Topic</th>
                  <th class="p-2 text-left font-semibold text-gray-400">Student</th>
                  <th class="p-2 text-left font-semibold text-gray-400">Priority</th>
                  <th class="p-2 text-left font-semibold text-gray-400">Status</th>
                  <th class="p-2 text-left font-semibold text-gray-400">Last Updated</th>
                  <th class="p-2"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="query in queries" :key="query.id" class="border-b hover:bg-blue-50">
                  <td class="p-2 font-mono">{{ query.id }}</td>
                  <td class="p-2">{{ query.topic }}</td>
                  <td class="p-2">{{ query.student }}</td>
                  <td class="p-2">
                    <span :class="{
                      'bg-red-100 text-red-700': query.priority === 'High',
                      'bg-yellow-100 text-yellow-700': query.priority === 'Medium',
                      'bg-green-100 text-green-700': query.priority === 'Low'
                    }" class="px-2 py-1 rounded font-medium text-xs">{{ query.priority }}</span>
                  </td>
                  <td class="p-2">
                    <span :class="{
                      'bg-blue-100 text-blue-700': query.status === 'Open',
                      'bg-gray-100 text-gray-700': query.status === 'Pending',
                      'bg-green-100 text-green-700': query.status === 'Resolved',
                      'bg-red-100 text-red-700': query.status === 'Escalated'
                    }" class="px-2 py-1 rounded font-medium text-xs">{{ query.status }}</span>
                  </td>
                  <td class="p-2">{{ query.updated }}</td>
                  <td class="p-2">
                    <button class="hover:bg-blue-50 rounded-full p-1">
                      <span class="font-bold text-xl text-gray-400">…</span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
            <div class="flex justify-between items-center text-xs mt-2 text-gray-500">
              <div>Showing 1-7 of 7 queries</div>
              <div>
                <button class="mx-1 px-2 py-1 rounded bg-blue-50 text-blue-700 hover:bg-blue-100 border">Previous</button>
                <button class="mx-1 px-2 py-1 rounded bg-blue-50 text-blue-700 hover:bg-blue-100 border">1</button>
                <button class="mx-1 px-2 py-1 rounded bg-blue-50 text-blue-700 hover:bg-blue-100 border">2</button>
                <button class="mx-1 px-2 py-1 rounded bg-blue-50 text-blue-700 hover:bg-blue-100 border">3</button>
                <button class="mx-1 px-2 py-1 rounded bg-blue-50 text-blue-700 hover:bg-blue-100 border">Next</button>
              </div>
            </div>
          </div>
        </div>
        <!-- Side Panel at same row (vertically starts from Query Tracker, not header) -->
        <div class="flex flex-col gap-7 w-[320px]">
          <div class="bg-white rounded-xl shadow p-5">
            <div class="font-bold mb-4 text-base text-black">Quick Actions</div>
            <button class="w-full mb-2 px-4 py-3 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-800">Create New Query</button>
            <button class="w-full mb-2 px-4 py-3 rounded-lg bg-blue-50 text-blue-700 font-medium border hover:bg-blue-100">Bulk Update Status</button>
            <button class="w-full mb-2 px-4 py-3 rounded-lg bg-blue-50 text-blue-700 font-medium border hover:bg-blue-100">Export Filtered List</button>
            <button class="w-full mb-2 px-4 py-3 rounded-lg bg-blue-50 text-blue-700 font-medium border hover:bg-blue-100">View Query Analytics</button>
          </div>
          <div class="bg-white rounded-xl shadow p-5">
            <div class="font-bold mb-4 text-base text-black">Query Statistics</div>
            <div class="flex flex-col gap-2">
              <div class="flex justify-between items-center">
                <span class="text-gray-600 text-sm">Open Queries</span>
                <span class="bg-blue-50 text-blue-800 p-2 rounded">{{ queries.filter(q=>q.status==="Open").length }}</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-gray-600 text-sm">Resolved Today</span>
                <span class="bg-blue-50 text-blue-800 p-2 rounded">{{ queries.filter(q=>q.status==="Resolved").length }}</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-gray-600 text-sm">High Priority</span>
                <span class="bg-red-100 text-red-700 p-2 rounded">{{ queries.filter(q=>q.priority==="High").length }}</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-gray-600 text-sm">Escalated</span>
                <span class="bg-red-100 text-red-700 p-2 rounded">{{ queries.filter(q=>q.status==="Escalated").length }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
    </div>
</template>
