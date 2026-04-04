import api from './axios'

// TA Doubt Summarizer API wrapper
export const doubtsAPI = {
  upload(payload) {
    // payload: { course_code, source, messages: [{ author_role, text }] }
    return api.post('/ta/doubts/upload', payload).then(r => r.data)
  },
  getSummary(courseCode, params = {}) {
    // params: { period, source }
    return api.get(`/ta/doubts/summary/${encodeURIComponent(courseCode)}`, { params, timeout: 15000 }).then(r => r.data)
  },
  getTopics(courseCode, params = {}) {
    return api.get(`/ta/doubts/topics/${encodeURIComponent(courseCode)}`, { params }).then(r => r.data)
  },
  getInsights(courseCode, params = {}) {
    return api.get(`/ta/doubts/insights/${encodeURIComponent(courseCode)}`, { params }).then(r => r.data)
  },
  getSourceBreakdown(courseCode, params = {}) {
    // params: { period }
    return api.get(`/ta/doubts/source-breakdown/${encodeURIComponent(courseCode)}`, { params, timeout: 15000 }).then(r => r.data)
  }
}

export default doubtsAPI
