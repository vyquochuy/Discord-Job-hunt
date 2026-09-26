/**
 * Job Hunter Platform — Typed HTTP Client with Concurrency Mutex & Token Refresh
 */

import { resolveApiBaseUrl, getApiResolutionSource, isLocalDevEnvironment } from '../config/env';

export interface RequestOptions extends RequestInit {
  timeout?: number;
  maxRetries?: number;
  safeRetry?: boolean;
}

export type AuthExpiredListener = () => void;
export type BackendWakingListener = (detail: { attempt: number; maxAttempts: number; status?: number }) => void;
export type BackendReadyListener = () => void;

export class ApiClient {
  private baseUrl: string;
  private token: string | null = null;
  private refreshToken: string | null = null;
  private refreshPromise: Promise<string> | null = null; // Invariant 1: Frontend Mutex Promise Queue

  private authExpiredListeners: Set<AuthExpiredListener> = new Set();
  private backendWakingListeners: Set<BackendWakingListener> = new Set();
  private backendReadyListeners: Set<BackendReadyListener> = new Set();

  constructor() {
    this.baseUrl = resolveApiBaseUrl();
    if (typeof localStorage !== 'undefined') {
      this.token = localStorage.getItem('jh_access_token');
      this.refreshToken = localStorage.getItem('jh_refresh_token');
    }
  }

  // --- Listener Management ---
  onAuthExpired(fn: AuthExpiredListener) {
    this.authExpiredListeners.add(fn);
    return () => this.authExpiredListeners.delete(fn);
  }

  onBackendWaking(fn: BackendWakingListener) {
    this.backendWakingListeners.add(fn);
    return () => this.backendWakingListeners.delete(fn);
  }

  onBackendReady(fn: BackendReadyListener) {
    this.backendReadyListeners.add(fn);
    return () => this.backendReadyListeners.delete(fn);
  }

  private notifyAuthExpired() {
    this.authExpiredListeners.forEach(fn => fn());
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('jh:auth_expired'));
    }
  }

  private notifyBackendWaking(detail: { attempt: number; maxAttempts: number; status?: number }) {
    this.backendWakingListeners.forEach(fn => fn(detail));
  }

  private notifyBackendReady() {
    this.backendReadyListeners.forEach(fn => fn());
  }

  // --- Base URL & Config ---
  getBaseUrl(): string {
    return this.baseUrl;
  }

  setBaseUrl(url?: string): string {
    if (url && typeof url === 'string' && url.trim()) {
      const cleaned = url.trim().replace(/\/+$/, '');
      this.baseUrl = cleaned;
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('jh_api_base', cleaned);
      }
    } else {
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem('jh_api_base');
      }
      this.baseUrl = resolveApiBaseUrl();
    }
    return this.baseUrl;
  }

  resetBaseUrl(): string {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('jh_api_base');
    }
    this.baseUrl = resolveApiBaseUrl();
    return this.baseUrl;
  }

  getResolutionSource(): string {
    return getApiResolutionSource();
  }

  // --- Token Management ---
  setTokens(accessToken: string | null, refreshToken: string | null = null) {
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

  hasToken(): boolean {
    return !!this.token;
  }

  getToken(): string | null {
    return this.token;
  }

  getRefreshToken(): string | null {
    return this.refreshToken;
  }

  async logout(): Promise<void> {
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
    this.notifyAuthExpired();
  }

  async refreshAuthToken(): Promise<string> {
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
        return data.access_token as string;
      } catch (err) {
        this.token = null;
        this.refreshToken = null;
        if (typeof localStorage !== 'undefined') {
          localStorage.removeItem('jh_access_token');
          localStorage.removeItem('jh_refresh_token');
        }
        this.notifyAuthExpired();
        throw err;
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  private getHeaders(customHeaders: HeadersInit = {}): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((customHeaders as Record<string, string>) || {}),
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  private async executeFetch(
    url: string,
    options: RequestOptions,
    headers: Record<string, string>,
    timeoutMs: number
  ): Promise<Response> {
    const controller = new AbortController();
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
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
    } catch (err: unknown) {
      const error = err as Error;
      if (didTimeout || error.name === 'AbortError') {
        const timeoutErr = new Error('Yêu cầu hết thời gian chờ (Backend cold start / Network timeout).');
        timeoutErr.name = 'TimeoutError';
        throw timeoutErr;
      }
      throw err;
    } finally {
      if (timeoutId) clearTimeout(timeoutId);
    }
  }

  async request<T = unknown>(endpoint: string, options: RequestOptions = {}, isAuthRetry = false): Promise<T> {
    let url: string;
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

    let lastError: unknown = null;
    let hadTransientFailure = false;

    for (let attempt = 1; attempt <= 1 + maxRetries; attempt++) {
      const headers = this.getHeaders(options.headers);

      try {
        const response = await this.executeFetch(url, options, headers, timeoutMs);

        // 401 Unauthorized: Refresh Token Mutex Queue
        if (response.status === 401) {
          const isAuthEndpoint =
            endpoint.includes('/auth/login') ||
            endpoint.includes('/auth/register') ||
            endpoint.includes('/auth/refresh');

          if (!isAuthRetry && !isAuthEndpoint && this.refreshToken) {
            try {
              await this.refreshAuthToken();
              return await this.request<T>(endpoint, options, true);
            } catch (_) {
              // Refresh failed
            }
          } else {
            if (this.token || this.refreshToken) {
              this.token = null;
              this.refreshToken = null;
              if (typeof localStorage !== 'undefined') {
                localStorage.removeItem('jh_access_token');
                localStorage.removeItem('jh_refresh_token');
              }
              this.notifyAuthExpired();
            }
          }
        }

        // 502/503/504 Render / Cold start
        if ([502, 503, 504].includes(response.status)) {
          hadTransientFailure = true;
          if (attempt <= maxRetries) {
            this.notifyBackendWaking({
              attempt,
              maxAttempts: 1 + maxRetries,
              status: response.status,
            });
            const backoffMs = Math.min(1500 * Math.pow(2, attempt - 1), 5000);
            await new Promise(r => setTimeout(r, backoffMs));
            continue;
          }

          const isLocal = isLocalDevEnvironment();
          const msg = isLocal
            ? `Máy chủ Backend phản hồi lỗi ${response.status}. Vui lòng kiểm tra lại dịch vụ Backend local.`
            : 'Máy chủ Backend đang khởi động lại (Render cold start). Vui lòng đợi trong giây lát và thử lại.';
          const err = new Error(msg);
          throw err;
        }

        if (!response.ok) {
          let errorMsg = `HTTP Error ${response.status}`;
          try {
            const errData = await response.json();
            errorMsg = errData.detail || errData.message || errorMsg;
          } catch (_) {}
          const appErr = new Error(errorMsg) as Error & { status: number };
          appErr.status = response.status;
          throw appErr;
        }

        if (hadTransientFailure) {
          this.notifyBackendReady();
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          return (await response.json()) as T;
        }
        return (await response.text()) as unknown as T;
      } catch (err: unknown) {
        lastError = err;
        const error = err as Error & { status?: number };

        // 4xx app errors should not be retried
        if (error.status && error.status < 500) {
          throw error;
        }

        const isTimeout = error.name === 'TimeoutError' || error.name === 'AbortError';
        const isTransientNetwork =
          isTimeout ||
          error.name === 'TypeError' ||
          (error.message &&
            (error.message.includes('fetch') ||
              error.message.includes('network') ||
              error.message.includes('NetworkError') ||
              error.message.includes('Failed to fetch')));

        if (isTransientNetwork && canRetry && attempt <= maxRetries) {
          hadTransientFailure = true;
          this.notifyBackendWaking({ attempt, maxAttempts: 1 + maxRetries });
          const backoffMs = Math.min(1500 * Math.pow(2, attempt - 1), 5000);
          await new Promise(r => setTimeout(r, backoffMs));
          continue;
        }

        if (isTransientNetwork) {
          const isLocal = isLocalDevEnvironment();
          let friendlyMsg: string;
          if (isTimeout) {
            friendlyMsg = isLocal
              ? 'Tác vụ xử lý quá thời gian chờ (Timeout). Backend local vẫn đang chạy ngầm trong nền, vui lòng đợi ít phút rồi làm mới danh sách.'
              : 'Tác vụ mất nhiều thời gian hơn dự kiến (Timeout). Quá trình quét vẫn đang chạy ngầm trên máy chủ, vui lòng đợi ít phút rồi làm mới danh sách.';
          } else {
            friendlyMsg = isLocal
              ? 'Không thể kết nối đến máy chủ Backend local (http://localhost:8000). Vui lòng kiểm tra xem Backend FastAPI / Docker đã chạy chưa.'
              : 'Máy chủ Backend đang khởi động lại (Render cold start). Vui lòng đợi trong giây lát và thử lại.';
          }
          throw new Error(friendlyMsg);
        }

        throw err;
      }
    }

    throw lastError || new Error('Yêu cầu không thành công');
  }

  get<T = unknown>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  post<T = unknown>(endpoint: string, body?: unknown, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body ? (typeof body === 'string' ? body : JSON.stringify(body)) : undefined,
    });
  }

  put<T = unknown>(endpoint: string, body?: unknown, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: body ? (typeof body === 'string' ? body : JSON.stringify(body)) : undefined,
    });
  }

  patch<T = unknown>(endpoint: string, body?: unknown, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: body ? (typeof body === 'string' ? body : JSON.stringify(body)) : undefined,
    });
  }

  delete<T = unknown>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }
}

export const client = new ApiClient();
