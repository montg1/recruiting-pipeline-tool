<script setup>
/**
 * CandidateCard — a draggable card on the Kanban board.
 * Shows candidate name, email, source badge, and score if available.
 */
const props = defineProps({
  candidate: { type: Object, required: true },
  application: { type: Object, required: true },
})

const emit = defineEmits(['dragstart'])

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
}

function formatDate(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
</script>

<template>
  <div
    draggable="true"
    @dragstart="onDragStart"
    @dragend="onDragEnd"
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
  </div>
</template>
