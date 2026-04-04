<template>
  <div class="flex min-h-screen bg-gray-50">
    <TASidebar class="fixed top-0 left-0 h-screen w-[250px]" />

    <main class="flex-1 flex flex-col min-h-screen ml-[250px] bg-gray-50">
      <header class="bg-white shadow-sm px-8 py-5 border-b border-gray-200">
        <h1 class="text-2xl font-extrabold text-gray-900">AI Onboarding Mentor</h1>
        <p class="text-sm text-gray-600 mt-1">
          Your personalized guide trained on institutional best practices, senior TA experiences, and faculty wisdom
        </p>
      </header>

      <div class="p-6 space-y-6">
        <!-- Tab Navigation -->
        <div class="bg-white border border-gray-200 rounded-xl p-2">
          <div class="flex space-x-2">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              @click="activeTab = tab.id"
              :class="[
                'flex-1 px-4 py-3 rounded-lg font-medium transition-colors text-sm',
                activeTab === tab.id
                  ? (themeStore.currentTheme === 'dark'
                      ? 'bg-blue-600 text-white'
                      : 'bg-blue-50 text-black border border-blue-600')
                  : (themeStore.currentTheme === 'dark'
                      ? 'text-gray-300 hover:bg-gray-800'
                      : 'text-gray-700 hover:bg-gray-100')
              ]"
            >
              {{ tab.label }}
            </button>
          </div>
        </div>

        <!-- AI Mentor Chat Tab (source of style) -->
        <div v-if="activeTab === 'mentor'" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div class="lg:col-span-2">
            <div class="bg-white border border-gray-200 rounded-xl flex flex-col h-[600px]">
              <div class="p-4 border-b border-gray-200 bg-white">
                <h3 class="font-bold text-gray-900">Conversational AI Mentor</h3>
                <p class="text-sm text-gray-600">Ask anything about your TA role, backed by real experiences</p>
              </div>

              <div class="flex-1 overflow-y-auto p-4 space-y-4">
                <div
                  v-for="(msg, i) in messages"
                  :key="i"
                  :class="['flex', msg.role === 'user' ? 'justify-end' : 'justify-start']"
                >
                  <div
                    :class="[
                      'max-w-md px-4 py-3 rounded-lg',
                      msg.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-900 border border-gray-200'
                    ]"
                  >
                    <div v-if="msg.role === 'ai'" class="flex items-center mb-2">
                      <span class="font-bold text-sm">AI Mentor</span>
                    </div>
                    <p class="text-sm whitespace-pre-wrap">{{ msg.text }}</p>
                  </div>
                </div>
                <div v-if="isTyping" class="flex justify-start">
                  <div class="bg-gray-100 px-4 py-3 rounded-lg border border-gray-200">
                    <p class="text-sm text-gray-600">AI is typing...</p>
                  </div>
                </div>
              </div>

              <div class="p-4 border-t border-gray-200 bg-gray-50">
                <div class="flex space-x-2">
                  <input
                    v-model="userInput"
                    type="text"
                    placeholder="Ask about TA responsibilities, best practices, or common challenges..."
                    class="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                    @keypress.enter="sendMessage"
                  />
                  <button
                    @click="sendMessage"
                    class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
                  >
                    <PaperAirplaneIcon class="w-5 h-5" />
                  </button>
                </div>
                <p class="text-xs text-gray-500 mt-2">Tip: Be specific with your questions for better guidance</p>
              </div>
            </div>
          </div>

          <div class="space-y-4">
            <div class="bg-white rounded-xl p-4">
              <h4 class="font-bold text-gray-900 mb-3">Suggested Questions</h4>
              <div class="space-y-2">
                <button
                  v-for="(question, idx) in suggestedQuestions"
                  :key="idx"
                  @click="userInput = question"
                  class="w-full text-left px-3 py-2 bg-white rounded-lg hover:bg-blue-100 text-sm text-gray-700 border border-gray-200"
                >
                  {{ question }}
                </button>
              </div>
            </div>

            <div class="bg-white rounded-xl p-4">
              <h4 class="font-bold text-gray-900 mb-2">Your Progress</h4>
              <div class="space-y-2 text-sm">
                <div class="flex justify-between">
                  <span class="text-gray-600">Topics Explored</span>
                  <span class="font-bold">4/10</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2">
                  <div class="bg-green-600 h-2 rounded-full" style="width: 40%"></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Connect with TAs/Faculty Tab – AI Bubble Style -->
        <div v-if="activeTab === 'connect'" class="space-y-6">
          <!-- [Same as previous – all bg-gray-100 / border-gray-200] -->
          <!-- Quick Actions -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="bg-gray-100 text-gray-900 border border-gray-200 rounded-xl p-6 cursor-pointer hover:bg-gray-200 transition-colors">
              <h3 class="font-bold text-lg mb-1">Start a Chat</h3>
              <p class="text-sm opacity-90">Message mentors directly</p>
            </div>
            <div class="bg-gray-100 text-gray-900 border border-gray-200 rounded-xl p-6 cursor-pointer hover:bg-gray-200 transition-colors">
              <h3 class="font-bold text-lg mb-1">Book Office Hours</h3>
              <p class="text-sm opacity-90">Schedule 1-on-1 sessions</p>
            </div>
            <div class="bg-gray-100 text-gray-900 border border-gray-200 rounded-xl p-6 cursor-pointer hover:bg-gray-200 transition-colors">
              <h3 class="font-bold text-lg mb-1">Find a Mentor</h3>
              <p class="text-sm opacity-90">Get paired with a guide</p>
            </div>
          </div>

          <!-- Available Mentors -->
          <div class="bg-white border border-gray-200 rounded-xl p-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-xl font-bold text-gray-900">Available Mentors</h3>
              <div class="flex items-center space-x-2">
                <select class="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-400">
                  <option>All Expertise</option>
                  <option>Design Patterns</option>
                  <option>Machine Learning</option>
                  <option>Databases</option>
                  <option>Web Development</option>
                </select>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div
                v-for="mentor in availableMentors"
                :key="mentor.id"
                class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div class="flex items-start justify-between mb-3">
                  <div class="flex items-start">
                    <div class="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mr-3 border border-gray-200">
                      <span class="font-bold text-gray-900">{{ mentor.avatar }}</span>
                    </div>
                    <div>
                      <h4 class="font-bold text-gray-900">{{ mentor.name }}</h4>
                      <p class="text-sm text-gray-600">{{ mentor.role }} • {{ mentor.experience }}</p>
                      <div class="flex items-center mt-1">
                        <span class="text-yellow-500 text-sm">★ {{ mentor.rating }}</span>
                        <span class="text-gray-400 text-xs ml-2">• {{ mentor.responses }} responses</span>
                      </div>
                    </div>
                  </div>
                  <span
                    :class="[
                      'px-2 py-1 rounded text-xs font-medium',
                      mentor.availability === 'Available'
                        ? 'bg-white text-green-600 border border-green-600'
                        : 'bg-white text-orange-600 border border-orange-600'
                    ]"
                  >
                    {{ mentor.availability }}
                  </span>
                </div>

                <div class="mb-3">
                  <p class="text-xs font-medium text-gray-700 mb-2">Expertise:</p>
                  <div class="flex flex-wrap gap-1">
                    <span
                      v-for="skill in mentor.expertise"
                      :key="skill"
                      class="px-2 py-1 bg-gray-100 text-gray-900 rounded text-xs border border-gray-200"
                    >
                      {{ skill }}
                    </span>
                  </div>
                </div>

                <div class="flex space-x-2">
                  <button class="flex-1 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">
                    Chat Now
                  </button>
                  <button class="flex-1 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">
                    Book Slot
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Discussion Forums -->
          <div class="bg-white border border-gray-200 rounded-xl p-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-xl font-bold text-gray-900">Active Discussions</h3>
              <button class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">
                + Start New Topic
              </button>
            </div>

            <div class="space-y-3">
              <div
                v-for="topic in discussionTopics"
                :key="topic.id"
                class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
              >
                <div class="flex items-start justify-between">
                  <div class="flex-1">
                    <div class="flex items-center mb-2">
                      <span class="px-2 py-1 bg-gray-100 text-gray-900 rounded text-xs font-medium mr-2 border border-gray-200">
                        {{ topic.category }}
                      </span>
                      <span class="text-xs text-gray-500">{{ topic.lastActive }}</span>
                    </div>
                    <h4 class="font-bold text-gray-900 mb-1">{{ topic.title }}</h4>
                    <p class="text-sm text-gray-600">
                      Started by <span class="font-medium">{{ topic.author }}</span> •
                      <span class="font-medium">{{ topic.replies }} replies</span>
                    </p>
                  </div>
                  <button class="ml-4 text-gray-600 hover:text-gray-700 text-xl">→</button>
                </div>
              </div>
            </div>
          </div>

          <!-- Upcoming Office Hours -->
          <div class="bg-white border border-gray-200 rounded-xl p-6">
            <h3 class="text-xl font-bold text-gray-900 mb-4">Upcoming Office Hours</h3>
            <div class="space-y-3">
              <div
                v-for="slot in upcomingOfficeHours"
                :key="slot.id"
                class="border border-gray-200 rounded-lg p-4 flex items-center justify-between"
              >
                <div class="flex items-start">
                  <div class="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center mr-3 border border-gray-200">
                    <ClockIcon class="w-5 h-5 text-gray-900" />
                  </div>
                  <div>
                    <h4 class="font-bold text-gray-900">{{ slot.mentor }}</h4>
                    <p class="text-sm text-gray-600">{{ slot.date }} • {{ slot.time }}</p>
                    <p class="text-xs text-gray-500 mt-1">{{ slot.location }}</p>
                  </div>
                </div>
                <div class="text-right">
                  <p class="text-sm font-medium text-gray-900 mb-2">{{ slot.spotsLeft }} spots left</p>
                  <button class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">
                    Book Now
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Community Chat -->
          <div class="bg-white border border-gray-200 rounded-xl p-6">
            <h3 class="text-xl font-bold text-gray-900 mb-4">Ask the Community</h3>
            <div class="mb-4">
              <textarea
                v-model="communityQuestion"
                placeholder="Have a question? Ask the TA community..."
                class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-400"
                rows="3"
              ></textarea>
              <div class="flex justify-between items-center mt-2">
                <div class="flex space-x-2">
                  <select class="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-400">
                    <option>General Question</option>
                    <option>Teaching Methods</option>
                    <option>Student Management</option>
                    <option>Technical Help</option>
                    <option>Career Advice</option>
                  </select>
                </div>
                <button class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">
                  Post Question
                </button>
              </div>
            </div>
            <p class="text-xs text-gray-500">
              Your question will be visible to all TAs and faculty mentors. Expect responses within 24 hours.
            </p>
          </div>

          <!-- Mentorship Program -->
          <div class="bg-white rounded-xl p-6">
            <div class="flex items-start">
              <div class="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center mr-4 border border-gray-200">
                <span class="text-gray-900 font-bold text-xl">M</span>
              </div>
              <div class="flex-1">
                <h3 class="text-xl font-bold text-gray-900 mb-2">Long-term Mentorship Program</h3>
                <p class="text-gray-700 mb-4">
                  Get paired with an experienced TA or faculty member for ongoing guidance throughout your TA journey.
                  Mentors provide personalized advice, career guidance, and support for professional development.
                </p>
                <div class="flex items-center space-x-4">
                  <button class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">
                    Request a Mentor
                  </button>
                  <button class="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 font-medium">
                    Learn More
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Quick Start Guide Tab (unchanged) -->
        <div v-if="activeTab === 'quickstart'" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="topic in quickStartTopics"
            :key="topic.id"
            class="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-md transition-shadow"
          >
            <h4 class="font-bold text-gray-900 mb-2">{{ topic.title }}</h4>
            <p class="text-sm text-gray-600 mb-4">{{ topic.description }}</p>
            <div class="space-y-2">
              <p class="text-xs font-medium text-gray-700">Common Questions:</p>
              <button
                v-for="(q, idx) in topic.questions"
                :key="idx"
                @click="activeTab = 'mentor'; userInput = q"
                class="w-full text-left text-xs text-blue-600 hover:text-blue-700 hover:underline"
              >
                • {{ q }}
              </button>
            </div>
          </div>
        </div>

        <!-- Senior TA Tips Tab – NOW USING AI BUBBLE STYLE -->
        <div v-if="activeTab === 'tips'" class="space-y-4">
          <div class="bg-white rounded-xl p-4">
            <h3 class="text-xl font-bold text-gray-900 mb-2">Wisdom from Experienced TAs</h3>
            <p class="text-gray-600">Real advice from TAs who have successfully navigated the challenges you'll face</p>
          </div>

          <div
            v-for="tip in seniorTATips"
            :key="tip.id"
            class="bg-gray-100 border border-gray-200 rounded-xl p-6 hover:shadow-sm transition-shadow"
          >
            <div class="flex items-start mb-4">
              <!-- Avatar -->
              <div class="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mr-4 border border-gray-200">
                <span class="text-gray-900 font-bold text-lg">TA</span>
              </div>
              <div class="flex-1">
                <p class="font-bold text-gray-900">{{ tip.author }}</p>
                <!-- Category tag -->
                <span class="px-2 py-1 bg-gray-100 text-gray-900 rounded text-xs font-medium border border-gray-200">
                  {{ tip.category }}
                </span>
              </div>
            </div>
            <!-- Quote box -->
            <div class="bg-gray-50 rounded-lg p-4 border-l-4 border-gray-300">
              <p class="text-gray-700 italic">"{{ tip.tip }}"</p>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useThemeStore } from '@/stores/theme'
import TASidebar from '@/components/layout/TaLayout/TASidebar.vue'
import { PaperAirplaneIcon, ClockIcon } from '@heroicons/vue/24/outline'

const activeTab = ref('mentor')
const communityQuestion = ref('')

// Theme store for light/dark awareness
const themeStore = useThemeStore()

const tabs = [
  { id: 'mentor', label: 'AI Mentor Chat' },
  { id: 'connect', label: 'Connect with TAs/Faculty' },
  { id: 'quickstart', label: 'Quick Start Guide' },
  { id: 'tips', label: 'Senior TA Tips' }
]

const messages = ref([
  {
    role: 'ai',
    text: "Hello! I'm your AI Onboarding Mentor, trained on institutional best practices, senior TA experiences, and faculty guidance. I'm here to help you succeed in your TA role. How can I assist you today?"
  }
])

const userInput = ref('')
const isTyping = ref(false)

const suggestedQuestions = [
  'How do I handle my first week as a TA?',
  'What are common mistakes new TAs make?',
  'How do I balance TA work with coursework?',
  'When should I escalate a query?',
  'Tips for effective office hours?'
]

const availableMentors = [
  {
    id: 1,
    name: 'Dr. Priya Kumar',
    role: 'Senior TA',
    experience: '3 years',
    expertise: ['Design Patterns', 'Software Architecture', 'Code Review'],
    availability: 'Available',
    avatar: 'PK',
    rating: 4.9,
    responses: 156
  },
  {
    id: 2,
    name: 'Rahul Mehta',
    role: 'Senior TA',
    experience: '2 years',
    expertise: ['Machine Learning', 'Neural Networks', 'Python'],
    availability: 'Busy',
    avatar: 'RM',
    rating: 4.8,
    responses: 142
  },
  {
    id: 3,
    name: 'Prof. Ananya Sharma',
    role: 'Faculty Mentor',
    experience: '5 years',
    expertise: ['Databases', 'System Design', 'Teaching Methods'],
    availability: 'Available',
    avatar: 'AS',
    rating: 5.0,
    responses: 203
  },
  {
    id: 4,
    name: 'Karthik Reddy',
    role: 'Senior TA',
    experience: '2.5 years',
    expertise: ['Web Development', 'React', 'Node.js'],
    availability: 'Available',
    avatar: 'KR',
    rating: 4.7,
    responses: 98
  }
]

const discussionTopics = [
  {
    id: 1,
    title: 'Best practices for handling difficult student interactions',
    author: 'Sarah T.',
    replies: 12,
    lastActive: '2 hours ago',
    category: 'Communication'
  },
  {
    id: 2,
    title: 'Time management tips for juggling multiple courses',
    author: 'Mike J.',
    replies: 8,
    lastActive: '5 hours ago',
    category: 'Productivity'
  },
  {
    id: 3,
    title: 'How to provide constructive feedback without discouraging students',
    author: 'Lisa K.',
    replies: 15,
    lastActive: '1 day ago',
    category: 'Feedback'
  }
]

const upcomingOfficeHours = [
  {
    id: 1,
    mentor: 'Dr. Priya Kumar',
    date: 'Today',
    time: '2:00 PM - 4:00 PM',
    location: 'Virtual (Zoom)',
    spotsLeft: 3
  },
  {
    id: 2,
    mentor: 'Prof. Ananya Sharma',
    date: 'Tomorrow',
    time: '10:00 AM - 12:00 PM',
    location: 'Room 305',
    spotsLeft: 5
  },
  {
    id: 3,
    mentor: 'Rahul Mehta',
    date: 'Nov 3',
    time: '3:00 PM - 5:00 PM',
    location: 'Virtual (Teams)',
    spotsLeft: 2
  }
]

const quickStartTopics = [
  {
    id: 1,
    title: 'Getting Started as a TA',
    description: 'Learn the fundamentals of your TA responsibilities',
    questions: [
      'What are my main responsibilities?',
      'How do I communicate with students effectively?',
      'What tools do I need to use?'
    ]
  },
  {
    id: 2,
    title: 'Handling Student Queries',
    description: 'Best practices for responding to doubts',
    questions: [
      'How to prioritize urgent queries?',
      'Best response time expectations?',
      'When should I escalate to instructor?'
    ]
  },
  {
    id: 3,
    title: 'Time Management',
    description: 'Balance TA work with your coursework',
    questions: [
      'How many hours should I dedicate weekly?',
      'Tips for managing multiple courses?',
      'Avoiding burnout strategies'
    ]
  },
  {
    id: 4,
    title: 'Grading Best Practices',
    description: 'Fair and consistent assessment guidelines',
    questions: [
      'How to grade assignments fairly?',
      'Handling re-evaluation requests?',
      'Providing constructive feedback'
    ]
  },
  {
    id: 5,
    title: 'Common Challenges',
    description: 'Solutions to typical TA difficulties',
    questions: [
      'Dealing with difficult students?',
      'Managing large query volumes?',
      'Handling academic integrity issues'
    ]
  },
  {
    id: 6,
    title: 'Office Hours Tips',
    description: 'Making office hours effective',
    questions: [
      'How to structure office hours?',
      'Handling multiple students at once?',
      'Virtual vs in-person office hours'
    ]
  }
]

const seniorTATips = [
  {
    id: 1,
    author: 'Priya K. (Senior TA, 2 years)',
    tip: 'Create a FAQ document for common queries. Update it regularly and share it with students. This reduced my repeat questions by 40%.',
    category: 'Efficiency'
  },
  {
    id: 2,
    author: 'Rahul M. (Senior TA, 3 years)',
    tip: 'Set clear boundaries for response times. I tell students I respond within 24 hours on weekdays. This manages expectations and prevents burnout.',
    category: 'Work-Life Balance'
  },
  {
    id: 3,
    author: 'Ananya S. (Senior TA, 1.5 years)',
    tip: 'Use the doubt summarizer tool daily. It helps identify patterns quickly and lets you address multiple students with similar issues in one go.',
    category: 'Tools'
  },
  {
    id: 4,
    author: 'Karthik R. (Senior TA, 2.5 years)',
    tip: "Don't hesitate to escalate complex queries to instructors. It's better to get the right answer than to provide incorrect information.",
    category: 'Quality'
  }
]

const sendMessage = () => {
  if (!userInput.value.trim()) return

  messages.value.push({ role: 'user', text: userInput.value })
  const query = userInput.value
  userInput.value = ''
  isTyping.value = true

  setTimeout(() => {
    messages.value.push({
      role: 'ai',
      text: `Based on senior TA experiences and institutional best practices, here's my guidance:\n\nWhen dealing with "${query}", consider:\n\n1. Break down complex concepts into smaller, digestible parts\n2. Use real-world examples to illustrate your points\n3. Encourage students to think through problems step-by-step\n4. Avoid providing direct answers - guide them to discover solutions\n\nWould you like more specific guidance on this topic?`
    })
    isTyping.value = false
  }, 1800)
}
</script>