<script setup>
/**
 * AddCandidateModal — slide-over modal for creating a new candidate
 * and optionally applying them to a job.
 */
import { ref, watch } from 'vue'

const props = defineProps({
  show: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'submit'])

const form = ref({
  full_name: '',
  email: '',
  phone: '',
  source: 'LinkedIn',
  linkedin_url: '',
  job_id: 1,
})

const submitting = ref(false)
const errorMsg = ref('')

// Reset form when modal opens
watch(
  () => props.show,
  (val) => {
    if (val) {
      form.value = { full_name: '', email: '', phone: '', source: 'LinkedIn', linkedin_url: '', job_id: 1 }
      errorMsg.value = ''
    }
  }
)

async function handleSubmit() {
  if (!form.value.full_name.trim() || !form.value.email.trim()) {
    errorMsg.value = 'Name and email are required.'
    return
  }
  submitting.value = true
  errorMsg.value = ''
  try {
    await emit('submit', { ...form.value })
  } catch (e) {
    errorMsg.value = e?.response?.data?.detail || 'Failed to add candidate.'
  } finally {
    submitting.value = false
  }
}

const sources = ['LinkedIn', 'Referral', 'Job Board', 'Website', 'n8n_scrape', 'Other']
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="show" class="fixed inset-0 z-50 flex">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="emit('close')" />

        <!-- Panel -->
        <div class="relative ml-auto w-full max-w-md bg-white shadow-2xl flex flex-col
                    animate-[slideInRight_0.3s_ease]">
          <!-- Header -->
          <div class="flex items-center justify-between px-6 py-5 border-b border-hplus-border">
            <div>
              <h2 class="text-lg font-bold text-hplus-text">Add Candidate</h2>
              <p class="text-xs text-hplus-text-muted mt-0.5">Create a new candidate and add to pipeline</p>
            </div>
            <button
              @click="emit('close')"
              class="p-2 rounded-lg hover:bg-slate-100 transition"
            >
              <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- Form -->
          <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
            <!-- Error -->
            <div v-if="errorMsg" class="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-600">
              {{ errorMsg }}
            </div>

            <!-- Name -->
            <div>
              <label class="block text-xs font-semibold text-hplus-text-muted uppercase tracking-wider mb-1.5">
                Full Name *
              </label>
              <input
                v-model="form.full_name"
                type="text"
                placeholder="e.g. Somchai Prasert"
                class="w-full px-3 py-2.5 rounded-lg border border-hplus-border bg-hplus-surface
                       text-sm text-hplus-text placeholder:text-slate-400
                       focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold
                       transition"
              />
            </div>

            <!-- Email -->
            <div>
              <label class="block text-xs font-semibold text-hplus-text-muted uppercase tracking-wider mb-1.5">
                Email *
              </label>
              <input
                v-model="form.email"
                type="email"
                placeholder="candidate@email.com"
                class="w-full px-3 py-2.5 rounded-lg border border-hplus-border bg-hplus-surface
                       text-sm text-hplus-text placeholder:text-slate-400
                       focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold
                       transition"
              />
            </div>

            <!-- Phone -->
            <div>
              <label class="block text-xs font-semibold text-hplus-text-muted uppercase tracking-wider mb-1.5">
                Phone
              </label>
              <input
                v-model="form.phone"
                type="tel"
                placeholder="+66 81 234 5678"
                class="w-full px-3 py-2.5 rounded-lg border border-hplus-border bg-hplus-surface
                       text-sm text-hplus-text placeholder:text-slate-400
                       focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold
                       transition"
              />
            </div>

            <!-- Source -->
            <div>
              <label class="block text-xs font-semibold text-hplus-text-muted uppercase tracking-wider mb-1.5">
                Source
              </label>
              <select
                v-model="form.source"
                class="w-full px-3 py-2.5 rounded-lg border border-hplus-border bg-hplus-surface
                       text-sm text-hplus-text
                       focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold
                       transition"
              >
                <option v-for="s in sources" :key="s" :value="s">{{ s }}</option>
              </select>
            </div>

            <!-- LinkedIn URL -->
            <div>
              <label class="block text-xs font-semibold text-hplus-text-muted uppercase tracking-wider mb-1.5">
                LinkedIn URL
              </label>
              <input
                v-model="form.linkedin_url"
                type="url"
                placeholder="https://linkedin.com/in/..."
                class="w-full px-3 py-2.5 rounded-lg border border-hplus-border bg-hplus-surface
                       text-sm text-hplus-text placeholder:text-slate-400
                       focus:outline-none focus:ring-2 focus:ring-hplus-gold/40 focus:border-hplus-gold
                       transition"
              />
            </div>
          </div>

          <!-- Footer -->
          <div class="px-6 py-4 border-t border-hplus-border bg-slate-50 flex items-center justify-end gap-3">
            <button
              @click="emit('close')"
              class="px-4 py-2 rounded-lg text-sm font-medium text-hplus-text-muted
                     hover:bg-slate-200 transition"
            >
              Cancel
            </button>
            <button
              @click="handleSubmit"
              :disabled="submitting"
              class="px-5 py-2.5 rounded-lg text-sm font-semibold
                     bg-hplus-gold text-hplus-navy shadow-md
                     hover:bg-amber-400 hover:shadow-lg
                     disabled:opacity-50 disabled:cursor-not-allowed
                     transition-all duration-200"
            >
              <span v-if="submitting" class="flex items-center gap-2">
                <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                Adding...
              </span>
              <span v-else>Add Candidate</span>
            </button>
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
