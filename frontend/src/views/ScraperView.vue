<script setup>
/**
 * ScraperView — Module 1: JD-driven Candidate Discovery
 * Flow: Job/JD + sources → AI-ranked shortlist → HR selects → push to Tracker.
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getJobs, searchFromJD, approveLeads } from '@/services/api'

const router = useRouter()

/* ---- State ---- */
const step = ref(1) // 1 = input, 2 = shortlist review
const jobs = ref([])
const selectedJobId = ref(null)
const jdText = ref('')
const sources = ref({ github: true, linkedin: true })
const perSource = ref(10)

const searching = ref(false)
const approving = ref(false)
const error = ref(null)
const notification = ref(null)

const result = ref(null)          // CandidateSearchResponse
const selected = ref(new Set())   // indices of chosen leads

/* ---- Derived ---- */
const chosenSources = computed(() => Object.keys(sources.value).filter(k => sources.value[k]))
const canSearch = computed(() =>
  chosenSources.value.length > 0 && (jdText.value.trim().length > 20 || selectedJobId.value != null)
)
const leads = computed(() => result.value?.results || [])
const isPartial = computed(() => result.value?.status === 'partial')
const allSelected = computed(() => leads.value.length > 0 && selected.value.size === leads.value.length)

/* ---- Load jobs for the dropdown ---- */
onMounted(async () => {
  try {
    const { data } = await getJobs()
    jobs.value = data
  } catch { /* dropdown stays empty; raw JD still works for search */ }
})

function onJobChange() {
  const job = jobs.value.find(j => j.id === selectedJobId.value)
  if (job) {
    // prefill the editable JD box from the job's stored text
    jdText.value = [job.title, job.description, job.requirements].filter(Boolean).join('\n\n')
  }
}

/* ---- Step 1: Search ---- */
async function handleSearch() {
  if (!canSearch.value) return
  searching.value = true
  error.value = null
  try {
    const { data } = await searchFromJD({
      jd_text: jdText.value.trim() || null,
      job_id: selectedJobId.value,
      sources: chosenSources.value,
      per_source: perSource.value,
    })
    result.value = data
    selected.value = new Set()
    step.value = 2
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Search failed. Check API keys (ANTHROPIC / ZENROWS).'
  } finally {
    searching.value = false
  }
}

/* ---- Step 2: selection ---- */
function toggle(i) {
  const s = new Set(selected.value)
  s.has(i) ? s.delete(i) : s.add(i)
  selected.value = s
}
function toggleAll() {
  selected.value = allSelected.value ? new Set() : new Set(leads.value.map((_, i) => i))
}

/* ---- Step 2: Approve → push to tracker ---- */
async function handleApprove() {
  if (selected.value.size === 0) return
  if (selectedJobId.value == null) {
    error.value = 'Select a Job above to push the chosen candidates into.'
    return
  }
  approving.value = true
  error.value = null
  try {
    const payloadLeads = [...selected.value].map(i => {
      const r = leads.value[i]
      return {
        full_name: r.full_name,
        email: r.email || null,
        linkedin_url: r.source === 'LinkedIn' ? r.profile_url : null,
        profile_url: r.profile_url || null,
        source: r.source,
        skills: r.skills || [],
        experience_summary: r.experience_summary || null,
        education_summary: r.education_summary || null,
        match_score: r.match_score,
        reasons: r.reasons || [],
      }
    })
    const { data } = await approveLeads({
      job_id: selectedJobId.value,
      leads: payloadLeads,
      search_id: result.value?.id || null,
    })
    showNotification(`Pushed ${data.created} candidate(s) to the pipeline` +
      (data.skipped ? ` · ${data.skipped} already existed` : ''))
    setTimeout(() => router.push('/'), 1800)
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Failed to push candidates.'
  } finally {
    approving.value = false
  }
}

/* ---- Helpers ---- */
function resetSearch() {
  step.value = 1
  result.value = null
  selected.value = new Set()
  error.value = null
}
function showNotification(msg) {
  notification.value = msg
  setTimeout(() => { notification.value = null }, 3500)
}

function verdictClass(verdict) {
  return {
    Strong:   'bg-emerald-50 text-emerald-700 border-emerald-200',
    Possible: 'bg-amber-50 text-amber-700 border-amber-200',
    Weak:     'bg-slate-100 text-slate-500 border-slate-200',
  }[verdict] || 'bg-slate-100 text-slate-500 border-slate-200'
}
function scoreColor(s) {
  if (s >= 75) return 'text-emerald-600'
  if (s >= 50) return 'text-amber-600'
  return 'text-slate-400'
}
</script>

<template>
  <div class="min-h-[calc(100vh-4rem)]">
    <!-- Header -->
    <div class="bg-white border-b border-hplus-border sticky top-16 z-30">
      <div class="px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-hplus-text tracking-tight">Candidate Discovery</h1>
          <p class="text-sm text-hplus-text-muted mt-0.5">
            Find &amp; rank candidates from a job description across multiple sources
          </p>
        </div>
        <div class="hidden sm:flex items-center gap-3">
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all"
                 :class="step >= 1 ? 'bg-hplus-gold text-hplus-navy' : 'bg-slate-200 text-slate-500'">1</div>
            <span class="text-xs font-medium" :class="step >= 1 ? 'text-hplus-text' : 'text-slate-400'">JD &amp; Sources</span>
          </div>
          <div class="w-8 h-px" :class="step >= 2 ? 'bg-hplus-gold' : 'bg-slate-200'"></div>
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all"
                 :class="step >= 2 ? 'bg-hplus-gold text-hplus-navy' : 'bg-slate-200 text-slate-500'">2</div>
            <span class="text-xs font-medium" :class="step >= 2 ? 'text-hplus-text' : 'text-slate-400'">Review &amp; Push</span>
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

      <Transition name="fade" mode="out-in">
        <!-- ============ STEP 1: JD + sources ============ -->
        <div v-if="step === 1" key="step1">
          <div class="bg-white rounded-2xl border border-hplus-border shadow-sm p-6 sm:p-8">
            <h2 class="text-lg font-bold text-hplus-text mb-1">Job Description</h2>
            <p class="text-sm text-hplus-text-muted mb-6">Pick an open job or paste a JD. The AI builds the search queries.</p>

            <!-- Job dropdown -->
            <div class="mb-5">
              <label class="block text-xs font-semibold text-hplus-text mb-1.5">Open Job (candidates get pushed here on approval)</label>
              <select v-model="selectedJobId" @change="onJobChange"
                      class="w-full px-3 py-2.5 rounded-lg border border-hplus-border text-sm bg-white
                             focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold transition">
                <option :value="null">— None (search by raw JD only) —</option>
                <option v-for="j in jobs" :key="j.id" :value="j.id">{{ j.title }}<span v-if="j.department"> · {{ j.department }}</span></option>
              </select>
            </div>

            <!-- JD textarea -->
            <div class="mb-6">
              <label class="block text-xs font-semibold text-hplus-text mb-1.5">JD / Criteria (skills, experience, role)</label>
              <textarea v-model="jdText" rows="8"
                        placeholder="Paste the job description here — Thai or English…"
                        class="w-full px-4 py-3 rounded-xl border border-hplus-border bg-slate-50/50 text-sm text-hplus-text
                               placeholder-slate-400 resize-none focus:outline-none focus:ring-2 focus:ring-hplus-gold/40
                               focus:border-hplus-gold transition"></textarea>
            </div>

            <!-- Sources -->
            <div class="mb-6">
              <label class="block text-xs font-semibold text-hplus-text mb-2">Sources to search</label>
              <div class="flex flex-wrap gap-3">
                <label v-for="src in [{k:'github',label:'GitHub'},{k:'linkedin',label:'LinkedIn'}]" :key="src.k"
                       class="flex items-center gap-2 px-4 py-2.5 rounded-xl border cursor-pointer transition-all"
                       :class="sources[src.k] ? 'border-hplus-gold bg-hplus-gold/10 text-hplus-navy' : 'border-hplus-border text-slate-500 hover:border-slate-300'">
                  <input type="checkbox" v-model="sources[src.k]" class="accent-hplus-gold" />
                  <span class="text-sm font-medium">{{ src.label }}</span>
                </label>
                <div class="flex items-center gap-2 ml-auto">
                  <label class="text-xs text-slate-500">per source</label>
                  <input v-model.number="perSource" type="number" min="1" max="25"
                         class="w-16 px-2 py-1.5 rounded-lg border border-hplus-border text-sm text-center" />
                </div>
              </div>
            </div>

            <button @click="handleSearch" :disabled="!canSearch || searching"
                    class="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold transition-all duration-200
                           disabled:opacity-50 disabled:cursor-not-allowed"
                    :class="canSearch ? 'bg-hplus-gold text-hplus-navy shadow-md shadow-hplus-gold/25 hover:bg-amber-400 hover:shadow-lg active:scale-[0.98]' : 'bg-slate-200 text-slate-500'">
              <template v-if="searching">
                <div class="flex gap-1.5">
                  <div class="w-2 h-2 rounded-full bg-hplus-navy/60 pulse-dot"></div>
                  <div class="w-2 h-2 rounded-full bg-hplus-navy/60 pulse-dot"></div>
                  <div class="w-2 h-2 rounded-full bg-hplus-navy/60 pulse-dot"></div>
                </div>
                Searching &amp; ranking…
              </template>
              <template v-else>
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                </svg>
                Find Candidates
              </template>
            </button>
          </div>
        </div>

        <!-- ============ STEP 2: Shortlist ============ -->
        <div v-else key="step2">
          <!-- Criteria summary -->
          <div class="bg-white rounded-2xl border border-hplus-border shadow-sm p-5 mb-4">
            <div class="flex items-center justify-between mb-3">
              <h2 class="text-lg font-bold text-hplus-text">Ranked Shortlist <span class="text-sm font-normal text-slate-400">({{ leads.length }})</span></h2>
              <button @click="resetSearch" class="text-xs font-medium text-slate-500 hover:text-hplus-navy px-3 py-1.5 rounded-lg hover:bg-slate-100 transition">New Search</button>
            </div>
            <div v-if="result?.criteria" class="flex flex-wrap gap-1.5">
              <span v-if="result.criteria.position" class="px-2.5 py-1 rounded-md bg-hplus-navy/5 text-hplus-navy text-xs font-medium">{{ result.criteria.position }}</span>
              <span v-for="s in (result.criteria.must_have_skills || [])" :key="s" class="px-2.5 py-1 rounded-md bg-slate-100 text-slate-600 text-xs">{{ s }}</span>
              <span v-if="result.criteria.location" class="px-2.5 py-1 rounded-md bg-slate-100 text-slate-600 text-xs">📍 {{ result.criteria.location }}</span>
            </div>
            <details v-if="result?.queries" class="mt-3">
              <summary class="text-xs text-slate-400 cursor-pointer hover:text-slate-600">AI-generated search queries</summary>
              <div class="mt-2 space-y-1">
                <div v-for="(q, src) in result.queries" :key="src" class="text-xs">
                  <span class="font-semibold text-slate-500">{{ src }}:</span>
                  <code class="text-slate-600 bg-slate-50 px-1.5 py-0.5 rounded break-all">{{ q }}</code>
                </div>
              </div>
            </details>
            <div v-if="isPartial" class="mt-3 text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              ⚠️ AI ranking was unavailable — leads are shown unranked. Check your LLM provider (ANTHROPIC_API_KEY or Ollama).
            </div>
          </div>

          <!-- Select-all bar -->
          <div v-if="leads.length" class="flex items-center justify-between px-1 mb-3">
            <label class="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
              <input type="checkbox" :checked="allSelected" @change="toggleAll" class="accent-hplus-gold" />
              Select all
            </label>
            <span class="text-xs text-slate-400">{{ selected.size }} selected</span>
          </div>

          <!-- Lead cards -->
          <div class="space-y-3">
            <div v-for="(r, i) in leads" :key="r.profile_url || i"
                 @click="toggle(i)"
                 class="bg-white rounded-xl border shadow-sm p-4 cursor-pointer transition-all"
                 :class="selected.has(i) ? 'border-hplus-gold ring-2 ring-hplus-gold/30' : 'border-hplus-border hover:border-slate-300'">
              <div class="flex items-start gap-3">
                <input type="checkbox" :checked="selected.has(i)" @click.stop="toggle(i)" class="mt-1 accent-hplus-gold" />

                <!-- Score -->
                <div class="flex flex-col items-center w-12 flex-shrink-0">
                  <span class="text-xl font-bold leading-none" :class="scoreColor(r.match_score)">{{ r.match_score }}</span>
                  <span class="text-[10px] text-slate-400 mt-0.5">/ 100</span>
                </div>

                <!-- Body -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <h3 class="text-sm font-bold text-hplus-text truncate">{{ r.full_name }}</h3>
                    <span class="px-2 py-0.5 rounded text-[10px] font-semibold border" :class="verdictClass(r.verdict)">{{ r.verdict }}</span>
                    <span class="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-500">{{ r.source }}</span>
                  </div>
                  <p v-if="r.headline" class="text-xs text-slate-500 mt-0.5 line-clamp-2">{{ r.headline }}</p>

                  <ul v-if="r.reasons?.length" class="mt-2 space-y-0.5">
                    <li v-for="(reason, k) in r.reasons" :key="k" class="text-xs text-emerald-700 flex gap-1.5">
                      <span class="text-emerald-400">+</span><span>{{ reason }}</span>
                    </li>
                  </ul>
                  <p v-if="r.missing?.length" class="text-xs text-red-400 mt-1">missing: {{ r.missing.join(', ') }}</p>

                  <a v-if="r.profile_url" :href="r.profile_url" target="_blank" @click.stop
                     class="inline-flex items-center gap-1 text-xs text-hplus-navy hover:underline mt-2">
                    View profile
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
                  </a>
                </div>
              </div>
            </div>

            <div v-if="!leads.length" class="text-center py-12 text-slate-400 text-sm">
              No candidates found. Try broadening the JD or enabling more sources.
            </div>
          </div>

          <!-- Approve bar -->
          <div v-if="leads.length" class="sticky bottom-4 mt-5 bg-white/85 backdrop-blur rounded-xl border border-hplus-border shadow-lg p-3 space-y-2.5">
            <!-- Target job picker (required to push) -->
            <div class="flex items-center gap-2">
              <label class="text-xs font-semibold text-hplus-text whitespace-nowrap">Push to job</label>
              <select v-model="selectedJobId"
                      class="flex-1 px-3 py-2 rounded-lg border text-sm bg-white focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold transition"
                      :class="selectedJobId == null ? 'border-amber-300 bg-amber-50/40' : 'border-hplus-border'">
                <option :value="null" disabled>— select an open job —</option>
                <option v-for="j in jobs" :key="j.id" :value="j.id">{{ j.title }}<span v-if="j.department"> · {{ j.department }}</span></option>
              </select>
            </div>
            <p v-if="!jobs.length" class="text-xs text-amber-600">No open jobs found — create one in the tracker first.</p>
            <p v-else-if="selectedJobId == null" class="text-xs text-amber-600">เลือก job ที่จะ push candidate เข้าก่อนกด Approve</p>

            <button @click="handleApprove" :disabled="selected.size === 0 || approving || selectedJobId == null"
                    class="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl text-sm font-semibold shadow-lg transition-all
                           disabled:opacity-50 disabled:cursor-not-allowed bg-hplus-gold text-hplus-navy hover:bg-amber-400 active:scale-[0.99]">
              <template v-if="approving">
                <div class="flex gap-1.5">
                  <div class="w-2 h-2 rounded-full bg-hplus-navy/60 pulse-dot"></div>
                  <div class="w-2 h-2 rounded-full bg-hplus-navy/60 pulse-dot"></div>
                  <div class="w-2 h-2 rounded-full bg-hplus-navy/60 pulse-dot"></div>
                </div>
                Pushing…
              </template>
              <template v-else>
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                Approve {{ selected.size }} &amp; Push to Pipeline
              </template>
            </button>
          </div>
        </div>
      </Transition>
    </div>

    <!-- Toast -->
    <Transition name="fade">
      <div v-if="notification"
           class="fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-xl shadow-xl border backdrop-blur-sm bg-emerald-50/90 border-emerald-200 text-emerald-700">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
        <span class="text-sm font-medium">{{ notification }}</span>
      </div>
    </Transition>
  </div>
</template>
