/**
 * Job Hunter Platform — HTTP Client Base
 */

import { resolveApiBaseUrl, getApiResolutionSource } from '../config/config.js';
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

  async request(endpoint, options = {}, isRetry = false) {
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

      // Tự động làm mới phiên với Refresh Token Mutex Queue khi gặp 401
      if (response.status === 401) {
        const isAuthEndpoint = endpoint.includes('/auth/login') ||
                               endpoint.includes('/auth/register') ||
                               endpoint.includes('/auth/refresh');

        if (!isRetry && !isAuthEndpoint && this.refreshToken) {
          try {
            console.info('Access token expired, triggering automatic refresh with mutex...');
            await this.refreshAuthToken();
            // Thử lại request gốc với access token vừa được làm mới
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
      if (!isRetry) {
        console.error(`API Error [${options.method || 'GET'} ${endpoint}] -> ${url}:`, err);
      }
      throw err;
    }
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
