<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="min-h-screen bg-hplus-surface">
    <!-- Navigation -->
    <nav class="bg-hplus-navy shadow-lg">
      <div class="mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16 items-center">
          <!-- Logo -->
          <div class="flex items-center gap-8">
            <RouterLink to="/" class="flex items-center gap-2 group">
              <div class="w-9 h-9 rounded-lg bg-hplus-gold flex items-center justify-center shadow-md
                          group-hover:shadow-hplus-gold/40 transition-shadow duration-300">
                <span class="text-hplus-navy font-black text-sm">H+</span>
              </div>
              <span class="text-white font-bold text-lg tracking-tight">
                Recruit<span class="text-hplus-gold">Pipe</span>
              </span>
            </RouterLink>

            <!-- Nav Links -->
            <div class="hidden sm:flex items-center gap-1">
              <RouterLink
                to="/"
                class="px-3 py-2 rounded-lg text-sm font-medium text-slate-300
                       hover:text-white hover:bg-white/10 transition-all duration-200"
                active-class="!text-hplus-gold !bg-hplus-gold/10"
              >
                <span class="flex items-center gap-2">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
                  </svg>
                  Pipeline
                </span>
              </RouterLink>
              <RouterLink
                to="/upload"
                class="px-3 py-2 rounded-lg text-sm font-medium text-slate-300
                       hover:text-white hover:bg-white/10 transition-all duration-200"
                active-class="!text-hplus-gold !bg-hplus-gold/10"
              >
                <span class="flex items-center gap-2">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  Upload Resume
                </span>
              </RouterLink>
              <RouterLink
                to="/scraper"
                class="px-3 py-2 rounded-lg text-sm font-medium text-slate-300
                       hover:text-white hover:bg-white/10 transition-all duration-200"
                active-class="!text-hplus-gold !bg-hplus-gold/10"
              >
                <span class="flex items-center gap-2">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  Scraper
                </span>
              </RouterLink>
              <RouterLink
                to="/cv-screener"
                class="px-3 py-2 rounded-lg text-sm font-medium text-slate-300
                       hover:text-white hover:bg-white/10 transition-all duration-200"
                active-class="!text-hplus-gold !bg-hplus-gold/10"
              >
                <span class="flex items-center gap-2">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                  </svg>
                  AI Screener
                </span>
              </RouterLink>
            </div>
          </div>

          <!-- Right side -->
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-full bg-hplus-gold/20 border-2 border-hplus-gold/40
                        flex items-center justify-center">
              <svg class="w-4 h-4 text-hplus-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main content -->
    <main>
      <RouterView />
    </main>
  </div>
</template>
