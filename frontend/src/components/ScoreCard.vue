<script setup>
// ScoreCard — displays AI-generated scoring breakdown for a candidate's resume
defineProps({
  scores: {
    type: Object,
    default: () => ({})
  }
})
</script>

<template>
  <div class="border rounded-lg p-4">
    <h3 class="font-semibold">Score Card</h3>
    <!-- TODO: Render skills fit, experience fit, culture fit scores -->
  </div>
</template>
