/**
 * Pipeline store — manages Kanban board state with Pinia.
 *
 * Holds: stages, candidates (with nested applications), loading/error state.
 * Actions: fetch, create candidate, create application, move stage (drag-and-drop).
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getStages,
  getCandidates,
  createCandidate as apiCreateCandidate,
  createApplication as apiCreateApplication,
  updateApplicationStage as apiUpdateStage,
  getCandidate,
} from '@/services/api'

export const usePipelineStore = defineStore('pipeline', () => {
  /* ---- State ---- */
  const stages = ref([])
  const candidates = ref([])
  const loading = ref(false)
  const error = ref(null)

  /* ---- Getters ---- */

  /** Build a map: stageId → [{ candidate, application }] for the Kanban board. */
  const boardColumns = computed(() => {
    const cols = {}
    for (const stage of stages.value) {
      cols[stage.id] = {
        stage,
        cards: [],
      }
    }
    // Walk every candidate's applications and slot them into columns
    for (const candidate of candidates.value) {
      if (!candidate.applications) continue
      for (const app of candidate.applications) {
        if (!app.is_active) continue
        const col = cols[app.current_stage_id]
        if (col) {
          col.cards.push({
            candidate,
            application: app,
          })
        }
      }
    }
    // Sort cards within each column by kanban_position
    for (const col of Object.values(cols)) {
      col.cards.sort((a, b) => a.application.kanban_position - b.application.kanban_position)
    }
    return cols
  })

  /* ---- Actions ---- */

  async function fetchStages() {
    try {
      const { data } = await getStages()
      stages.value = data
    } catch (e) {
      console.error('Failed to fetch stages:', e)
      error.value = 'Failed to load pipeline stages.'
    }
  }

  async function fetchCandidates() {
    loading.value = true
    error.value = null
    try {
      // First fetch list, then get detail (with applications) for each
      const { data: list } = await getCandidates()
      // Fetch details with applications in parallel
      const details = await Promise.all(
        list.map((c) => getCandidate(c.id).then((r) => r.data))
      )
      candidates.value = details
    } catch (e) {
      console.error('Failed to fetch candidates:', e)
      error.value = 'Failed to load candidates.'
    } finally {
      loading.value = false
    }
  }

  async function addCandidate(payload) {
    const { data } = await apiCreateCandidate(payload)
    // Fetch detail to get the full object with applications
    const { data: detail } = await getCandidate(data.id)
    candidates.value.push(detail)
    return detail
  }

  async function applyToJob(candidateId, jobId) {
    const { data: app } = await apiCreateApplication(candidateId, { job_id: jobId })
    // Re-fetch this candidate's detail to update applications list
    const { data: detail } = await getCandidate(candidateId)
    const idx = candidates.value.findIndex((c) => c.id === candidateId)
    if (idx !== -1) {
      candidates.value[idx] = detail
    }
    return app
  }

  /** Called when a card is dropped into a new column. */
  async function moveApplication(candidateId, appId, newStageId, kanbanPosition = 0) {
    // Optimistic update
    const candidate = candidates.value.find((c) => c.id === candidateId)
    const app = candidate?.applications?.find((a) => a.id === appId)
    const previousStageId = app?.current_stage_id
    if (app) {
      app.current_stage_id = newStageId
      app.kanban_position = kanbanPosition
      // Update nested stage object
      const stageObj = stages.value.find((s) => s.id === newStageId)
      if (stageObj) app.current_stage = { ...stageObj }
    }

    try {
      await apiUpdateStage(candidateId, appId, {
        stage_id: newStageId,
        kanban_position: kanbanPosition,
      })
    } catch (e) {
      // Revert on failure
      if (app && previousStageId) {
        app.current_stage_id = previousStageId
        const stageObj = stages.value.find((s) => s.id === previousStageId)
        if (stageObj) app.current_stage = { ...stageObj }
      }
      console.error('Failed to move application:', e)
      error.value = 'Failed to update stage.'
    }
  }

  async function init() {
    await fetchStages()
    await fetchCandidates()
  }

  return {
    stages,
    candidates,
    loading,
    error,
    boardColumns,
    fetchStages,
    fetchCandidates,
    addCandidate,
    applyToJob,
    moveApplication,
    init,
  }
})
