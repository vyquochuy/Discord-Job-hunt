/**
 * Job Hunter Platform — HTTP Client Base
 */

import { resolveApiBaseUrl, getApiResolutionSource } from '../config/config.js';
import { events, APP_EVENTS } from '../core/events.js';

export class ApiClient {
  constructor() {
    this.baseUrl = resolveApiBaseUrl();
    this.token = (typeof localStorage !== 'undefined') ? localStorage.getItem('jh_access_token') : null;
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

  hasToken() {
    return !!this.token;
  }

  logout() {
    this.setToken(null);
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
        if (this.token) {
          this.setToken(null);
          events.emit(APP_EVENTS.AUTH_EXPIRED);
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
