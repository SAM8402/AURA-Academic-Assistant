<template>
  <div class="flex min-h-screen bg-slate-50 text-slate-800">
    <component :is="role==='ta'? taSidebar : instructorSidebar" class="print:hidden" />
    <main class="flex-1 ml-64 p-6 lg:p-8 print:ml-0">
      <div class="max-w-5xl mx-auto flex flex-col gap-6">
        <!-- Header / Actions -->
        <div class="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 flex flex-col gap-4">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 class="text-3xl font-extrabold tracking-tight">Assessment Workspace</h1>
              <p class="text-slate-500 text-sm mt-1">Unified AI question paper generation for {{ roleLabel }}</p>
            </div>
            <div class="flex gap-2 flex-wrap">
              <button @click="resetForm" class="btn-secondary">Reset</button>
              <button @click="generate" :disabled="generating|| form.topics.length===0" class="btn-primary">{{ generating? 'Generating…' : 'Generate' }}</button>
              <button v-if="quizId" @click="goToQuizList" class="btn-success">View Quizzes</button>
            </div>
          </div>

          <!-- Form -->
          <form @submit.prevent="generate" class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-2">
            <div>
              <label class="form-label">Course ID *</label>
              <input v-model.number="form.courseId" type="number" required min="1" class="form-input" />
            </div>
            <div>
              <label class="form-label">Title *</label>
              <input v-model="form.title" type="text" required placeholder="e.g. Mid-Term Logic" class="form-input" />
              <div v-if="form.useLatex" class="mt-1 text-[10px] text-slate-500">LaTeX preview: <span v-html="latexPreview"></span></div>
            </div>
            <div class="md:col-span-2">
              <label class="form-label">Topics *</label>
              <div class="flex flex-wrap gap-2 mb-2">
                <span v-for="(t,i) in form.topics" :key="i" class="px-2 py-1 bg-blue-50 text-blue-700 rounded-md text-xs font-semibold flex items-center gap-1">
                  {{ t.name }} <button type="button" @click="removeTopic(i)" class="hover:text-red-600">✕</button>
                </span>
              </div>
              <div class="flex gap-2">
                <input v-model="newTopic" @keyup.enter.prevent="addTopic" placeholder="Add topic & Enter" class="form-input flex-1" />
                <button type="button" @click="addTopic" class="btn-secondary">Add</button>
                <button type="button" @click="form.topics=[]" v-if="form.topics.length" class="btn-danger">Clear</button>
              </div>
            </div>
            <div>
              <label class="form-label">Difficulty</label>
              <select v-model="form.difficulty" class="form-input">
                <option>Easy</option><option>Medium</option><option>Hard</option><option>Mixed</option>
              </select>
            </div>
            <div>
              <label class="form-label">Marks / Question</label>
              <input v-model.number="form.marks" type="number" min="1" class="form-input" />
            </div>
            <div>
              <label class="form-label">Total Questions</label>
              <input v-model.number="form.count" type="number" min="1" max="50" class="form-input" />
            </div>
            <div class="flex items-center gap-2">
              <input type="checkbox" v-model="form.useLatex" id="latex" />
              <label for="latex" class="text-xs font-semibold text-slate-600">Enable LaTeX preview</label>
            </div>
            <div class="flex items-center gap-4">
              <span class="text-[11px] font-bold uppercase tracking-wide text-slate-500">Publish Mode</span>
              <label class="text-xs flex items-center gap-1"><input type="radio" value="manual" v-model="form.publishMode" /> Manual</label>
              <label class="text-xs flex items-center gap-1"><input type="radio" value="auto" v-model="form.publishMode" /> Auto</label>
            </div>
          </form>

          <!-- Generation Status -->
          <div v-if="generating" class="mt-4 flex items-center gap-3 text-sm text-slate-600">
            <span class="animate-spin h-5 w-5 border-2 border-slate-300 border-t-blue-600 rounded-full"></span>
            Generating assessment… please wait.
          </div>
          <div v-if="error" class="mt-4 text-sm text-red-600 font-semibold">⚠ {{ error }}</div>
          <div v-if="successMessage" class="mt-4 text-sm text-green-600 font-semibold">✓ {{ successMessage }}</div>
        </div>

        <!-- Generated Summary -->
        <div v-if="quizId" class="bg-white border border-slate-200 rounded-2xl shadow-sm p-6">
          <h2 class="text-xl font-bold mb-3">Assessment Summary</h2>
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div><span class="font-semibold text-slate-600">Course:</span> {{ form.courseId }}</div>
            <div><span class="font-semibold text-slate-600">Difficulty:</span> {{ form.difficulty }}</div>
            <div><span class="font-semibold text-slate-600">Marks/Q:</span> {{ form.marks }}</div>
            <div><span class="font-semibold text-slate-600">Questions:</span> {{ form.count }}</div>
            <div class="col-span-2"><span class="font-semibold text-slate-600">Topics:</span> {{ form.topics.map(t=>t.name).join(', ') }}</div>
            <div class="col-span-2"><span class="font-semibold text-slate-600">Publish:</span> {{ form.publishMode }}</div>
          </div>
          <div class="mt-4 flex gap-2">
            <button @click="viewQuiz" class="btn-primary flex-1">Open Quiz</button>
            <button @click="resetForm" class="btn-secondary">New</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import instructorSidebar from '@/components/layout/instructorLayout/instructorSideBar.vue'
import taSidebar from '@/components/layout/TaLayout/TASidebar.vue'
import { api } from '@/api'
import { renderLatex } from '@/components/shared/assessment/renderLatex'

const props = defineProps({ role: { type: String, default: 'instructor' } })
const roleLabel = computed(()=> props.role === 'ta' ? 'Teaching Assistant' : 'Instructor')

const router = useRouter()
const generating = ref(false)
const error = ref('')
const successMessage = ref('')
const quizId = ref(null)
const newTopic = ref('')

const form = reactive({
  courseId: 1,
  title: '',
  topics: [],
  difficulty: 'Medium',
  marks: 5,
  count: 5,
  useLatex: false,
  publishMode: 'manual'
})

function addTopic(){ if(newTopic.value.trim()){ form.topics.push({ name:newTopic.value.trim() }); newTopic.value='' } }
function removeTopic(i){ form.topics.splice(i,1) }
function resetForm(){ Object.assign(form,{ courseId:1,title:'',topics:[],difficulty:'Medium',marks:5,count:5,useLatex:false,publishMode:'manual'}); quizId.value=null; successMessage.value=''; error.value='' }

async function generate(){
  if(!form.title || form.topics.length===0) { error.value='Add title & at least one topic'; return }
  generating.value=true; error.value=''; successMessage.value=''; quizId.value=null
  try {
    const payload = {
      course_id: form.courseId,
      title: form.title,
      topics: form.topics.map(t=>t.name),
      difficulty: form.difficulty,
      marks_per_question: form.marks,
      num_questions: form.count,
      use_latex: form.useLatex,
      publish_mode: form.publishMode
    }
    const res = await api.post('/quizzes/generate', payload, { timeout: 60000 })
    quizId.value = res.data?.id || null
    successMessage.value = `Quiz "${form.title}" generated successfully!`
  } catch(e){ 
    const detail = e.response?.data?.detail
    if (Array.isArray(detail)) {
      error.value = detail.map(err => `${err.loc?.join('.')} - ${err.msg}`).join('; ')
    } else {
      error.value = detail || e.message
    }
  }
  finally { generating.value=false }
}

function viewQuiz(){
  if(!quizId.value) return
  const base = props.role==='ta'? '/ta' : '/instructor'
  router.push(`${base}/quiz-details/${quizId.value}`)
}
function goToQuizList(){ router.push(props.role==='ta'? '/ta/quiz-list' : '/instructor/quiz-list') }

// LaTeX preview computed
const latexPreview = computed(()=> form.useLatex ? renderLatex(form.title || '') : '')
</script>

<style scoped>
.form-label { @apply block text-[10px] font-extrabold text-slate-500 mb-1.5 uppercase tracking-wider; }
.form-input { @apply w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition text-sm text-slate-800; }
.btn-primary { @apply px-5 py-2.5 rounded-lg bg-blue-600 text-white text-xs font-bold shadow hover:bg-blue-700 transition disabled:opacity-40; }
.btn-secondary { @apply px-5 py-2.5 rounded-lg bg-white border border-slate-300 text-slate-700 text-xs font-bold shadow-sm hover:bg-slate-50 transition disabled:opacity-40; }
.btn-danger { @apply px-4 py-2 rounded-lg bg-red-100 text-red-600 text-xs font-bold shadow-sm hover:bg-red-200 transition disabled:opacity-40; }
.btn-success { @apply px-5 py-2.5 rounded-lg bg-green-600 text-white text-xs font-bold shadow hover:bg-green-700 transition disabled:opacity-40; }
</style>
