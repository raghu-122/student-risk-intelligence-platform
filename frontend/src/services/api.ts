import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// --- Auth ---
export const authApi = {
  login: (username: string, password: string) =>
    api.post('/api/auth/login', { username, password }),
  me: () => api.get('/api/auth/me'),
};

// --- Dashboard ---
export const dashboardApi = {
  getStats: () => api.get('/api/dashboard/stats'),
  getRiskDistribution: () => api.get('/api/dashboard/risk-distribution'),
  getAtRiskStudents: (limit = 10) => api.get(`/api/dashboard/at-risk-students?limit=${limit}`),
  getRecentInterventions: (limit = 5) => api.get(`/api/dashboard/recent-interventions?limit=${limit}`),
};

// --- Students ---
export const studentsApi = {
  list: (params?: Record<string, unknown>) => api.get('/api/students/', { params }),
  get: (id: string) => api.get(`/api/students/${id}`),
  create: (data: unknown) => api.post('/api/students/', data),
  update: (id: string, data: unknown) => api.put(`/api/students/${id}`, data),
  getRiskHistory: (id: string) => api.get(`/api/students/${id}/risk-history`),
  getEnrollments: (id: string) => api.get(`/api/students/${id}/enrollments`),
};

// --- Courses ---
export const coursesApi = {
  list: (params?: Record<string, unknown>) => api.get('/api/courses/', { params }),
  get: (id: string) => api.get(`/api/courses/${id}`),
};

// --- Enrollments ---
export const enrollmentsApi = {
  list: (params?: Record<string, unknown>) => api.get('/api/enrollments/', { params }),
  get: (id: string) => api.get(`/api/enrollments/${id}`),
};

// --- Attendance ---
export const attendanceApi = {
  list: (params?: Record<string, unknown>) => api.get('/api/attendance/', { params }),
  getSummary: (enrollmentId: string) => api.get(`/api/attendance/summary/${enrollmentId}`),
};

// --- Assessments ---
export const assessmentsApi = {
  list: (params?: Record<string, unknown>) => api.get('/api/assessments/', { params }),
  listResults: (params?: Record<string, unknown>) => api.get('/api/assessments/results', { params }),
};

// --- LMS ---
export const lmsApi = {
  list: (params?: Record<string, unknown>) => api.get('/api/lms/', { params }),
  getSummary: (enrollmentId: string) => api.get(`/api/lms/summary/${enrollmentId}`),
};

// --- Risk ---
export const riskApi = {
  list: (params?: Record<string, unknown>) => api.get('/api/risk/', { params }),
  getRanking: (params?: Record<string, unknown>) => api.get('/api/risk/ranking', { params }),
  calculate: (studentId: string, enrollmentId: string, cutoffDate?: string) =>
    api.post('/api/risk/calculate', { student_id: studentId, enrollment_id: enrollmentId, cutoff_date: cutoffDate }),
  getFactors: (riskId: string) => api.get(`/api/risk/${riskId}/factors`),
  getDistribution: () => api.get('/api/risk/distribution'),
};

// --- Support Cases ---
export const supportCasesApi = {
  list: (params?: Record<string, unknown>) => api.get('/api/support-cases/', { params }),
  get: (id: string) => api.get(`/api/support-cases/${id}`),
  create: (data: unknown) => api.post('/api/support-cases/', data),
  update: (id: string, data: unknown) => api.put(`/api/support-cases/${id}`, data),
  transition: (id: string, action: string, notes?: string) =>
    api.post(`/api/support-cases/${id}/transition`, { action, notes }),
};

// --- Interventions ---
export const interventionsApi = {
  list: (params?: Record<string, unknown>) => api.get('/api/interventions/', { params }),
  get: (id: string) => api.get(`/api/interventions/${id}`),
  create: (data: unknown) => api.post('/api/interventions/', data),
  update: (id: string, data: unknown) => api.put(`/api/interventions/${id}`, data),
  transition: (id: string, action: string, notes?: string) =>
    api.post(`/api/interventions/${id}/transition`, { action, notes }),
  recommend: (studentId: string, enrollmentId?: string) =>
    api.post('/api/interventions/recommend', { student_id: studentId, enrollment_id: enrollmentId }),
};

// --- Outcomes ---
export const outcomesApi = {
  list: (params?: Record<string, unknown>) => api.get('/api/outcomes/', { params }),
  get: (id: string) => api.get(`/api/outcomes/${id}`),
  getDistribution: () => api.get('/api/outcomes/distribution'),
};

// --- Data Quality ---
export const dataQualityApi = {
  list: (params?: Record<string, unknown>) => api.get('/api/data-quality/', { params }),
  runChecks: () => api.post('/api/data-quality/run-checks'),
  getSummary: () => api.get('/api/data-quality/summary'),
};

// --- Reports ---
export const reportsApi = {
  downloadStudents: () => api.get('/api/reports/students', { responseType: 'blob' }),
  downloadRisk: () => api.get('/api/reports/risk-assessments', { responseType: 'blob' }),
  downloadInterventions: () => api.get('/api/reports/interventions', { responseType: 'blob' }),
  downloadOutcomes: () => api.get('/api/reports/outcomes', { responseType: 'blob' }),
  downloadDataQuality: () => api.get('/api/reports/data-quality', { responseType: 'blob' }),
  downloadDataManifest: () => api.get('/api/reports/data-manifest', { responseType: 'blob' }),
};

