/**
 * API service — centralised Axios instance for backend communication.
 */

import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export default api

// TODO: Add specific service functions, e.g.:
// export const getCandidates = () => api.get('/candidates')
// export const uploadResume = (formData) => api.post('/resumes/upload', formData)
// export const scheduleInterview = (data) => api.post('/interviews', data)
