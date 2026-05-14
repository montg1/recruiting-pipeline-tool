<script setup>
/**
 * CVUploadView.vue — Module 2: AI Resume Screener
 * Upload a PDF, select a Job, get AI scoring via n8n + Claude
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { screenResume, getJobs, createCandidate, createApplication } from '@/services/api'
import ScoreCard from '@/components/ScoreCard.vue'

const router = useRouter()

/* ---- State ---- */
const step = ref(1) // 1 = upload, 2 = results
const selectedFile = ref(null)
const selectedJobId = ref('')
const jobs = ref([])
const screening = ref(false)
const saving = ref(false)
const error = ref(null)
const result = ref(null)
const notification = ref(null)
const dragOver = ref(false)

/* ---- Load jobs on mount ---- */
const loadJobs = async () => {
  try {
    const { data } = await getJobs()
    jobs.value = Array.isArray(data) ? data : []
    if (jobs.value.length > 0) selectedJobId.value = jobs.value[0].id
  } catch {
    // Jobs endpoint may not exist yet — use fallback
    jobs.value = [
      { id: 1, title: 'Backend Engineer' },
      { id: 2, title: 'Frontend Developer' },
      { id: 3, title: 'Full Stack Developer' },
    ]
    selectedJobId.value = 1
  }
}
loadJobs()

/* ---- Computed ---- */
const canSubmit = computed(() => selectedFile.value && selectedJobId.value && !screening.value)
const selectedJobTitle = computed(() => {
  const job = jobs.value.find(j => j.id == selectedJobId.value)
  return job ? job.title : ''
})

/* ---- File handling ---- */
function onFileSelect(e) {
  const file = e.target.files[0]
  if (file && file.type === 'application/pdf') {
    selectedFile.value = file
    error.value = null
  } else {
    error.value = 'Please select a PDF file.'
  }
}

function onDrop(e) {
  dragOver.value = false
  const file = e.dataTransfer.files[0]
  if (file && file.type === 'application/pdf') {
    selectedFile.value = file
    error.value = null
  } else {
    error.value = 'Please drop a PDF file.'
  }
}

function removeFile() {
  selectedFile.value = null
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

/* ---- Submit for screening ---- */
async function handleScreen() {
  if (!canSubmit.value) return
  screening.value = true
  error.value = null

  try {
    const { data } = await screenResume(selectedFile.value, selectedJobId.value)
    result.value = data
    step.value = 2
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Screening failed. Check your n8n webhook.'
  } finally {
    screening.value = false
  }
}

/* ---- Save candidate to pipeline ---- */
async function handleSaveToPipeline() {
  if (!result.value) return
  saving.value = true
  error.value = null

  try {
    const ev = result.value.evaluation
    const scores = Array.isArray(ev) && ev[0]?.output ? ev[0].output : ev

    const candidatePayload = {
      full_name: selectedFile.value.name.replace('.pdf', '').replace(/_/g, ' '),
      email: `candidate-${Date.now()}@pipeline.local`,
      source: 'AI Resume Screen',
      parsed_data: {
        ai_evaluation: scores,
        resume_filename: result.value.resume_filename,
        job_matched: result.value.job_title,
      },
    }

    const { data: candidate } = await createCandidate(candidatePayload)

    try {
      await createApplication(candidate.id, { job_id: Number(selectedJobId.value) })
    } catch (_) { /* job may not exist */ }

    showNotification('Candidate added to pipeline with AI insights!')
    setTimeout(() => router.push('/'), 1500)
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Failed to save candidate.'
  } finally {
    saving.value = false
  }
}

/* ---- Helpers ---- */
function resetAll() {
  step.value = 1
  selectedFile.value = null
  result.value = null
  error.value = null
}

function showNotification(msg) {
  notification.value = msg
  setTimeout(() => { notification.value = null }, 3000)
}
</script>

<template>
  <div class="min-h-[calc(100vh-4rem)]">
    <!-- Header -->
    <div class="bg-white border-b border-hplus-border z-30">
      <div class="px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold text-hplus-text tracking-tight">AI Resume Screener</h1>
            <p class="text-sm text-hplus-text-muted mt-0.5">Upload a CV and get AI-powered scoring against a job description</p>
          </div>
          <div class="hidden sm:flex items-center gap-3">
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all"
                   :class="step >= 1 ? 'bg-hplus-gold text-hplus-navy' : 'bg-slate-200 text-slate-500'">1</div>
              <span class="text-xs font-medium" :class="step >= 1 ? 'text-hplus-text' : 'text-slate-400'">Upload</span>
            </div>
            <div class="w-8 h-px" :class="step >= 2 ? 'bg-hplus-gold' : 'bg-slate-200'"></div>
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all"
                   :class="step >= 2 ? 'bg-hplus-gold text-hplus-navy' : 'bg-slate-200 text-slate-500'">2</div>
              <span class="text-xs font-medium" :class="step >= 2 ? 'text-hplus-text' : 'text-slate-400'">Results</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      <!-- Error banner -->
      <div v-if="error" class="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3">
        <svg class="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <div>
          <p class="text-sm font-medium text-red-700">{{ error }}</p>
          <button @click="error = null" class="text-xs text-red-500 underline mt-1">Dismiss</button>
        </div>
      </div>

      <!-- ============ STEP 1: Upload ============ -->
      <Transition name="fade" mode="out-in">
        <div v-if="step === 1" key="step1">
          <div class="bg-white rounded-2xl border border-hplus-border shadow-sm p-6 sm:p-8">
            <h2 class="text-lg font-bold text-hplus-text mb-1">Upload CV</h2>
            <p class="text-sm text-hplus-text-muted mb-6">Select a job position and upload a PDF resume for AI analysis.</p>

            <!-- Job selector -->
            <div class="mb-6">
              <label class="block text-sm font-semibold text-hplus-text mb-2">Job Position</label>
              <select v-model="selectedJobId"
                      class="w-full px-4 py-3 rounded-xl border border-hplus-border bg-white text-sm
                             focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold transition-all duration-200">
                <option v-for="job in jobs" :key="job.id" :value="job.id">{{ job.title }}</option>
              </select>
            </div>

            <!-- Drop zone -->
            <div class="mb-6">
              <label class="block text-sm font-semibold text-hplus-text mb-2">Resume PDF</label>
              <div v-if="!selectedFile"
                   @dragover.prevent="dragOver = true"
                   @dragleave="dragOver = false"
                   @drop.prevent="onDrop"
                   class="border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200"
                   :class="dragOver ? 'border-hplus-gold bg-hplus-gold/5' : 'border-slate-300 hover:border-hplus-gold/50 hover:bg-slate-50'"
                   @click="$refs.fileInput.click()">
                <svg class="w-10 h-10 mx-auto text-slate-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                        d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                <p class="text-sm text-slate-500 font-medium">Drop your PDF here or <span class="text-hplus-gold underline">browse</span></p>
                <p class="text-xs text-slate-400 mt-1">PDF only, max 10MB</p>
                <input ref="fileInput" type="file" accept=".pdf" class="hidden" @change="onFileSelect" />
              </div>

              <!-- File preview -->
              <div v-else class="flex items-center gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200">
                <div class="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center flex-shrink-0">
                  <svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                  </svg>
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-hplus-text truncate">{{ selectedFile.name }}</p>
                  <p class="text-xs text-slate-400">{{ formatSize(selectedFile.size) }}</p>
                </div>
                <button @click="removeFile" class="p-1.5 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-500 transition">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                  </svg>
                </button>
              </div>
            </div>

            <!-- Submit button -->
            <button @click="handleScreen" :disabled="!canSubmit"
                    class="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold
                           transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    :class="canSubmit
                      ? 'bg-hplus-gold text-hplus-navy shadow-md shadow-hplus-gold/25 hover:bg-amber-400 hover:shadow-lg active:scale-[0.98]'
                      : 'bg-slate-200 text-slate-500'">
              <template v-if="screening">
                <div class="flex gap-1.5">
                  <div class="w-2 h-2 rounded-full bg-hplus-navy/60 animate-bounce" style="animation-delay: 0ms"></div>
                  <div class="w-2 h-2 rounded-full bg-hplus-navy/60 animate-bounce" style="animation-delay: 150ms"></div>
                  <div class="w-2 h-2 rounded-full bg-hplus-navy/60 animate-bounce" style="animation-delay: 300ms"></div>
                </div>
                Analyzing with AI...
              </template>
              <template v-else>
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                </svg>
                Screen Resume with AI
              </template>
            </button>
          </div>
        </div>

        <!-- ============ STEP 2: Results ============ -->
        <div v-else key="step2">
          <div class="bg-white rounded-2xl border border-hplus-border shadow-sm p-6 sm:p-8">
            <div class="flex items-center justify-between mb-6">
              <div>
                <h2 class="text-lg font-bold text-hplus-text">Screening Results</h2>
                <p class="text-sm text-hplus-text-muted">AI-powered evaluation of the uploaded resume.</p>
              </div>
              <button @click="resetAll"
                      class="text-xs font-medium text-slate-500 hover:text-hplus-navy px-3 py-1.5 rounded-lg hover:bg-slate-100 transition">
                Screen Another
              </button>
            </div>

            <!-- ScoreCard Component -->
            <ScoreCard :result="result" />

            <!-- Action buttons -->
            <div class="flex items-center gap-3 mt-8 pt-6 border-t border-hplus-border">
              <button @click="resetAll"
                      class="flex-1 py-3 rounded-xl text-sm font-semibold text-slate-600 bg-slate-100
                             hover:bg-slate-200 transition-all duration-200">
                Screen Another CV
              </button>
              <button @click="handleSaveToPipeline" :disabled="saving"
                      class="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold
                             bg-hplus-gold text-hplus-navy shadow-md shadow-hplus-gold/25
                             hover:bg-amber-400 hover:shadow-lg active:scale-[0.98]
                             disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200">
                <template v-if="saving">
                  <div class="flex gap-1.5">
                    <div class="w-2 h-2 rounded-full bg-hplus-navy/60 animate-bounce"></div>
                    <div class="w-2 h-2 rounded-full bg-hplus-navy/60 animate-bounce" style="animation-delay: 150ms"></div>
                    <div class="w-2 h-2 rounded-full bg-hplus-navy/60 animate-bounce" style="animation-delay: 300ms"></div>
                  </div>
                  Saving...
                </template>
                <template v-else>
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                  </svg>
                  Add Candidate to Pipeline
                </template>
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </div>

    <!-- Toast -->
    <Transition name="fade">
      <div v-if="notification"
           class="fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-xl shadow-xl
                  border backdrop-blur-sm bg-emerald-50/90 border-emerald-200 text-emerald-700">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
        </svg>
        <span class="text-sm font-medium">{{ notification }}</span>
      </div>
    </Transition>
  </div>
</template>
