/**
 * Job Hunter Platform — Environment & API URL Resolution
 */

declare global {
  interface Window {
    ENV?: {
      API_URL?: string;
      ENVIRONMENT?: string;
    };
    __RUNTIME_CONFIG__?: {
      API_URL?: string;
    };
    API_URL?: string;
  }
}

export function isLocalDevEnvironment(): boolean {
  if (typeof window === 'undefined' || !window.location) return false;
  const { hostname, protocol } = window.location;
  if (protocol === 'file:') return true;
  if (
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    hostname === '0.0.0.0' ||
    hostname.endsWith('.local') ||
    hostname.startsWith('192.168.') ||
    hostname.startsWith('10.') ||
    /^172\.(1[6-9]|2[0-9]|3[0-1])\./.test(hostname)
  ) {
    return true;
  }
  if (window.ENV && window.ENV.ENVIRONMENT === 'development') return true;
  return false;
}

export function normalizeBaseUrl(url: string): string {
  if (!url || typeof url !== 'string') return '';
  let cleaned = url.trim().replace(/\/+$/, '');
  if (!cleaned.endsWith('/api/v1') && !cleaned.includes('/api/')) {
    cleaned += '/api/v1';
  }
  return cleaned;
}

export function resolveApiBaseUrl(): string {
  // 1. localStorage override
  try {
    const saved = localStorage.getItem('jh_api_base');
    if (saved && saved.trim()) {
      return normalizeBaseUrl(saved);
    }
  } catch (_) {}

  // 2. Local dev auto-detection
  if (typeof window !== 'undefined' && window.location) {
    const { protocol, hostname, port } = window.location;
    const isLocal =
      protocol === 'file:' ||
      hostname === 'localhost' ||
      hostname === '127.0.0.1' ||
      hostname === '0.0.0.0' ||
      hostname.endsWith('.local') ||
      hostname.startsWith('192.168.') ||
      hostname.startsWith('10.') ||
      /^172\.(1[6-9]|2[0-9]|3[0-1])\./.test(hostname);

    if (isLocal) {
      if (port === '8000') {
        return '/api/v1';
      }
      const host = (hostname && hostname !== '0.0.0.0') ? hostname : 'localhost';
      return `http://${host}:8000/api/v1`;
    }
  }

  // 3. Window Runtime Config
  const envUrl = window.ENV?.API_URL || window.__RUNTIME_CONFIG__?.API_URL || window.API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim()) {
    return normalizeBaseUrl(envUrl);
  }

  // 4. Meta tag
  if (typeof document !== 'undefined') {
    const metaTag = document.querySelector<HTMLMetaElement>('meta[name="api-base"]');
    if (metaTag && metaTag.content && metaTag.content.trim()) {
      return normalizeBaseUrl(metaTag.content);
    }
  }

  // 5. Default relative path
  return '/api/v1';
}

export function getApiResolutionSource(): string {
  try {
    const saved = localStorage.getItem('jh_api_base');
    if (saved && saved.trim()) return 'localStorage (Tùy biến người dùng)';
  } catch (_) {}

  if (typeof window !== 'undefined' && window.location) {
    const { protocol, hostname, port } = window.location;
    const isLocal =
      protocol === 'file:' ||
      hostname === 'localhost' ||
      hostname === '127.0.0.1' ||
      hostname === '0.0.0.0' ||
      hostname.endsWith('.local') ||
      hostname.startsWith('192.168.') ||
      hostname.startsWith('10.') ||
      /^172\.(1[6-9]|2[0-9]|3[0-1])\./.test(hostname);

    if (isLocal) {
      if (protocol === 'file:') return 'file:// protocol (Tự động nhận diện Localhost:8000)';
      if (port === '8000') return 'Localhost:8000 (Tự động nhận diện Same-Origin /api/v1)';
      return `Dev Port ${port || 'default'} (Tự động nhận diện Localhost:8000)`;
    }
  }

  const envUrl = window.ENV?.API_URL || window.__RUNTIME_CONFIG__?.API_URL || window.API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim()) return 'window.ENV (env.js / Runtime Config)';

  if (typeof document !== 'undefined') {
    const metaTag = document.querySelector<HTMLMetaElement>('meta[name="api-base"]');
    if (metaTag && metaTag.content && metaTag.content.trim()) return 'HTML <meta name="api-base">';
  }

  return 'Relative Path (/api/v1)';
}
