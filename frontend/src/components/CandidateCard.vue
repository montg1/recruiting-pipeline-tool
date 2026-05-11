<script setup>
// CandidateCard — compact card shown in the pipeline / list view
defineProps({
  candidate: {
    type: Object,
    default: () => ({})
  }
})
</script>

<template>
  <div class="border rounded-lg p-4">
    <h3 class="font-semibold">{{ candidate.name || 'Candidate Name' }}</h3>
    <!-- TODO: Show stage badge, email, source, etc. -->
  </div>
</template>
