/**
 * Job Hunter Platform — HTTP Client Base
 */

import { resolveApiBaseUrl, getApiResolutionSource, isLocalDevEnvironment } from '../config/config.js';
import { events, APP_EVENTS } from '../core/events.js';

export class ApiClient {
  constructor() {
    this.baseUrl = resolveApiBaseUrl();
    this.token = (typeof localStorage !== 'undefined') ? localStorage.getItem('jh_access_token') : null;
    this.refreshToken = (typeof localStorage !== 'undefined') ? localStorage.getItem('jh_refresh_token') : null;
    this.refreshPromise = null; // Mutex Promise Queue cho in-flight refresh requests
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

  setTokens(accessToken, refreshToken = null) {
    this.token = accessToken;
    if (refreshToken !== undefined && refreshToken !== null) {
      this.refreshToken = refreshToken;
    }
    if (typeof localStorage !== 'undefined') {
      if (accessToken) {
        localStorage.setItem('jh_access_token', accessToken);
      } else {
        localStorage.removeItem('jh_access_token');
      }
      if (this.refreshToken) {
        localStorage.setItem('jh_refresh_token', this.refreshToken);
      } else if (refreshToken === null) {
        localStorage.removeItem('jh_refresh_token');
      }
    }
  }

  setToken(token, refreshToken = null) {
    this.setTokens(token, refreshToken);
  }

  hasToken() {
    return !!this.token;
  }

  async logout() {
    if (this.refreshToken) {
      try {
        await fetch(`${this.baseUrl}/auth/logout`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: this.refreshToken }),
        });
      } catch (_) {}
    }
    this.token = null;
    this.refreshToken = null;
    this.refreshPromise = null;
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('jh_access_token');
      localStorage.removeItem('jh_refresh_token');
    }
    events.emit(APP_EVENTS.AUTH_EXPIRED);
  }

  async refreshAuthToken() {
    // Invariant 1: Frontend Mutex ngăn chặn hoàn toàn duplicate refresh requests
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    if (!this.refreshToken) {
      throw new Error('No refresh token available');
    }

    this.refreshPromise = (async () => {
      try {
        const response = await fetch(`${this.baseUrl}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: this.refreshToken }),
        });

        if (!response.ok) {
          throw new Error(`Refresh failed with status ${response.status}`);
        }

        const data = await response.json();
        this.setTokens(data.access_token, data.refresh_token);
        return data.access_token;
      } catch (err) {
        this.token = null;
        this.refreshToken = null;
        if (typeof localStorage !== 'undefined') {
          localStorage.removeItem('jh_access_token');
          localStorage.removeItem('jh_refresh_token');
        }
        events.emit(APP_EVENTS.AUTH_EXPIRED);
        throw err;
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
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

  async request(endpoint, options = {}, isAuthRetry = false) {
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

        // 401 Unauthorized: Refresh Token Mutex Queue (Không retry vô hạn, chỉ 1 lần qua isAuthRetry)
        if (response.status === 401) {
          const isAuthEndpoint = endpoint.includes('/auth/login') ||
                                 endpoint.includes('/auth/register') ||
                                 endpoint.includes('/auth/refresh');

          if (!isAuthRetry && !isAuthEndpoint && this.refreshToken) {
            try {
              console.info('Access token expired, triggering automatic refresh with mutex...');
              await this.refreshAuthToken();
              return await this.request(endpoint, options, true);
            } catch (refreshErr) {
              console.warn('Token refresh failed, session terminated:', refreshErr);
            }
          } else {
            console.warn('Unauthorized request — user session might be expired or missing.');
            if (this.token || this.refreshToken) {
              this.token = null;
              this.refreshToken = null;
              if (typeof localStorage !== 'undefined') {
                localStorage.removeItem('jh_access_token');
                localStorage.removeItem('jh_refresh_token');
              }
              events.emit(APP_EVENTS.AUTH_EXPIRED);
            }
          }
        }

        // Kiểm tra lỗi tạm thời 502/503/504 từ Render / Gateway khi cold start
        if ([502, 503, 504].includes(response.status)) {
          hadTransientFailure = true;
          if (attempt <= maxRetries) {
            events.emit(APP_EVENTS.BACKEND_WAKING, {
              attempt,
              maxAttempts: 1 + maxRetries,
              status: response.status,
            });
            const backoffMs = Math.min(1500 * Math.pow(2, attempt - 1), 5000);
            await new Promise((resolve) => setTimeout(resolve, backoffMs));
            continue;
          }

          const isLocal = isLocalDevEnvironment();
          const msg = isLocal
            ? `Máy chủ Backend phản hồi lỗi ${response.status}. Vui lòng kiểm tra lại dịch vụ Backend local.`
            : 'Máy chủ Backend đang khởi động lại (Render cold start). Vui lòng đợi trong giây lát và thử lại.';
          const err = new Error(msg);
          err.isBackendWaking = !isLocal;
          err.status = response.status;
          throw err;
        }

        // Xử lý các lỗi ứng dụng khác (400, 403, 404, 422, 500...) — TUYỆT ĐỐI KHÔNG coi là backend waking
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

        // Nếu trước đó có retry do lỗi tạm thời và lần này thành công, thông báo backend sẵn sàng
        if (hadTransientFailure) {
          events.emit(APP_EVENTS.BACKEND_READY);
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          return await response.json();
        }
        return await response.text();
      } catch (err) {
        lastError = err;

        // Nếu là lỗi ứng dụng (400, 401, 403, 404, 422...) đã throw có status, rethrow ngay lập tức không retry
        if (err.status && err.status < 500) {
          throw err;
        }

        // Kiểm tra lỗi mạng / timeout
        const isTimeout = err.isTimeout || err.name === 'TimeoutError' || err.name === 'AbortError';
        const isTransientNetwork = isTimeout ||
                                   err.name === 'TypeError' ||
                                   (err.message && (
                                     err.message.includes('fetch') ||
                                     err.message.includes('network') ||
                                     err.message.includes('NetworkError') ||
                                     err.message.includes('Failed to fetch')
                                   ));

        if (isTransientNetwork && canRetry && attempt <= maxRetries) {
          hadTransientFailure = true;
          events.emit(APP_EVENTS.BACKEND_WAKING, {
            attempt,
            maxAttempts: 1 + maxRetries,
          });
          const backoffMs = Math.min(1500 * Math.pow(2, attempt - 1), 5000);
          await new Promise((resolve) => setTimeout(resolve, backoffMs));
          continue;
        }

        if (isTransientNetwork) {
          const isLocal = isLocalDevEnvironment();
          let friendlyMsg;
          if (isTimeout) {
            friendlyMsg = isLocal
              ? 'Tác vụ xử lý quá thời gian chờ (Timeout). Backend local vẫn đang chạy ngầm trong nền, vui lòng đợi ít phút rồi làm mới danh sách.'
              : 'Tác vụ mất nhiều thời gian hơn dự kiến (Timeout). Quá trình quét vẫn đang chạy ngầm trên máy chủ, vui lòng đợi ít phút rồi làm mới danh sách.';
          } else {
            friendlyMsg = isLocal
              ? 'Không thể kết nối đến máy chủ Backend local (http://localhost:8000). Vui lòng kiểm tra xem Backend FastAPI / Docker đã chạy chưa.'
              : 'Máy chủ Backend đang khởi động lại (Render cold start). Vui lòng đợi trong giây lát và thử lại.';
          }
          const friendlyErr = new Error(friendlyMsg);
          friendlyErr.isBackendWaking = !isLocal && !isTimeout;
          friendlyErr.status = 503;
          throw friendlyErr;
        }

        throw err;
      }
    }

    throw lastError || new Error('Yêu cầu không thành công');
  }


  get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' });
  }

  post(endpoint, body = null, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'POST',
      body: body ? (typeof body === 'string' ? body : JSON.stringify(body)) : undefined,
    });
  }

  put(endpoint, body = null, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PUT',
      body: body ? (typeof body === 'string' ? body : JSON.stringify(body)) : undefined,
    });
  }

  patch(endpoint, body = null, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PATCH',
      body: body ? (typeof body === 'string' ? body : JSON.stringify(body)) : undefined,
    });
  }

  delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  }
}

export const client = new ApiClient();
