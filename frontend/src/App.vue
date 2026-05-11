<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Navigation -->
    <nav class="bg-white shadow-sm border-b">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16 items-center">
          <div class="flex items-center gap-8">
            <RouterLink to="/" class="text-xl font-bold text-indigo-600">
              RecruitPipe
            </RouterLink>
            <div class="flex gap-4">
              <RouterLink to="/" class="text-gray-600 hover:text-indigo-600 transition">
                Dashboard
              </RouterLink>
              <RouterLink to="/upload" class="text-gray-600 hover:text-indigo-600 transition">
                Upload Resume
              </RouterLink>
            </div>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main content -->
    <main class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
      <RouterView />
    </main>
  </div>
</template>
