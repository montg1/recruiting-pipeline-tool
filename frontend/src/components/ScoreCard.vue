<script setup>
/**
 * ScoreCard.vue — Displays AI evaluation results from n8n/Claude
 * Adapts to the n8n response shape: evaluation[0].output
 */
import { computed } from 'vue'

const props = defineProps({
  result: { type: Object, required: true },
})

// Unwrap the n8n response: evaluation may be an array with .output
const scores = computed(() => {
  const ev = props.result.evaluation
  if (Array.isArray(ev) && ev.length > 0 && ev[0].output) return ev[0].output
  if (ev && typeof ev === 'object' && !Array.isArray(ev)) return ev
  return null
})

const overallScore = computed(() => {
  if (!scores.value) return 0
  const s = scores.value
  return Math.round(((s.skills_score || 0) * 0.4 + (s.experience_score || 0) * 0.4 + (s.culture_score || 0) * 0.2) * 10) / 10
})

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

function overallBg(val) {
  if (val >= 7) return 'from-emerald-500 to-emerald-600'
  if (val >= 5) return 'from-amber-500 to-amber-600'
  return 'from-red-500 to-red-600'
}
</script>

<template>
  <div v-if="scores" class="space-y-6">
    <!-- Header with Overall Score -->
    <div class="flex items-start gap-6">
      <div class="flex-shrink-0">
        <div class="w-24 h-24 rounded-2xl bg-gradient-to-br shadow-lg flex flex-col items-center justify-center text-white"
             :class="overallBg(overallScore)">
          <span class="text-3xl font-black leading-none">{{ overallScore }}</span>
          <span class="text-[10px] font-semibold opacity-80 mt-0.5">/ 10</span>
        </div>
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="text-lg font-bold text-hplus-text">AI Evaluation</h3>
        <p class="text-sm text-hplus-text-muted mt-1">
          Matched against: <span class="font-semibold text-hplus-navy">{{ result.job_title }}</span>
        </p>
        <p class="text-xs text-slate-400 mt-0.5">
          Resume: {{ result.resume_filename }} ({{ result.resume_text_length }} chars extracted)
        </p>
      </div>
    </div>

    <!-- Score Cards Row -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div v-for="item in [
        { label: 'Skills Fit', score: scores.skills_score, reasoning: scores.skills_reasoning },
        { label: 'Experience Fit', score: scores.experience_score, reasoning: scores.experience_reasoning },
        { label: 'Culture Fit', score: scores.culture_score, reasoning: scores.culture_reasoning },
      ]" :key="item.label"
           class="rounded-xl border p-4 transition-all duration-200 hover:shadow-md"
           :class="scoreBg(item.score)">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-bold uppercase tracking-wider text-slate-500">{{ item.label }}</span>
          <span class="text-2xl font-black" :class="scoreColor(item.score)">{{ item.score }}</span>
        </div>
        <!-- Score bar -->
        <div class="w-full h-1.5 rounded-full bg-slate-200 mb-3">
          <div class="h-1.5 rounded-full transition-all duration-500"
               :class="item.score >= 7 ? 'bg-emerald-500' : item.score >= 5 ? 'bg-amber-500' : 'bg-red-400'"
               :style="{ width: `${(item.score / 10) * 100}%` }"></div>
        </div>
        <p v-if="item.reasoning" class="text-xs text-slate-600 leading-relaxed whitespace-pre-wrap">{{ item.reasoning }}</p>
      </div>
    </div>

    <!-- Key Strengths -->
    <div v-if="scores.key_strengths && scores.key_strengths.length" class="bg-white rounded-xl border border-hplus-border p-5">
      <h4 class="text-sm font-bold text-hplus-text mb-3 flex items-center gap-2">
        <svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
        </svg>
        Key Strengths
      </h4>
      <ul class="space-y-2">
        <li v-for="(s, i) in scores.key_strengths" :key="i"
            class="flex items-start gap-2 text-sm text-slate-700">
          <span class="flex-shrink-0 w-5 h-5 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center text-[10px] font-bold mt-0.5">{{ i + 1 }}</span>
          <span class="leading-relaxed">{{ s }}</span>
        </li>
      </ul>
    </div>

    <!-- Prescreen Questions -->
    <div v-if="scores.prescreen_questions && scores.prescreen_questions.length" class="bg-white rounded-xl border border-hplus-border p-5">
      <h4 class="text-sm font-bold text-hplus-text mb-3 flex items-center gap-2">
        <svg class="w-4 h-4 text-hplus-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        Recommended Prescreen Questions
      </h4>
      <ol class="space-y-3">
        <li v-for="(q, i) in scores.prescreen_questions" :key="i"
            class="flex items-start gap-3 text-sm text-slate-700">
          <span class="flex-shrink-0 w-6 h-6 rounded-lg bg-hplus-gold/10 text-hplus-gold flex items-center justify-center text-xs font-bold mt-0.5">Q{{ i + 1 }}</span>
          <span class="leading-relaxed">{{ q }}</span>
        </li>
      </ol>
    </div>
  </div>

  <!-- Fallback if scores cannot be parsed -->
  <div v-else class="p-6 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-700">
    <p class="font-semibold">Could not parse the AI evaluation.</p>
    <pre class="mt-2 text-xs overflow-x-auto">{{ JSON.stringify(result.evaluation, null, 2) }}</pre>
  </div>
</template>
