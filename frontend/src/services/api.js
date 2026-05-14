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

/* ---- Candidates ---- */
export const getCandidates = (params = {}) => api.get('/candidates/', { params })
export const getCandidate = (id) => api.get(`/candidates/${id}`)
export const createCandidate = (data) => api.post('/candidates/', data)
export const updateCandidate = (id, data) => api.put(`/candidates/${id}`, data)
export const deleteCandidate = (id) => api.delete(`/candidates/${id}`)

/* ---- Applications ---- */
export const createApplication = (candidateId, data) =>
  api.post(`/candidates/${candidateId}/applications`, data)

export const updateApplicationStage = (candidateId, appId, data) =>
  api.patch(`/candidates/${candidateId}/applications/${appId}/stage`, data)

/* ---- Pipeline Stages ---- */
export const getStages = () => api.get('/candidates/stages')

/* ---- Scraper (Module 1) ---- */
export const extractCandidate = (inputType, payload) =>
  api.post('/scraper/extract', { input_type: inputType, payload })

/* ---- Resume Screener (Module 2) ---- */
export const screenResume = (file, jobId) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('job_id', jobId)
  return api.post('/resumes/screen', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000, // 2 min — Claude can take time
  })
}

/* ---- Jobs ---- */
export const getJobs = () => api.get('/jobs/')

export default api
