/**
 * Job Hunter Platform - REST API Client
 */

const API_BASE = '/api/v1';

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('jh_access_token') || null;
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('jh_access_token', token);
    } else {
      localStorage.removeItem('jh_access_token');
    }
  }

  getHeaders(customHeaders = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...customHeaders,
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = this.getHeaders(options.headers);
    
    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (response.status === 401) {
        // Token expired or invalid
        console.warn('Unauthorized request - session may have expired.');
      }

      if (!response.ok) {
        let errorMsg = `HTTP Error ${response.status}`;
        try {
          const errData = await response.json();
          errorMsg = errData.detail || errorMsg;
        } catch (_) {}
        throw new Error(errorMsg);
      }

      // Check if response is JSON
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      return await response.text();
    } catch (err) {
      console.error(`API Error on [${options.method || 'GET'} ${endpoint}]:`, err);
      throw err;
    }
  }

  // --- Auth APIs ---
  async register(email, password, fullName) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name: fullName }),
    });
  }

  async login(email, password) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  }

  async getMe() {
    return this.request('/auth/me');
  }

  // --- Jobs APIs ---
  async getJobs(params = {}) {
    const query = new URLSearchParams();
    if (params.keyword) query.append('keyword', params.keyword);
    if (params.work_mode) query.append('work_mode', params.work_mode);
    if (params.level) query.append('level', params.level);
    if (params.location) query.append('location', params.location);
    if (params.source) query.append('source', params.source);
    if (params.page) query.append('page', params.page);
    if (params.page_size) query.append('page_size', params.page_size);

    return this.request(`/jobs?${query.toString()}`);
  }

  async getJobDetail(jobId) {
    return this.request(`/jobs/${jobId}`);
  }

  async getSavedJobs() {
    return this.request('/jobs/saved');
  }

  async saveJob(jobId, notes = '') {
    return this.request(`/jobs/${jobId}/save`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    });
  }

  async unsaveJob(jobId) {
    return this.request(`/jobs/${jobId}/save`, {
      method: 'DELETE',
    });
  }

  async triggerDailyBatch(limitPerSource = 50) {
    return this.request(`/jobs/daily-batch?limit_per_source=${limitPerSource}`, {
      method: 'POST',
    });
  }

  async triggerCollection(source = 'mock', limit = 5) {
    return this.request(`/jobs/collect?source=${source}&limit=${limit}`, {
      method: 'POST',
    });
  }

  // --- Matches APIs ---
  async getTopRecommendations(limit = 10) {
    return this.request(`/matches/recommendations/top?limit=${limit}`);
  }

  async getMatchDetail(jobId) {
    return this.request(`/matches/${jobId}`);
  }

  async calculateMatch(jobId, forceRecalculate = false) {
    return this.request(`/matches/calculate/${jobId}`, {
      method: 'POST',
      body: JSON.stringify({ force_recalculate: forceRecalculate }),
    });
  }

  // --- Profile APIs ---
  async getProfile() {
    return this.request('/profile');
  }

  async updateProfile(profileData) {
    return this.request('/profile', {
      method: 'PUT',
      body: JSON.stringify(profileData),
    });
  }

  async syncProfileFromContext() {
    return this.request('/profile/sync', {
      method: 'POST',
    });
  }

  async uploadResumeFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const url = `${API_BASE}/profile/upload-resume`;
    const headers = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      let errorMsg = `HTTP Error ${response.status}`;
      try {
        const errData = await response.json();
        errorMsg = errData.detail || errorMsg;
      } catch (_) {}
      throw new Error(errorMsg);
    }
    return await response.json();
  }

  // --- Resumes & Applications APIs ---
  async getTailoredResume(jobId) {
    return this.request(`/resumes/job/${jobId}`);
  }

  async tailorResume(jobId, forceRegenerate = false, customTone = 'professional_and_humble') {
    return this.request(`/resumes/tailor/${jobId}`, {
      method: 'POST',
      body: JSON.stringify({
        force_regenerate: forceRegenerate,
        custom_tone: customTone,
      }),
    });
  }

  async deleteTailoredResume(jobId) {
    return this.request(`/resumes/job/${jobId}`, {
      method: 'DELETE',
    });
  }

  async deleteTailoredResumeById(resumeId) {
    return this.request(`/resumes/${resumeId}`, {
      method: 'DELETE',
    });
  }

  getResumePdfUrl(resumeId) {
    return `${API_BASE}/resumes/${resumeId}/pdf`;
  }

  async getApplications(page = 1, pageSize = 20) {
    return this.request(`/applications?page=${page}&page_size=${pageSize}`);
  }

  async submitApplication(jobId, payload = {}) {
    return this.request(`/applications/apply/${jobId}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async updateApplicationStatus(appId, status, errorMessage = null) {
    return this.request(`/applications/${appId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status, error_message: errorMessage }),
    });
  }

  // --- System Administration & Database APIs ---
  async purgeDatabase(scope = 'jobs_and_tailoring', cleanStorage = true) {
    return this.request('/system/purge-database', {
      method: 'POST',
      body: JSON.stringify({
        scope,
        clean_storage: cleanStorage,
        confirm: true,
      }),
    });
  }

  async resetDemo() {
    return this.request('/system/reset-demo', {
      method: 'POST',
    });
  }
}

window.api = new ApiClient();

