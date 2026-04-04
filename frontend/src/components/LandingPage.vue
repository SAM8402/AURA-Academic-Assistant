
<template>
  <div class="min-h-screen bg-white">
    <!-- ==================== HEADER ==================== -->
    <header class="bg-white/95 backdrop-blur-sm border-b border-gray-100 sticky top-0 z-50 animate-slide-down">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center py-4">
          <div class="flex items-center cursor-pointer" @click="goToLogin">
            <div class="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-sm hover:shadow-md transition-shadow duration-200">
              <span class="text-white font-bold text-xl">A</span>
            </div>
            <span class="ml-3 text-2xl font-bold text-gray-900">Aura</span>
          </div>

          <nav class="hidden md:flex space-x-8">
            <a href="#home" class="text-gray-600 hover:text-blue-600 font-medium transition-colors duration-200">Home</a>
            <a href="#features" class="text-gray-600 hover:text-blue-600 font-medium transition-colors duration-200">Features</a>
            <a href="#about" class="text-gray-600 hover:text-blue-600 font-medium transition-colors duration-200">About</a>
            <a href="#contact" class="text-gray-600 hover:text-blue-600 font-medium transition-colors duration-200">Contact</a>
          </nav>

          <div class="flex items-center space-x-3">
            <button @click="goToLogin" class="px-5 py-2.5 text-blue-600 font-medium hover:bg-blue-50 rounded-lg transition-colors duration-200 cursor-pointer">Sign In</button>
            <button @click="goToRegister" class="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors duration-200 shadow-sm hover:shadow-md cursor-pointer">Get Started</button>
          </div>
        </div>
      </div>
    </header>

    <!-- ==================== HERO ==================== -->
    <section id="home" class="py-24 sm:py-32 bg-gradient-to-b from-blue-50 via-white to-white text-center overflow-hidden">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="inline-flex items-center px-4 py-2 bg-blue-50 rounded-full text-blue-600 text-sm font-medium mb-8 animate-float">
          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
          AI-Powered Academic Support
        </div>
        <h1 class="text-4xl sm:text-5xl md:text-6xl font-bold text-gray-900 mb-6 leading-tight tracking-tight animate-fade-in-up">
          Welcome to <span class="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">Aura</span>
        </h1>
        <p class="text-lg sm:text-xl text-gray-600 mb-4 max-w-3xl mx-auto leading-relaxed animate-fade-in-up stagger-1">
          Your AI-Powered Academic Support System for IITM Students, TAs, Instructors, and Administrators
        </p>
        <p class="text-base sm:text-lg text-gray-500 mb-10 max-w-2xl mx-auto leading-relaxed animate-fade-in-up stagger-2">
          Revolutionizing academic support through intelligent assistance, personalized learning, and seamless communication
        </p>
        <div class="flex flex-col sm:flex-row items-center justify-center gap-4 animate-fade-in-up stagger-3">
          <button @click="goToRegister" class="px-8 py-3.5 bg-blue-600 text-white hover:bg-blue-700 rounded-xl text-lg font-semibold shadow-lg hover:shadow-xl transition-all duration-200 cursor-pointer hover:scale-105">
            Explore Aura
          </button>
          <a href="#features" class="px-8 py-3.5 text-gray-600 hover:text-blue-600 font-semibold transition-colors duration-200 cursor-pointer">
            Learn more &darr;
          </a>
        </div>
      </div>
    </section>

    <!-- ==================== FEATURES ==================== -->
    <section id="features" class="py-20 bg-white">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-16" ref="featuresHeader">
          <h2 class="text-3xl sm:text-4xl font-bold text-gray-900 mb-4" :class="{ 'animate-fade-in-up': featuresVisible }">Key Features</h2>
          <p class="text-lg text-gray-500" :class="{ 'animate-fade-in-up stagger-1': featuresVisible }">Empowering academic excellence through AI innovation</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div
            v-for="(feature, index) in features"
            :key="index"
            class="bg-white border border-gray-100 rounded-2xl p-6 hover-lift cursor-pointer group"
            :class="{ 'animate-fade-in-up': featuresVisible }"
            :style="{ animationDelay: `${(index + 1) * 0.1}s` }"
          >
            <div :class="['w-12 h-12 rounded-xl flex items-center justify-center mb-4 transition-transform duration-200 group-hover:scale-110', feature.color]">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="feature.iconPath"/>
              </svg>
            </div>
            <h3 class="text-lg font-bold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors duration-200">{{ feature.title }}</h3>
            <p class="text-gray-500 text-sm leading-relaxed">{{ feature.description }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== ABOUT ==================== -->
    <section id="about" class="py-20 bg-gray-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8" ref="aboutSection">
        <div class="text-center mb-12">
          <h2 class="text-3xl sm:text-4xl font-bold text-gray-900 mb-4" :class="{ 'animate-fade-in-up': aboutVisible }">About Aura</h2>
          <p class="text-lg text-gray-500 max-w-3xl mx-auto" :class="{ 'animate-fade-in-up stagger-1': aboutVisible }">
            Aura is an innovative AI-powered academic support system designed specifically for the IITM BS Degree Program community.
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
          <div :class="{ 'animate-fade-in-left': aboutVisible }">
            <h3 class="text-2xl font-bold text-gray-900 mb-4">Our Mission</h3>
            <p class="text-gray-600 mb-6 leading-relaxed">
              To revolutionize the academic experience at IITM by leveraging cutting-edge Generative AI technologies to provide personalized, accessible, and efficient support.
            </p>
            <h3 class="text-2xl font-bold text-gray-900 mb-4">Who We Serve</h3>
            <ul class="space-y-3">
              <li v-for="(item, index) in serveList" :key="index" class="flex items-start">
                <div class="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center mr-3 mt-0.5 flex-shrink-0">
                  <svg class="w-3.5 h-3.5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>
                </div>
                <span class="text-gray-600" v-html="item"></span>
              </li>
            </ul>
          </div>

          <div class="bg-white rounded-2xl shadow-lg p-8 border border-gray-100" :class="{ 'animate-fade-in-right': aboutVisible }">
            <h3 class="text-2xl font-bold text-gray-900 mb-6">Key Technologies</h3>
            <div class="space-y-5">
              <div v-for="(tech, i) in technologies" :key="i" class="flex items-center p-3 rounded-xl hover:bg-gray-50 transition-colors duration-200">
                <div :class="['w-10 h-10 rounded-xl flex items-center justify-center mr-4 flex-shrink-0', tech.bg]">
                  <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="tech.iconPath"/>
                  </svg>
                </div>
                <div>
                  <h4 class="font-bold text-gray-900 text-sm">{{ tech.title }}</h4>
                  <p class="text-xs text-gray-500">{{ tech.desc }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== CONTACT ==================== -->
    <section id="contact" class="py-20 bg-white text-center" ref="contactSection">
      <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 class="text-3xl sm:text-4xl font-bold text-gray-900 mb-4" :class="{ 'animate-fade-in-up': contactVisible }">Get in Touch</h2>
        <p class="text-lg text-gray-500 mb-8" :class="{ 'animate-fade-in-up stagger-1': contactVisible }">
          Have questions about Aura? We'd love to hear from you.
        </p>
        <div class="bg-gray-50 rounded-2xl p-8 border border-gray-100" :class="{ 'animate-fade-in-scale stagger-2': contactVisible }">
          <p class="text-gray-600 mb-6">For inquiries, feedback, or support, please contact us at:</p>
          <a href="mailto:aura@iitm.ac.in" class="inline-flex items-center text-blue-600 font-bold text-lg hover:text-blue-700 transition-colors duration-200">
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
            aura@iitm.ac.in
          </a>
        </div>
      </div>
    </section>

    <!-- ==================== FOOTER ==================== -->
    <footer class="bg-gray-900 text-white py-16">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div>
            <div class="flex items-center mb-4">
              <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-500 rounded-xl flex items-center justify-center">
                <span class="text-white font-bold text-xl">A</span>
              </div>
              <span class="ml-3 text-2xl font-bold">Aura</span>
            </div>
            <p class="text-gray-400 text-sm leading-relaxed">AI-Powered Academic Support System for IITM</p>
          </div>
          <div>
            <h4 class="font-bold text-lg mb-4">Quick Links</h4>
            <ul class="space-y-2">
              <li><a href="#home" class="text-gray-400 hover:text-white transition-colors duration-200 text-sm">Home</a></li>
              <li><a href="#features" class="text-gray-400 hover:text-white transition-colors duration-200 text-sm">Features</a></li>
              <li><a href="#about" class="text-gray-400 hover:text-white transition-colors duration-200 text-sm">About</a></li>
              <li><a href="#contact" class="text-gray-400 hover:text-white transition-colors duration-200 text-sm">Contact</a></li>
            </ul>
          </div>
          <div>
            <h4 class="font-bold text-lg mb-4">Connect</h4>
            <p class="text-gray-400 text-sm mb-2">Indian Institute of Technology Madras</p>
            <p class="text-gray-400 text-sm">Chennai, Tamil Nadu 600036</p>
          </div>
        </div>
        <div class="border-t border-gray-800 mt-10 pt-8 text-center text-gray-500 text-sm">
          <p>&copy; 2025 Aura. All rights reserved. | IITM BS Degree Program</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const goToRegister = () => router.push('/register')
const goToLogin = () => router.push('/login')

// Scroll-triggered animation visibility
const featuresHeader = ref(null)
const aboutSection = ref(null)
const contactSection = ref(null)
const featuresVisible = ref(false)
const aboutVisible = ref(false)
const contactVisible = ref(false)

let observers = []

onMounted(() => {
  const createObserver = (elRef, visibleRef) => {
    if (!elRef.value) return
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) visibleRef.value = true },
      { threshold: 0.1 }
    )
    obs.observe(elRef.value)
    observers.push(obs)
  }

  createObserver(featuresHeader, featuresVisible)
  createObserver(aboutSection, aboutVisible)
  createObserver(contactSection, contactVisible)

  // Smooth scroll
  document.documentElement.style.scrollBehavior = 'smooth'
})

onUnmounted(() => {
  observers.forEach(obs => obs.disconnect())
  document.documentElement.style.scrollBehavior = ''
})

const features = [
  { iconPath: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z', color: 'bg-blue-100 text-blue-600', title: 'RAG-based AI Assistant', description: 'Get instant answers to academic questions using retrieval-augmented generation.' },
  { iconPath: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z', color: 'bg-purple-100 text-purple-600', title: 'Smart Study Assistant', description: 'Receive weekly summaries of lectures, tasks, and deadlines.' },
  { iconPath: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253', color: 'bg-green-100 text-green-600', title: 'AI Content Recommender', description: 'Get personalized content recommendations based on your learning patterns.' },
  { iconPath: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z', color: 'bg-orange-100 text-orange-600', title: 'TA Doubt Summarizer', description: 'Automatically summarize student queries for efficient TA workload management.' },
  { iconPath: 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9', color: 'bg-red-100 text-red-600', title: 'AI Query Escalation', description: 'Automatically classify and route queries to the right person by urgency.' },
  { iconPath: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6', color: 'bg-indigo-100 text-indigo-600', title: 'Analytics Dashboard', description: 'Visualize system-wide metrics on FAQs, unresolved queries, and sentiment.' },
  { iconPath: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z', color: 'bg-pink-100 text-pink-600', title: 'Discourse Integration', description: 'Quickly find if your question has been asked before in forum threads.' },
  { iconPath: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z', color: 'bg-cyan-100 text-cyan-600', title: 'AI Onboarding Mentor', description: 'Personalized onboarding guide for new TAs joining the system.' },
  { iconPath: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4', color: 'bg-yellow-100 text-yellow-600', title: 'Assessment Generator', description: 'Dynamically create question sets with difficulty levels and scoring.' }
]

const serveList = [
  '<strong>Students:</strong> Get instant answers, study help, and resource recommendations.',
  '<strong>TAs:</strong> Manage workload efficiently with automated doubt summarization.',
  '<strong>Instructors:</strong> Track student engagement and generate assessments.',
  '<strong>Administrators:</strong> Gain insights with system-wide analytics and reporting.'
]

const technologies = [
  { bg: 'bg-gradient-to-br from-blue-500 to-blue-600', iconPath: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z', title: 'RAG (Retrieval Augmented Generation)', desc: 'For accurate, context-aware responses' },
  { bg: 'bg-gradient-to-br from-purple-500 to-purple-600', iconPath: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z', title: 'Conversational AI', desc: 'Natural language interaction powered by Gemini' },
  { bg: 'bg-gradient-to-br from-green-500 to-green-600', iconPath: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6', title: 'AI Agents & Workflow Automation', desc: 'Intelligent task management' },
  { bg: 'bg-gradient-to-br from-orange-500 to-orange-600', iconPath: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z', title: 'LLM-based Summarization', desc: 'Concise information extraction' }
]
</script>
