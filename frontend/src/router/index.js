import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
    },
    {
      path: '/candidates/:id',
      name: 'candidate-detail',
      component: () => import('@/views/CandidateDetailView.vue'),
    },
    {
      path: '/upload',
      name: 'upload',
      component: () => import('@/views/UploadView.vue'),
    },
    {
      path: '/scraper',
      name: 'scraper',
      component: () => import('@/views/ScraperView.vue'),
    },
  ],
})

export default router
