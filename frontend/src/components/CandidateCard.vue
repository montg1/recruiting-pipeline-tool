<script setup>
/**
 * CandidateCard — a draggable card on the Kanban board.
 * Shows candidate name, email, source badge, and score if available.
 */
const props = defineProps({
  candidate: { type: Object, required: true },
  application: { type: Object, required: true },
})

const emit = defineEmits(['dragstart', 'open'])

let isDragging = false

const sourceColors = {
  LinkedIn: 'bg-blue-100 text-blue-700',
  Referral: 'bg-emerald-100 text-emerald-700',
  n8n_scrape: 'bg-purple-100 text-purple-700',
}

function getSourceClass(source) {
  return sourceColors[source] || 'bg-slate-100 text-slate-600'
}

function getInitials(name) {
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

function onDragStart(event) {
  isDragging = true
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData(
    'application/json',
    JSON.stringify({
      candidateId: props.candidate.id,
      appId: props.application.id,
      fromStageId: props.application.current_stage_id,
    })
  )
  event.target.classList.add('drag-ghost')
  emit('dragstart')
}

function onDragEnd(event) {
  event.target.classList.remove('drag-ghost')
  setTimeout(() => { isDragging = false }, 100)
}

function handleClick() {
  if (!isDragging) emit('open', props.candidate)
}

function formatDate(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function formatRelative(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = d - now
  const diffDays = Math.floor(diffMs / 86400000)
  const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
  if (diffDays < 0) return `${formatDate(dateStr)} ${time}`
  if (diffDays === 0) return `Today ${time}`
  if (diffDays === 1) return `Tomorrow ${time}`
  return `${formatDate(dateStr)} ${time}`
}
</script>

<template>
  <div
    draggable="true"
    @dragstart="onDragStart"
    @dragend="onDragEnd"
    @click="handleClick"
    class="group bg-white rounded-xl p-4 shadow-sm border border-hplus-border
           hover:shadow-md hover:border-hplus-gold/30
           transition-all duration-200 cursor-grab active:cursor-grabbing"
  >
    <!-- Header: Avatar + Name -->
    <div class="flex items-start gap-3">
      <div
        class="w-10 h-10 rounded-full flex-shrink-0 flex items-center justify-center
               bg-gradient-to-br from-hplus-gold to-amber-500 text-hplus-navy
               text-xs font-bold shadow-sm"
      >
        {{ getInitials(candidate.full_name) }}
      </div>
      <div class="min-w-0 flex-1">
        <h4 class="text-sm font-semibold text-hplus-text truncate leading-tight">
          {{ candidate.full_name }}
        </h4>
        <p class="text-xs text-hplus-text-muted truncate mt-0.5">
          {{ candidate.email }}
        </p>
      </div>
    </div>

    <!-- Meta row -->
    <div class="mt-3 flex items-center justify-between gap-2">
      <span
        v-if="candidate.source"
        :class="getSourceClass(candidate.source)"
        class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider"
      >
        {{ candidate.source }}
      </span>
      <span class="text-[10px] text-hplus-text-muted font-medium">
        {{ formatDate(application.applied_at) }}
      </span>
    </div>

    <!-- Score badge (if resume was scored) -->
    <div
      v-if="application.resume_scores?.length"
      class="mt-2 flex items-center gap-1.5"
    >
      <div class="flex items-center gap-1 px-2 py-1 rounded-lg bg-amber-50 border border-amber-200">
        <svg class="w-3 h-3 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
        </svg>
        <span class="text-[10px] font-bold text-amber-700">
          {{ Number(application.resume_scores[0].overall_score).toFixed(1) }}
        </span>
      </div>
    </div>

    <!-- Rejected reason -->
    <div
      v-if="application.rejected_reason"
      class="mt-2 px-2 py-1.5 rounded-lg bg-red-50 border border-red-100"
    >
      <p class="text-[10px] text-red-600 leading-relaxed line-clamp-2">
        {{ application.rejected_reason }}
      </p>
    </div>

    <!-- Interview / Google Meet -->
    <div v-if="application.next_interview_at" class="mt-2">
      <a v-if="application.google_meet_link"
         :href="application.google_meet_link" target="_blank" rel="noopener"
         @click.stop
         class="flex items-center gap-2 px-2.5 py-1.5 rounded-lg
                bg-blue-50 border border-blue-200
                hover:bg-blue-100 hover:border-blue-300
                transition-all duration-150 group/meet">
        <svg class="w-3.5 h-3.5 text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
        </svg>
        <span class="text-[10px] font-semibold text-blue-600 group-hover/meet:text-blue-700">Join Meeting</span>
        <span class="ml-auto text-[9px] text-blue-400 font-medium">{{ formatRelative(application.next_interview_at) }}</span>
      </a>
      <div v-else class="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-violet-50 border border-violet-200">
        <svg class="w-3.5 h-3.5 text-violet-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
        </svg>
        <span class="text-[10px] font-medium text-violet-600">{{ formatRelative(application.next_interview_at) }}</span>
      </div>
    </div>
  </div>
</template>
