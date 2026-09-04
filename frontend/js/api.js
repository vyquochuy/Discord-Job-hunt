/**
 * Job Hunter Platform — Enterprise REST API Client (Cloud-Ready & Multi-Tier Resolution)
 * Manages authentication, job querying, deterministic matching, resume tailoring, and system operations.
 * Supports Zero-Cost deployment on Cloudflare Pages, Render, Koyeb, Supabase, and local development.
 */

/**
 * Resolves the active Backend API base URL using a multi-tiered hierarchy:
 * 1. User manual override stored in localStorage (`jh_api_base`)
 * 2. Window Runtime Config (`window.ENV?.API_URL` or `window.__RUNTIME_CONFIG__?.API_URL` or `window.API_URL`)
 * 3. HTML Meta Tag (`<meta name="api-base" content="...">`)
 * 4. Local dev auto-detection (if on localhost / 127.0.0.1 on a non-8000 port -> http://localhost:8000/api/v1)
 * 5. File protocol auto-detection (if on file:// -> http://localhost:8000/api/v1)
 * 6. Default relative path (`/api/v1`)
 */
function resolveApiBaseUrl() {
  // 1. localStorage override
  try {
    const saved = localStorage.getItem('jh_api_base');
    if (saved && saved.trim()) {
      return saved.trim().replace(/\/+$/, '');
    }
  } catch (_) {}

  // 2. window.ENV / runtime config
  const envUrl = window.ENV?.API_URL || window.__RUNTIME_CONFIG__?.API_URL || window.API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim()) {
    return envUrl.trim().replace(/\/+$/, '');
  }

  // 3. Meta tag
  if (typeof document !== 'undefined') {
    const metaTag = document.querySelector('meta[name="api-base"]');
    if (metaTag && metaTag.content && metaTag.content.trim()) {
      return metaTag.content.trim().replace(/\/+$/, '');
    }
  }

  // 4. Local dev separate port fallback & file protocol
  if (typeof window !== 'undefined' && window.location) {
    const { protocol, hostname, port } = window.location;
    if (protocol === 'file:') {
      return 'http://localhost:8000/api/v1';
    }
    if ((hostname === 'localhost' || hostname === '127.0.0.1') && port && port !== '8000') {
      return 'http://localhost:8000/api/v1';
    }
  }

  // 5. Default relative API path
  return '/api/v1';
}

function getApiResolutionSource() {
  try {
    const saved = localStorage.getItem('jh_api_base');
    if (saved && saved.trim()) return 'localStorage (Tùy biến người dùng)';
  } catch (_) {}

  const envUrl = window.ENV?.API_URL || window.__RUNTIME_CONFIG__?.API_URL || window.API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim()) return 'window.ENV (env.js / Runtime Config)';

  if (typeof document !== 'undefined') {
    const metaTag = document.querySelector('meta[name="api-base"]');
    if (metaTag && metaTag.content && metaTag.content.trim()) return 'HTML <meta name="api-base">';
  }

  if (typeof window !== 'undefined' && window.location) {
    const { protocol, hostname, port } = window.location;
    if (protocol === 'file:') return 'file:// protocol (Fallback Localhost:8000)';
    if ((hostname === 'localhost' || hostname === '127.0.0.1') && port && port !== '8000') {
      return `Dev Port ${port} (Fallback Localhost:8000)`;
    }
  }

  return 'Relative Path (/api/v1)';
}

class ApiClient {
  constructor() {
    this.baseUrl = resolveApiBaseUrl();
    this.token = localStorage.getItem('jh_access_token') || null;
  }

  getBaseUrl() {
    return this.baseUrl;
  }

  setBaseUrl(url) {
    if (url && typeof url === 'string' && url.trim()) {
      const cleaned = url.trim().replace(/\/+$/, '');
      this.baseUrl = cleaned;
      localStorage.setItem('jh_api_base', cleaned);
    } else {
      localStorage.removeItem('jh_api_base');
      this.baseUrl = resolveApiBaseUrl();
    }
    return this.baseUrl;
  }

  resetBaseUrl() {
    localStorage.removeItem('jh_api_base');
    this.baseUrl = resolveApiBaseUrl();
    return this.baseUrl;
  }

  getResolutionSource() {
    return getApiResolutionSource();
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
    let url;
    if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) {
      url = endpoint;
    } else {
      const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
      url = `${this.baseUrl}${cleanEndpoint}`;
    }

    const headers = this.getHeaders(options.headers);
    
    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (response.status === 401) {
        console.warn('Unauthorized request — user session might be expired or missing.');
        if (this.token && typeof window !== 'undefined') {
          this.setToken(null);
          window.dispatchEvent(new CustomEvent('jh:auth_expired'));
        }
      }

      if (!response.ok) {
        let errorMsg = `HTTP Error ${response.status}`;
        try {
          const errData = await response.json();
          errorMsg = errData.detail || errData.message || errorMsg;
        } catch (_) {}
        throw new Error(errorMsg);
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      return await response.text();
    } catch (err) {
      console.error(`API Error [${options.method || 'GET'} ${endpoint}] -> ${url}:`, err);
      throw err;
    }
  }

  // --- Health Check & Ping ---
  async checkHealth() {
    const startTime = performance.now();
    let healthUrl;
    
    if (this.baseUrl.startsWith('http://') || this.baseUrl.startsWith('https://')) {
      const rootBase = this.baseUrl.replace(/\/api\/v1\/?$/, '');
      healthUrl = `${rootBase}/health`;
    } else {
      healthUrl = '/health';
    }

    try {
      const response = await fetch(healthUrl, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        cache: 'no-cache',
      });
      const latencyMs = Math.round(performance.now() - startTime);
      
      if (!response.ok) {
        return {
          healthy: false,
          status: response.status,
          latencyMs,
          error: `HTTP ${response.status}: ${response.statusText}`,
        };
      }

      const data = await response.json();
      return {
        healthy: data.status === 'healthy',
        status: response.status,
        latencyMs,
        data,
      };
    } catch (err) {
      const latencyMs = Math.round(performance.now() - startTime);
      return {
        healthy: false,
        status: 0,
        latencyMs,
        error: err.message || 'Không thể kết nối tới máy chủ Backend',
      };
    }
  }

  // --- Authentication ---
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

  logout() {
    this.setToken(null);
  }

  hasToken() {
    return !!this.token;
  }

  // --- Jobs Management ---
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

  async ingestManualJob(payload) {
    return this.request('/jobs/ingest-manual', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // --- Matching Engine ---
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

  // --- Profile & Resume Upload ---
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

    const url = `${this.baseUrl}/profile/upload-resume`;
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

  // --- Tailored Resumes & Applications ---
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

  async updateResumeLatex(resumeId, latexSource) {
    return this.request(`/resumes/${resumeId}/tex`, {
      method: 'PUT',
      body: JSON.stringify({ latex_source: latexSource }),
    });
  }

  getResumePdfUrl(resumeId, download = false) {
    const token = this.token;
    const tokenQuery = token ? `&token=${encodeURIComponent(token)}` : '';
    return `${this.baseUrl}/resumes/${resumeId}/pdf?download=${download ? 'true' : 'false'}${tokenQuery}`;
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

  // --- System Operations ---
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
