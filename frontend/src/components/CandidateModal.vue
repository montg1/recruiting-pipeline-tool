<script setup>
/**
 * CandidateModal.vue — Slide-over panel for viewing, editing, and deleting a candidate.
 *
 * View Mode: Displays all candidate details, stage, source, and AI Resume Scores.
 * Edit Mode: Toggled via 'Edit' button — lets HR update Name, Email, Phone.
 * Delete:    Red button with native confirm dialog before emitting delete event.
 */
import { ref, watch, computed } from 'vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  candidate: { type: Object, default: null },
})

const emit = defineEmits(['close', 'update', 'delete'])

/* ---- State ---- */
const editing = ref(false)
const saving = ref(false)
const errorMsg = ref('')
const form = ref({ full_name: '', email: '', phone: '' })

/* ---- Reset when modal opens ---- */
watch(
  () => props.show,
  (val) => {
    if (val && props.candidate) {
      form.value = {
        full_name: props.candidate.full_name || '',
        email: props.candidate.email || '',
        phone: props.candidate.phone || '',
      }
      editing.value = false
      errorMsg.value = ''
    }
  }
)

/* ---- Computed helpers ---- */
const currentApp = computed(() => {
  if (!props.candidate?.applications?.length) return null
  return props.candidate.applications.find(a => a.is_active) || props.candidate.applications[0]
})

const currentStageName = computed(() => currentApp.value?.current_stage?.name || '—')

const aiScores = computed(() => {
  if (!props.candidate?.parsed_data?.ai_evaluation) return null
  return props.candidate.parsed_data.ai_evaluation
})

const overallScore = computed(() => {
  if (!aiScores.value) return null
  const s = aiScores.value
  return Math.round(((s.skills_score || 0) * 0.4 + (s.experience_score || 0) * 0.4 + (s.culture_score || 0) * 0.2) * 10) / 10
})

/* ---- Source badge colors ---- */
const sourceColors = {
  LinkedIn: 'bg-blue-100 text-blue-700',
  Referral: 'bg-emerald-100 text-emerald-700',
  'Job Board': 'bg-orange-100 text-orange-700',
  n8n_scrape: 'bg-purple-100 text-purple-700',
  'AI Resume Screen': 'bg-amber-100 text-amber-700',
}

function getSourceClass(source) {
  return sourceColors[source] || 'bg-slate-100 text-slate-600'
}

function getInitials(name) {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

function scoreColor(val) {
  if (val >= 7) return 'text-emerald-600'
  if (val >= 5) return 'text-amber-600'
  return 'text-red-500'
}

function scoreBg(val) {
  if (val >= 7) return 'bg-emerald-50 border-emerald-200'
  if (val >= 5) return 'bg-amber-50 border-amber-200'
  return 'bg-red-50 border-red-200'
}

function scoreBarColor(val) {
  if (val >= 7) return 'bg-emerald-500'
  if (val >= 5) return 'bg-amber-500'
  return 'bg-red-400'
}

function overallGradient(val) {
  if (val >= 7) return 'from-emerald-500 to-emerald-600'
  if (val >= 5) return 'from-amber-500 to-amber-600'
  return 'from-red-500 to-red-600'
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

/* ---- Actions ---- */
function toggleEdit() {
  editing.value = !editing.value
  errorMsg.value = ''
  if (editing.value && props.candidate) {
    form.value = {
      full_name: props.candidate.full_name || '',
      email: props.candidate.email || '',
      phone: props.candidate.phone || '',
    }
  }
}

async function handleSave() {
  if (!form.value.full_name.trim() || !form.value.email.trim()) {
    errorMsg.value = 'Name and email are required.'
    return
  }
  saving.value = true
  errorMsg.value = ''
  try {
    emit('update', props.candidate.id, { ...form.value })
    editing.value = false
  } catch (e) {
    errorMsg.value = 'Failed to update candidate.'
  } finally {
    saving.value = false
  }
}

function handleDelete() {
  if (window.confirm(`Are you sure you want to delete "${props.candidate.full_name}"? This action cannot be undone.`)) {
    emit('delete', props.candidate.id)
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="show && candidate" class="fixed inset-0 z-50 flex">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="emit('close')" />

        <!-- Slide-over Panel -->
        <div class="relative ml-auto w-full max-w-lg bg-white shadow-2xl flex flex-col
                    animate-[slideInRight_0.3s_ease]">

          <!-- ===== HEADER ===== -->
          <div class="flex items-center justify-between px-6 py-5 border-b border-hplus-border">
            <div class="flex items-center gap-3">
              <div class="w-12 h-12 rounded-full flex-shrink-0 flex items-center justify-center
                          bg-gradient-to-br from-hplus-gold to-amber-500 text-hplus-navy
                          text-sm font-bold shadow-md">
                {{ getInitials(candidate.full_name) }}
              </div>
              <div>
                <h2 class="text-lg font-bold text-hplus-text">{{ candidate.full_name }}</h2>
                <div class="flex items-center gap-2 mt-0.5">
                  <span v-if="candidate.source"
                        :class="getSourceClass(candidate.source)"
                        class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider">
                    {{ candidate.source }}
                  </span>
                  <span class="text-xs text-hplus-text-muted">
                    Added {{ formatDate(candidate.created_at) }}
                  </span>
                </div>
              </div>
            </div>
            <button @click="emit('close')" class="p-2 rounded-lg hover:bg-slate-100 transition">
              <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- ===== BODY ===== -->
          <div class="flex-1 overflow-y-auto px-6 py-5 space-y-6">

            <!-- Error message -->
            <div v-if="errorMsg" class="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-600">
              {{ errorMsg }}
            </div>

            <!-- ---- VIEW MODE ---- -->
            <template v-if="!editing">
              <!-- Contact Details -->
              <div class="bg-slate-50 rounded-xl border border-slate-200 p-4 space-y-3">
                <h3 class="text-xs font-bold text-hplus-text-muted uppercase tracking-wider mb-2">Contact Details</h3>
                <div class="flex items-center gap-3">
                  <svg class="w-4 h-4 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                  </svg>
                  <span class="text-sm text-hplus-text">{{ candidate.email }}</span>
                </div>
                <div class="flex items-center gap-3">
                  <svg class="w-4 h-4 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/>
                  </svg>
                  <span class="text-sm text-hplus-text">{{ candidate.phone || 'Not provided' }}</span>
                </div>
                <div v-if="candidate.linkedin_url" class="flex items-center gap-3">
                  <svg class="w-4 h-4 text-blue-500 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
                  </svg>
                  <a :href="candidate.linkedin_url" target="_blank" class="text-sm text-blue-600 hover:underline truncate">
                    {{ candidate.linkedin_url }}
                  </a>
                </div>
              </div>

              <!-- Pipeline Stage -->
              <div v-if="currentApp" class="bg-slate-50 rounded-xl border border-slate-200 p-4">
                <h3 class="text-xs font-bold text-hplus-text-muted uppercase tracking-wider mb-3">Pipeline Status</h3>
                <div class="flex items-center gap-3">
                  <div class="w-3 h-3 rounded-full"
                       :class="currentApp.current_stage?.stage_type === 'success' ? 'bg-emerald-500'
                              : currentApp.current_stage?.stage_type === 'rejected' ? 'bg-red-500'
                              : 'bg-blue-500'"></div>
                  <span class="text-sm font-semibold text-hplus-text">{{ currentStageName }}</span>
                  <span class="text-xs text-hplus-text-muted ml-auto">
                    Applied {{ formatDate(currentApp.applied_at) }}
                  </span>
                </div>
                <div v-if="currentApp.rejected_reason" class="mt-2 px-3 py-2 rounded-lg bg-red-50 border border-red-100">
                  <p class="text-xs text-red-600">{{ currentApp.rejected_reason }}</p>
                </div>
              </div>

              <!-- ===== AI RESUME SCORES ===== -->
              <div v-if="aiScores" class="space-y-4">
                <div class="flex items-center gap-2">
                  <svg class="w-4 h-4 text-hplus-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                  </svg>
                  <h3 class="text-xs font-bold text-hplus-text-muted uppercase tracking-wider">AI Evaluation</h3>
                  <div v-if="overallScore !== null"
                       class="ml-auto w-10 h-10 rounded-xl bg-gradient-to-br shadow-sm flex items-center justify-center text-white text-sm font-black"
                       :class="overallGradient(overallScore)">
                    {{ overallScore }}
                  </div>
                </div>

                <!-- Score cards -->
                <div class="grid grid-cols-3 gap-3">
                  <div v-for="item in [
                    { label: 'Skills', score: aiScores.skills_score },
                    { label: 'Experience', score: aiScores.experience_score },
                    { label: 'Culture', score: aiScores.culture_score },
                  ]" :key="item.label"
                       class="rounded-xl border p-3 text-center transition-all"
                       :class="scoreBg(item.score)">
                    <span class="text-[10px] font-bold uppercase tracking-wider text-slate-500">{{ item.label }}</span>
                    <div class="text-xl font-black mt-1" :class="scoreColor(item.score)">{{ item.score }}</div>
                    <div class="w-full h-1 rounded-full bg-slate-200 mt-2">
                      <div class="h-1 rounded-full transition-all"
                           :class="scoreBarColor(item.score)"
                           :style="{ width: `${(item.score / 10) * 100}%` }"></div>
                    </div>
                  </div>
                </div>

                <!-- Reasoning -->
                <div v-if="aiScores.skills_reasoning || aiScores.experience_reasoning || aiScores.culture_reasoning"
                     class="bg-white rounded-xl border border-hplus-border p-4 space-y-3">
                  <div v-if="aiScores.skills_reasoning">
                    <p class="text-[10px] font-bold text-slate-400 uppercase">Skills</p>
                    <p class="text-xs text-slate-600 leading-relaxed mt-0.5">{{ aiScores.skills_reasoning }}</p>
                  </div>
                  <div v-if="aiScores.experience_reasoning">
                    <p class="text-[10px] font-bold text-slate-400 uppercase">Experience</p>
                    <p class="text-xs text-slate-600 leading-relaxed mt-0.5">{{ aiScores.experience_reasoning }}</p>
                  </div>
                  <div v-if="aiScores.culture_reasoning">
                    <p class="text-[10px] font-bold text-slate-400 uppercase">Culture</p>
                    <p class="text-xs text-slate-600 leading-relaxed mt-0.5">{{ aiScores.culture_reasoning }}</p>
                  </div>
                </div>

                <!-- Key Strengths -->
                <div v-if="aiScores.key_strengths?.length" class="bg-white rounded-xl border border-hplus-border p-4">
                  <h4 class="text-xs font-bold text-hplus-text-muted uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <svg class="w-3.5 h-3.5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                    </svg>
                    Key Strengths
                  </h4>
                  <ul class="space-y-1.5">
                    <li v-for="(s, i) in aiScores.key_strengths" :key="i" class="flex items-start gap-2 text-xs text-slate-600">
                      <span class="flex-shrink-0 w-4 h-4 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center text-[9px] font-bold mt-0.5">{{ i + 1 }}</span>
                      <span class="leading-relaxed">{{ s }}</span>
                    </li>
                  </ul>
                </div>

                <!-- Prescreen Questions -->
                <div v-if="aiScores.prescreen_questions?.length" class="bg-white rounded-xl border border-hplus-border p-4">
                  <h4 class="text-xs font-bold text-hplus-text-muted uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <svg class="w-3.5 h-3.5 text-hplus-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    Prescreen Questions
                  </h4>
                  <ol class="space-y-2">
                    <li v-for="(q, i) in aiScores.prescreen_questions" :key="i" class="flex items-start gap-2 text-xs text-slate-600">
                      <span class="flex-shrink-0 w-5 h-5 rounded-md bg-hplus-gold/10 text-hplus-gold flex items-center justify-center text-[9px] font-bold mt-0.5">Q{{ i + 1 }}</span>
                      <span class="leading-relaxed">{{ q }}</span>
                    </li>
                  </ol>
                </div>
              </div>

              <!-- No AI scores fallback -->
              <div v-else class="bg-slate-50 rounded-xl border border-slate-200 p-4 text-center">
                <svg class="w-8 h-8 mx-auto text-slate-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                        d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                </svg>
                <p class="text-xs text-slate-400 font-medium">No AI evaluation available</p>
                <p class="text-[10px] text-slate-400 mt-0.5">Screen this candidate's resume to generate AI insights</p>
              </div>
            </template>

            <!-- ---- EDIT MODE ---- -->
            <template v-else>
              <div class="space-y-4">
                <!-- Name -->
                <div>
                  <label class="block text-xs font-semibold text-hplus-text-muted uppercase tracking-wider mb-1.5">
                    Full Name *
                  </label>
                  <input v-model="form.full_name" type="text"
                         class="w-full px-3 py-2.5 rounded-lg border border-hplus-border bg-hplus-surface
                                text-sm text-hplus-text placeholder:text-slate-400
                                focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold transition"/>
                </div>

                <!-- Email -->
                <div>
                  <label class="block text-xs font-semibold text-hplus-text-muted uppercase tracking-wider mb-1.5">
                    Email *
                  </label>
                  <input v-model="form.email" type="email"
                         class="w-full px-3 py-2.5 rounded-lg border border-hplus-border bg-hplus-surface
                                text-sm text-hplus-text placeholder:text-slate-400
                                focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold transition"/>
                </div>

                <!-- Phone -->
                <div>
                  <label class="block text-xs font-semibold text-hplus-text-muted uppercase tracking-wider mb-1.5">
                    Phone
                  </label>
                  <input v-model="form.phone" type="tel" placeholder="+66 81 234 5678"
                         class="w-full px-3 py-2.5 rounded-lg border border-hplus-border bg-hplus-surface
                                text-sm text-hplus-text placeholder:text-slate-400
                                focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold transition"/>
                </div>
              </div>
            </template>
          </div>

          <!-- ===== FOOTER ===== -->
          <div class="px-6 py-4 border-t border-hplus-border bg-slate-50">
            <!-- View mode footer -->
            <div v-if="!editing" class="flex items-center gap-3">
              <button @click="handleDelete"
                      class="px-3 py-2 rounded-lg text-xs font-medium text-red-600 hover:bg-red-50 border border-transparent
                             hover:border-red-200 transition-all duration-200">
                <span class="flex items-center gap-1.5">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                  </svg>
                  Delete
                </span>
              </button>

              <div class="flex-1"></div>

              <button @click="emit('close')"
                      class="px-4 py-2 rounded-lg text-sm font-medium text-hplus-text-muted hover:bg-slate-200 transition">
                Close
              </button>
              <button @click="toggleEdit"
                      class="px-5 py-2.5 rounded-lg text-sm font-semibold
                             bg-hplus-navy text-white shadow-sm
                             hover:bg-slate-700 transition-all duration-200">
                <span class="flex items-center gap-1.5">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                  </svg>
                  Edit
                </span>
              </button>
            </div>

            <!-- Edit mode footer -->
            <div v-else class="flex items-center gap-3">
              <button @click="toggleEdit"
                      class="flex-1 py-2.5 rounded-lg text-sm font-medium text-hplus-text-muted hover:bg-slate-200 transition">
                Cancel
              </button>
              <button @click="handleSave" :disabled="saving"
                      class="flex-1 py-2.5 rounded-lg text-sm font-semibold
                             bg-hplus-gold text-hplus-navy shadow-md
                             hover:bg-amber-400 hover:shadow-lg
                             disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200">
                <span v-if="saving" class="flex items-center justify-center gap-2">
                  <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  Saving...
                </span>
                <span v-else>Save Changes</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
</style>
