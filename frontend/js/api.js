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
function normalizeBaseUrl(url) {
  if (!url || typeof url !== 'string') return '';
  let cleaned = url.trim().replace(/\/+$/, '');
  if (!cleaned.endsWith('/api/v1') && !cleaned.includes('/api/')) {
    cleaned += '/api/v1';
  }
  return cleaned;
}

function resolveApiBaseUrl() {
  // 1. localStorage override
  try {
    const saved = localStorage.getItem('jh_api_base');
    if (saved && saved.trim()) {
      return normalizeBaseUrl(saved);
    }
  } catch (_) {}

  // 2. window.ENV / runtime config
  const envUrl = window.ENV?.API_URL || window.__RUNTIME_CONFIG__?.API_URL || window.API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim()) {
    return normalizeBaseUrl(envUrl);
  }

  // 3. Meta tag
  if (typeof document !== 'undefined') {
    const metaTag = document.querySelector('meta[name="api-base"]');
    if (metaTag && metaTag.content && metaTag.content.trim()) {
      return normalizeBaseUrl(metaTag.content);
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

  async executeFetch(url, options, headers, timeoutMs) {
    const controller = new AbortController();
    let timeoutId = null;
    let didTimeout = false;

    if (timeoutMs > 0) {
      timeoutId = setTimeout(() => {
        didTimeout = true;
        controller.abort();
      }, timeoutMs);
    }

    if (options.signal) {
      if (options.signal.aborted) {
        controller.abort();
      } else {
        options.signal.addEventListener('abort', () => controller.abort(), { once: true });
      }
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });
      return response;
    } catch (err) {
      if (didTimeout || err.name === 'AbortError') {
        const timeoutErr = new Error('Yêu cầu hết thời gian chờ (Backend cold start / Network timeout).');
        timeoutErr.name = 'TimeoutError';
        timeoutErr.isTimeout = true;
        throw timeoutErr;
      }
      throw err;
    } finally {
      if (timeoutId) clearTimeout(timeoutId);
    }
  }

  async request(endpoint, options = {}) {
    let url;
    if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) {
      url = endpoint;
    } else {
      const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
      url = `${this.baseUrl}${cleanEndpoint}`;
    }

    const method = (options.method || 'GET').toUpperCase();
    const isSafeMethod = ['GET', 'HEAD', 'OPTIONS'].includes(method);
    const canRetry = isSafeMethod || options.safeRetry === true;
    const maxRetries = canRetry ? (options.maxRetries !== undefined ? options.maxRetries : 2) : 0;
    const timeoutMs = options.timeout !== undefined ? options.timeout : 25000;

    let lastError = null;
    let hadTransientFailure = false;

    for (let attempt = 1; attempt <= 1 + maxRetries; attempt++) {
      const headers = this.getHeaders(options.headers);

      try {
        const response = await this.executeFetch(url, options, headers, timeoutMs);

        if (response.status === 401) {
          console.warn('Unauthorized request — user session might be expired or missing.');
          if (this.token && typeof window !== 'undefined') {
            this.setToken(null);
            window.dispatchEvent(new CustomEvent('jh:auth_expired'));
          }
        }

        // Lỗi gateway / cold-start 502/503/504
        if ([502, 503, 504].includes(response.status)) {
          hadTransientFailure = true;
          if (attempt <= maxRetries) {
            if (typeof window !== 'undefined') {
              window.dispatchEvent(new CustomEvent('jh:backend_waking', {
                detail: { attempt, maxAttempts: 1 + maxRetries, status: response.status }
              }));
            }
            const backoffMs = Math.min(1500 * Math.pow(2, attempt - 1), 5000);
            await new Promise((resolve) => setTimeout(resolve, backoffMs));
            continue;
          }

          const err = new Error('Máy chủ Backend đang khởi động lại (Render cold start). Vui lòng đợi trong giây lát và thử lại.');
          err.isBackendWaking = true;
          err.status = response.status;
          throw err;
        }

        // Lỗi ứng dụng (400, 403, 404, 422, 500...)
        if (!response.ok) {
          let errorMsg = `HTTP Error ${response.status}`;
          try {
            const errData = await response.json();
            errorMsg = errData.detail || errData.message || errorMsg;
          } catch (_) {}
          const appErr = new Error(errorMsg);
          appErr.status = response.status;
          throw appErr;
        }

        if (hadTransientFailure && typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('jh:backend_ready'));
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          return await response.json();
        }
        return await response.text();
      } catch (err) {
        lastError = err;

        // Nếu là lỗi ứng dụng (status < 500), rethrow ngay lập tức
        if (err.status && err.status < 500) {
          throw err;
        }

        const isTransientNetwork = err.isTimeout ||
                                   err.name === 'TimeoutError' ||
                                   err.name === 'AbortError' ||
                                   err.name === 'TypeError' ||
                                   (err.message && (
                                     err.message.includes('fetch') ||
                                     err.message.includes('network') ||
                                     err.message.includes('NetworkError') ||
                                     err.message.includes('Failed to fetch')
                                   ));

        if (isTransientNetwork && canRetry && attempt <= maxRetries) {
          hadTransientFailure = true;
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('jh:backend_waking', {
              detail: { attempt, maxAttempts: 1 + maxRetries }
            }));
          }
          const backoffMs = Math.min(1500 * Math.pow(2, attempt - 1), 5000);
          await new Promise((resolve) => setTimeout(resolve, backoffMs));
          continue;
        }

        if (isTransientNetwork) {
          const friendlyErr = new Error('Máy chủ Backend đang khởi động lại (Render cold start). Vui lòng đợi trong giây lát và thử lại.');
          friendlyErr.isBackendWaking = true;
          friendlyErr.status = 503;
          throw friendlyErr;
        }

        throw err;
      }
    }

    throw lastError || new Error('Yêu cầu không thành công');
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
        healthy: data.status === 'ok' || data.status === 'healthy' || data.status === 'ready',
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

  // --- Database Readiness Probe ---
  async checkReadiness() {
    const startTime = performance.now();
    let readyUrl;
    
    if (this.baseUrl.startsWith('http://') || this.baseUrl.startsWith('https://')) {
      const rootBase = this.baseUrl.replace(/\/api\/v1\/?$/, '');
      readyUrl = `${rootBase}/health/ready`;
    } else {
      readyUrl = '/health/ready';
    }

    try {
      const response = await fetch(readyUrl, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        cache: 'no-cache',
      });
      const latencyMs = Math.round(performance.now() - startTime);
      const data = await response.json().catch(() => ({}));
      
      return {
        ready: response.status === 200 && data.status === 'ready',
        status: response.status,
        latencyMs,
        data,
      };
    } catch (err) {
      const latencyMs = Math.round(performance.now() - startTime);
      return {
        ready: false,
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
    return `${this.baseUrl}/resumes/${resumeId}/pdf?download=${download ? 'true' : 'false'}`;
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
