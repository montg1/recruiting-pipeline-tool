<script setup>
/**
 * DashboardView — Module 3 Kanban Board
 *
 * Displays pipeline columns with draggable candidate cards.
 * Fetches data via Pinia store; calls PATCH endpoint on drop.
 */
import { onMounted, ref, computed, watch } from 'vue'
import { usePipelineStore } from '@/stores/pipeline'
import CandidateCard from '@/components/CandidateCard.vue'
import AddCandidateModal from '@/components/AddCandidateModal.vue'
import CandidateModal from '@/components/CandidateModal.vue'
import { updateCandidate, deleteCandidate, getJobs } from '@/services/api'

const store = usePipelineStore()
const showAddModal = ref(false)
const selectedCandidate = ref(null)
const showCandidateModal = ref(false)
const dragOverStageId = ref(null)
const notification = ref(null)
const showFilters = ref(false)

/* ---- Filters ---- */
const filters = ref({
  job_id: '',
  stage_id: '',
  source: '',
  search: '',
})
const jobs = ref([])
const sources = ['LinkedIn', 'Referral', 'Job Board', 'n8n_scrape', 'AI Resume Screen', 'Website', 'Other']

const hasActiveFilters = computed(() => {
  return filters.value.job_id || filters.value.stage_id || filters.value.source || filters.value.search
})

function clearFilters() {
  filters.value = { job_id: '', stage_id: '', source: '', search: '' }
}

// Debounced auto-apply
let filterTimeout = null
watch(filters, () => {
  clearTimeout(filterTimeout)
  filterTimeout = setTimeout(() => {
    store.fetchCandidates(filters.value)
  }, 300)
}, { deep: true })

onMounted(async () => {
  store.init()
  try {
    const { data } = await getJobs()
    jobs.value = Array.isArray(data) ? data : []
  } catch {
    jobs.value = []
  }
})

/* ---- Stage colors for column headers ---- */
const stageColorMap = {
  1: { bg: 'bg-blue-500',    dot: 'bg-blue-400',   light: 'bg-blue-50',   text: 'text-blue-700' },
  2: { bg: 'bg-violet-500',  dot: 'bg-violet-400', light: 'bg-violet-50', text: 'text-violet-700' },
  3: { bg: 'bg-pink-500',    dot: 'bg-pink-400',   light: 'bg-pink-50',   text: 'text-pink-700' },
  4: { bg: 'bg-orange-500',  dot: 'bg-orange-400', light: 'bg-orange-50', text: 'text-orange-700' },
  5: { bg: 'bg-teal-500',    dot: 'bg-teal-400',   light: 'bg-teal-50',   text: 'text-teal-700' },
  6: { bg: 'bg-emerald-500', dot: 'bg-emerald-400',light: 'bg-emerald-50',text: 'text-emerald-700' },
  7: { bg: 'bg-red-500',     dot: 'bg-red-400',    light: 'bg-red-50',    text: 'text-red-700' },
}

function getStageColors(stageId) {
  return stageColorMap[stageId] || stageColorMap[1]
}

/* ---- Stats ---- */
const totalCandidates = computed(() => store.candidates.length)
const totalApplications = computed(() => {
  let count = 0
  for (const col of Object.values(store.boardColumns)) {
    count += col.cards.length
  }
  return count
})

/* ---- Drag-and-Drop ---- */
function onDragOver(event, stageId) {
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
  dragOverStageId.value = stageId
}

function onDragLeave(event, stageId) {
  // Only clear if truly leaving the column (not entering a child)
  if (!event.currentTarget.contains(event.relatedTarget)) {
    dragOverStageId.value = null
  }
}

async function onDrop(event, stageId) {
  event.preventDefault()
  dragOverStageId.value = null

  try {
    const payload = JSON.parse(event.dataTransfer.getData('application/json'))
    if (payload.fromStageId === stageId) return // same column, no change

    await store.moveApplication(payload.candidateId, payload.appId, stageId)

    const stageName = store.stages.find((s) => s.id === stageId)?.name || 'Unknown'
    showNotification(`Moved to ${stageName}`, 'success')
  } catch (e) {
    console.error('Drop failed:', e)
    showNotification('Failed to move card', 'error')
  }
}

/* ---- Add candidate ---- */
async function handleAddCandidate(formData) {
  try {
    const candidate = await store.addCandidate({
      full_name: formData.full_name,
      email: formData.email,
      phone: formData.phone || null,
      source: formData.source || null,
      linkedin_url: formData.linkedin_url || null,
    })
    // Apply to job
    if (formData.job_id) {
      await store.applyToJob(candidate.id, formData.job_id)
    }
    showAddModal.value = false
    showNotification(`${formData.full_name} added to pipeline`, 'success')
  } catch (e) {
    showNotification(e?.response?.data?.detail || 'Failed to add candidate', 'error')
  }
}

/* ---- Notifications ---- */
function showNotification(message, type = 'success') {
  notification.value = { message, type }
  setTimeout(() => {
    notification.value = null
  }, 3000)
}

/* ---- Candidate modal ---- */
function openCandidateModal(candidate) {
  selectedCandidate.value = candidate
  showCandidateModal.value = true
}

async function handleUpdateCandidate(id, data) {
  try {
    await updateCandidate(id, data)
    // Update local state
    const idx = store.candidates.findIndex(c => c.id === id)
    if (idx !== -1) {
      store.candidates[idx] = { ...store.candidates[idx], ...data }
      selectedCandidate.value = store.candidates[idx]
    }
    showNotification(`${data.full_name || 'Candidate'} updated`, 'success')
  } catch (e) {
    showNotification(e?.response?.data?.detail || 'Failed to update', 'error')
  }
}

async function handleDeleteCandidate(id) {
  try {
    await deleteCandidate(id)
    store.candidates = store.candidates.filter(c => c.id !== id)
    showCandidateModal.value = false
    selectedCandidate.value = null
    showNotification('Candidate deleted', 'success')
  } catch (e) {
    showNotification(e?.response?.data?.detail || 'Failed to delete', 'error')
  }
}
</script>

<template>
  <div class="min-h-[calc(100vh-4rem)]">
    <!-- Header Bar -->
    <div class="bg-white border-b border-hplus-border sticky top-16 z-30">
      <div class="px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold text-hplus-text tracking-tight">
              Recruiting Pipeline
            </h1>
            <p class="text-sm text-hplus-text-muted mt-0.5">
              Drag and drop candidates between stages
            </p>
          </div>

          <div class="flex items-center gap-3">
            <!-- Stats pills -->
            <div class="hidden md:flex items-center gap-2">
              <div class="px-3 py-1.5 rounded-full bg-hplus-gold/10 border border-hplus-gold/20">
                <span class="text-xs font-semibold text-hplus-gold-dark">
                  {{ totalCandidates }} candidates
                </span>
              </div>
              <div class="px-3 py-1.5 rounded-full bg-blue-50 border border-blue-100">
                <span class="text-xs font-semibold text-blue-600">
                  {{ totalApplications }} active
                </span>
              </div>
            </div>

            <!-- Filter toggle -->
            <button
              @click="showFilters = !showFilters"
              class="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200"
              :class="showFilters || hasActiveFilters
                ? 'bg-hplus-navy text-white shadow-sm'
                : 'text-slate-500 hover:bg-slate-100'"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"/>
              </svg>
              Filters
              <span v-if="hasActiveFilters"
                    class="w-2 h-2 rounded-full bg-hplus-gold animate-pulse"></span>
            </button>

            <!-- Add button -->
            <button
              @click="showAddModal = true"
              class="flex items-center gap-2 px-4 py-2.5 rounded-xl
                     bg-hplus-gold text-hplus-navy text-sm font-semibold
                     shadow-md shadow-hplus-gold/25
                     hover:bg-amber-400 hover:shadow-lg hover:shadow-hplus-gold/30
                     active:scale-[0.97]
                     transition-all duration-200"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4" />
              </svg>
              Add Candidate
            </button>
          </div>
        </div>
      </div>

      <!-- ===== Filter Bar ===== -->
      <Transition name="slide-down">
        <div v-if="showFilters" class="border-t border-hplus-border bg-slate-50/80 px-4 sm:px-6 lg:px-8 py-3">
          <div class="flex flex-wrap items-center gap-3">
            <!-- Search -->
            <div class="relative flex-1 min-w-[180px] max-w-xs">
              <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
              </svg>
              <input
                v-model="filters.search"
                type="text"
                placeholder="Search name or email..."
                class="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 bg-white text-sm
                       placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-hplus-gold/40
                       focus:border-hplus-gold transition"
              />
            </div>

            <!-- Job filter -->
            <select
              v-model="filters.job_id"
              class="px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm text-hplus-text
                     focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold transition min-w-[160px]"
            >
              <option value="">All Jobs</option>
              <option v-for="job in jobs" :key="job.id" :value="job.id">{{ job.title }}</option>
            </select>

            <!-- Stage filter -->
            <select
              v-model="filters.stage_id"
              class="px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm text-hplus-text
                     focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold transition min-w-[160px]"
            >
              <option value="">All Stages</option>
              <option v-for="stage in store.stages" :key="stage.id" :value="stage.id">{{ stage.name }}</option>
            </select>

            <!-- Source filter -->
            <select
              v-model="filters.source"
              class="px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm text-hplus-text
                     focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold transition min-w-[140px]"
            >
              <option value="">All Sources</option>
              <option v-for="s in sources" :key="s" :value="s">{{ s }}</option>
            </select>

            <!-- Clear button -->
            <button
              v-if="hasActiveFilters"
              @click="clearFilters"
              class="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium
                     text-red-600 hover:bg-red-50 border border-transparent hover:border-red-200 transition"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
              Clear
            </button>
          </div>
        </div>
      </Transition>
    </div>

    <!-- Loading State -->
    <div v-if="store.loading" class="flex items-center justify-center py-32">
      <div class="text-center">
        <div class="flex justify-center gap-2 mb-4">
          <div class="w-3 h-3 rounded-full bg-hplus-gold pulse-dot"></div>
          <div class="w-3 h-3 rounded-full bg-hplus-gold pulse-dot"></div>
          <div class="w-3 h-3 rounded-full bg-hplus-gold pulse-dot"></div>
        </div>
        <p class="text-sm text-hplus-text-muted font-medium">Loading pipeline...</p>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="store.error" class="flex items-center justify-center py-32">
      <div class="text-center max-w-md">
        <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 flex items-center justify-center">
          <svg class="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <p class="text-hplus-text font-semibold">{{ store.error }}</p>
        <button
          @click="store.init()"
          class="mt-4 px-4 py-2 rounded-lg bg-hplus-navy text-white text-sm font-medium hover:bg-slate-700 transition"
        >
          Retry
        </button>
      </div>
    </div>

    <!-- Kanban Board -->
    <div v-else class="overflow-x-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="flex gap-4 min-w-max pb-4">
        <!-- Column for each stage -->
        <div
          v-for="stage in store.stages"
          :key="stage.id"
          class="w-72 flex-shrink-0 flex flex-col rounded-2xl transition-all duration-200"
          :class="[
            dragOverStageId === stage.id ? 'drag-over' : '',
            stage.is_terminal ? 'opacity-80' : ''
          ]"
          @dragover="onDragOver($event, stage.id)"
          @dragleave="onDragLeave($event, stage.id)"
          @drop="onDrop($event, stage.id)"
        >
          <!-- Column header -->
          <div
            class="flex items-center justify-between px-4 py-3 rounded-t-2xl"
            :class="getStageColors(stage.id).light"
          >
            <div class="flex items-center gap-2">
              <div
                class="w-2.5 h-2.5 rounded-full"
                :class="getStageColors(stage.id).dot"
              ></div>
              <h3
                class="text-sm font-bold"
                :class="getStageColors(stage.id).text"
              >
                {{ stage.name }}
              </h3>
            </div>
            <span
              class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold"
              :class="[getStageColors(stage.id).light, getStageColors(stage.id).text]"
              style="border: 1.5px solid currentColor;"
            >
              {{ store.boardColumns[stage.id]?.cards.length || 0 }}
            </span>
          </div>

          <!-- Cards area -->
          <div
            class="flex-1 bg-slate-50/60 rounded-b-2xl border border-t-0 border-slate-200/60
                   p-2 space-y-2 min-h-[200px] kanban-col overflow-y-auto max-h-[calc(100vh-320px)]"
          >
            <TransitionGroup name="slide-up">
              <CandidateCard
                v-for="card in store.boardColumns[stage.id]?.cards"
                :key="`${card.candidate.id}-${card.application.id}`"
                :candidate="card.candidate"
                :application="card.application"
                @open="openCandidateModal"
              />
            </TransitionGroup>

            <!-- Empty state -->
            <div
              v-if="!store.boardColumns[stage.id]?.cards.length"
              class="flex flex-col items-center justify-center py-8 text-center"
            >
              <div class="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center mb-2">
                <svg class="w-5 h-5 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                        d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <p class="text-xs text-slate-400 font-medium">
                Drop candidates here
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Add Candidate Modal -->
    <AddCandidateModal
      :show="showAddModal"
      @close="showAddModal = false"
      @submit="handleAddCandidate"
    />

    <!-- Candidate Detail Modal -->
    <CandidateModal
      :show="showCandidateModal"
      :candidate="selectedCandidate"
      @close="showCandidateModal = false"
      @update="handleUpdateCandidate"
      @delete="handleDeleteCandidate"
    />

    <!-- Toast Notification -->
    <Transition name="fade">
      <div
        v-if="notification"
        class="fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-xl shadow-xl
               border backdrop-blur-sm"
        :class="notification.type === 'success'
          ? 'bg-emerald-50/90 border-emerald-200 text-emerald-700'
          : 'bg-red-50/90 border-red-200 text-red-700'"
      >
        <svg v-if="notification.type === 'success'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
        </svg>
        <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <span class="text-sm font-medium">{{ notification.message }}</span>
      </div>
    </Transition>
  </div>
</template>
