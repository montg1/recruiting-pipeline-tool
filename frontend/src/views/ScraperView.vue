<script setup>
/**
 * ScraperView — Module 1: Candidate Data Extraction
 * Two-step flow: Extract → Preview/Edit → Save to Pipeline
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { extractCandidate, createCandidate, createApplication } from '@/services/api'

const router = useRouter()

/* ---- State ---- */
const step = ref(1) // 1 = input, 2 = preview/edit
const inputType = ref('url')
const payload = ref('')
const extracting = ref(false)
const saving = ref(false)
const error = ref(null)
const notification = ref(null)

// Editable candidate fields (populated after extraction)
const form = ref({
  full_name: '',
  email: '',
  phone: '',
  linkedin_url: '',
  source: '',
  skills: '',
  experience_summary: '',
  education_summary: '',
})
const rawJson = ref(null)

/* ---- Input type toggle ---- */
const isUrl = computed(() => inputType.value === 'url')
const canExtract = computed(() => payload.value.trim().length > 5)

/* ---- Step 1: Extract ---- */
async function handleExtract() {
  if (!canExtract.value) return
  extracting.value = true
  error.value = null

  try {
    const { data } = await extractCandidate(inputType.value, payload.value.trim())
    rawJson.value = data

    // Map n8n response fields into editable form
    form.value = {
      full_name: data.full_name || data.Name || data.name || '',
      email: data.email || data.Email || '',
      phone: data.phone || data.Phone || '',
      linkedin_url: data.linkedin_url || data.LinkedIn || payload.value.trim(),
      source: data.source || (isUrl.value ? 'LinkedIn' : 'Manual Entry'),
      skills: Array.isArray(data.skills || data.Skills)
        ? (data.skills || data.Skills).join(', ')
        : (data.skills || data.Skills || ''),
      experience_summary: Array.isArray(data.experience || data.WorkExperience)
        ? (data.experience || data.WorkExperience).map(e =>
            `${e.title || e.role || ''} at ${e.company || ''} (${e.date_range || e.dates || ''})`
          ).join('\n')
        : (data.experience_summary || data.experience || ''),
      education_summary: Array.isArray(data.education || data.Education)
        ? (data.education || data.Education).map(e =>
            `${e.degree || ''} — ${e.school || e.institution || ''}`
          ).join('\n')
        : (data.education_summary || data.education || ''),
    }

    step.value = 2
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Extraction failed. Check your n8n webhook.'
  } finally {
    extracting.value = false
  }
}

/* ---- Step 2: Save to pipeline ---- */
async function handleSave() {
  if (!form.value.full_name || !form.value.email) {
    error.value = 'Name and Email are required.'
    return
  }
  saving.value = true
  error.value = null

  try {
    const candidatePayload = {
      full_name: form.value.full_name,
      email: form.value.email,
      phone: form.value.phone || null,
      linkedin_url: form.value.linkedin_url || null,
      source: form.value.source || null,
      parsed_data: {
        skills: form.value.skills,
        experience: form.value.experience_summary,
        education: form.value.education_summary,
        raw_extraction: rawJson.value,
      },
    }

    const { data: candidate } = await createCandidate(candidatePayload)

    // Auto-apply to default job (job_id = 1)
    try {
      await createApplication(candidate.id, { job_id: 1 })
    } catch (_) { /* job may not exist yet */ }

    showNotification(`${form.value.full_name} saved to pipeline!`)
    setTimeout(() => router.push('/'), 1500)
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Failed to save candidate.'
  } finally {
    saving.value = false
  }
}

/* ---- Helpers ---- */
function resetForm() {
  step.value = 1
  payload.value = ''
  error.value = null
  rawJson.value = null
  form.value = { full_name:'', email:'', phone:'', linkedin_url:'', source:'', skills:'', experience_summary:'', education_summary:'' }
}

function showNotification(message) {
  notification.value = message
  setTimeout(() => { notification.value = null }, 3000)
}
</script>

<template>
  <div class="min-h-[calc(100vh-4rem)]">
    <!-- Header -->
    <div class="bg-white border-b border-hplus-border sticky top-16 z-30">
      <div class="px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold text-hplus-text tracking-tight">
              Candidate Scraper
            </h1>
            <p class="text-sm text-hplus-text-muted mt-0.5">
              Extract candidate data from a URL or paste raw text
            </p>
          </div>
          <!-- Step indicator -->
          <div class="hidden sm:flex items-center gap-3">
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all"
                   :class="step >= 1 ? 'bg-hplus-gold text-hplus-navy' : 'bg-slate-200 text-slate-500'">1</div>
              <span class="text-xs font-medium" :class="step >= 1 ? 'text-hplus-text' : 'text-slate-400'">Extract</span>
            </div>
            <div class="w-8 h-px" :class="step >= 2 ? 'bg-hplus-gold' : 'bg-slate-200'"></div>
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all"
                   :class="step >= 2 ? 'bg-hplus-gold text-hplus-navy' : 'bg-slate-200 text-slate-500'">2</div>
              <span class="text-xs font-medium" :class="step >= 2 ? 'text-hplus-text' : 'text-slate-400'">Review & Save</span>
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

      <!-- ============ STEP 1: Input ============ -->
      <Transition name="fade" mode="out-in">
        <div v-if="step === 1" key="step1">
          <div class="bg-white rounded-2xl border border-hplus-border shadow-sm p-6 sm:p-8">
            <h2 class="text-lg font-bold text-hplus-text mb-1">Data Source</h2>
            <p class="text-sm text-hplus-text-muted mb-6">Choose how you'd like to provide candidate information.</p>

            <!-- Type toggle -->
            <div class="flex rounded-xl bg-slate-100 p-1 mb-6">
              <button v-for="t in [{val:'url', label:'URL (LinkedIn)', icon:'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101'}, {val:'text', label:'Paste Text', icon:'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z'}]"
                      :key="t.val"
                      @click="inputType = t.val"
                      class="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all duration-200"
                      :class="inputType === t.val
                        ? 'bg-white text-hplus-navy shadow-sm'
                        : 'text-slate-500 hover:text-slate-700'">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="t.icon"/>
                </svg>
                {{ t.label }}
              </button>
            </div>

            <!-- Input field -->
            <div class="mb-6">
              <label class="block text-sm font-semibold text-hplus-text mb-2">
                {{ isUrl ? 'Profile URL' : 'Candidate Information' }}
              </label>
              <input v-if="isUrl" v-model="payload" type="url"
                     placeholder="https://www.linkedin.com/in/john-doe/"
                     class="w-full px-4 py-3 rounded-xl border border-hplus-border bg-slate-50/50
                            text-sm text-hplus-text placeholder-slate-400
                            focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold
                            transition-all duration-200" />
              <textarea v-else v-model="payload" rows="8"
                        placeholder="Paste resume text, job application details, or any candidate information here..."
                        class="w-full px-4 py-3 rounded-xl border border-hplus-border bg-slate-50/50
                               text-sm text-hplus-text placeholder-slate-400 resize-none
                               focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold
                               transition-all duration-200"></textarea>
            </div>

            <!-- Extract button -->
            <button @click="handleExtract" :disabled="!canExtract || extracting"
                    class="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold
                           transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    :class="canExtract
                      ? 'bg-hplus-gold text-hplus-navy shadow-md shadow-hplus-gold/25 hover:bg-amber-400 hover:shadow-lg active:scale-[0.98]'
                      : 'bg-slate-200 text-slate-500'">
              <template v-if="extracting">
                <div class="flex gap-1.5">
                  <div class="w-2 h-2 rounded-full bg-hplus-navy/60 pulse-dot"></div>
                  <div class="w-2 h-2 rounded-full bg-hplus-navy/60 pulse-dot"></div>
                  <div class="w-2 h-2 rounded-full bg-hplus-navy/60 pulse-dot"></div>
                </div>
                Extracting...
              </template>
              <template v-else>
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                </svg>
                Extract Candidate Data
              </template>
            </button>
          </div>
        </div>

        <!-- ============ STEP 2: Preview & Edit ============ -->
        <div v-else key="step2">
          <div class="bg-white rounded-2xl border border-hplus-border shadow-sm p-6 sm:p-8">
            <div class="flex items-center justify-between mb-6">
              <div>
                <h2 class="text-lg font-bold text-hplus-text">Review Extracted Data</h2>
                <p class="text-sm text-hplus-text-muted">Verify and edit the details before saving.</p>
              </div>
              <button @click="resetForm"
                      class="text-xs font-medium text-slate-500 hover:text-hplus-navy px-3 py-1.5 rounded-lg hover:bg-slate-100 transition">
                Start Over
              </button>
            </div>

            <!-- Form fields -->
            <div class="space-y-5">
              <!-- Row: Name + Email -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs font-semibold text-hplus-text mb-1.5">
                    Full Name <span class="text-red-400">*</span>
                  </label>
                  <input v-model="form.full_name" type="text"
                         class="w-full px-3 py-2.5 rounded-lg border border-hplus-border text-sm
                                focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold transition" />
                </div>
                <div>
                  <label class="block text-xs font-semibold text-hplus-text mb-1.5">
                    Email <span class="text-red-400">*</span>
                  </label>
                  <input v-model="form.email" type="email"
                         class="w-full px-3 py-2.5 rounded-lg border border-hplus-border text-sm
                                focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold transition" />
                </div>
              </div>

              <!-- Row: Phone + Source -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs font-semibold text-hplus-text mb-1.5">Phone</label>
                  <input v-model="form.phone" type="text"
                         class="w-full px-3 py-2.5 rounded-lg border border-hplus-border text-sm
                                focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold transition" />
                </div>
                <div>
                  <label class="block text-xs font-semibold text-hplus-text mb-1.5">Source</label>
                  <select v-model="form.source"
                          class="w-full px-3 py-2.5 rounded-lg border border-hplus-border text-sm bg-white
                                 focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold transition">
                    <option value="LinkedIn">LinkedIn</option>
                    <option value="JobsDB">JobsDB</option>
                    <option value="Referral">Referral</option>
                    <option value="Manual Entry">Manual Entry</option>
                    <option value="n8n_scrape">n8n Scrape</option>
                  </select>
                </div>
              </div>

              <!-- LinkedIn URL -->
              <div>
                <label class="block text-xs font-semibold text-hplus-text mb-1.5">LinkedIn URL</label>
                <input v-model="form.linkedin_url" type="url"
                       class="w-full px-3 py-2.5 rounded-lg border border-hplus-border text-sm
                              focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold transition" />
              </div>

              <!-- Divider -->
              <div class="border-t border-hplus-border pt-5">
                <h3 class="text-sm font-bold text-hplus-text mb-4">AI-Extracted Details</h3>
              </div>

              <!-- Skills -->
              <div>
                <label class="block text-xs font-semibold text-hplus-text mb-1.5">Skills</label>
                <input v-model="form.skills" type="text" placeholder="e.g. Python, React, SQL"
                       class="w-full px-3 py-2.5 rounded-lg border border-hplus-border text-sm
                              focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold transition" />
              </div>

              <!-- Experience -->
              <div>
                <label class="block text-xs font-semibold text-hplus-text mb-1.5">Experience</label>
                <textarea v-model="form.experience_summary" rows="4"
                          class="w-full px-3 py-2.5 rounded-lg border border-hplus-border text-sm resize-none
                                 focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold transition"></textarea>
              </div>

              <!-- Education -->
              <div>
                <label class="block text-xs font-semibold text-hplus-text mb-1.5">Education</label>
                <textarea v-model="form.education_summary" rows="3"
                          class="w-full px-3 py-2.5 rounded-lg border border-hplus-border text-sm resize-none
                                 focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold transition"></textarea>
              </div>
            </div>

            <!-- Action buttons -->
            <div class="flex items-center gap-3 mt-8 pt-6 border-t border-hplus-border">
              <button @click="resetForm"
                      class="flex-1 py-3 rounded-xl text-sm font-semibold text-slate-600 bg-slate-100
                             hover:bg-slate-200 transition-all duration-200">
                Cancel
              </button>
              <button @click="handleSave" :disabled="saving"
                      class="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold
                             bg-hplus-gold text-hplus-navy shadow-md shadow-hplus-gold/25
                             hover:bg-amber-400 hover:shadow-lg active:scale-[0.98]
                             disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200">
                <template v-if="saving">
                  <div class="flex gap-1.5">
                    <div class="w-2 h-2 rounded-full bg-hplus-navy/60 pulse-dot"></div>
                    <div class="w-2 h-2 rounded-full bg-hplus-navy/60 pulse-dot"></div>
                    <div class="w-2 h-2 rounded-full bg-hplus-navy/60 pulse-dot"></div>
                  </div>
                  Saving...
                </template>
                <template v-else>
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                  </svg>
                  Save Candidate to Pipeline
                </template>
              </button>
            </div>
          </div>

          <!-- Raw JSON collapsible -->
          <details class="mt-4 bg-white rounded-2xl border border-hplus-border shadow-sm">
            <summary class="px-6 py-3 text-xs font-semibold text-slate-500 cursor-pointer hover:text-hplus-text transition">
              View Raw Extraction JSON
            </summary>
            <pre class="px-6 pb-4 text-xs text-slate-600 overflow-x-auto max-h-64 overflow-y-auto">{{ JSON.stringify(rawJson, null, 2) }}</pre>
          </details>
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
