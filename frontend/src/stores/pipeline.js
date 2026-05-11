/**
 * Pipeline store — manages candidate pipeline state with Pinia.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

export const usePipelineStore = defineStore('pipeline', () => {
  const candidates = ref([])
  const loading = ref(false)

  // TODO: Implement actions:
  // - fetchCandidates()
  // - addCandidate(candidate)
  // - updateStage(candidateId, newStage)

  return { candidates, loading }
})
