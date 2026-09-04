/**
 * Job Hunter Platform — Global Configuration & Environment Resolver
 */

export const VALID_VIEWS = [
  'dashboard',
  'jobs',
  'recommendations',
  'resume',
  'applications',
  'profile',
  'system',
];

export const VIEW_TITLES = {
  dashboard: 'Tổng quan Dashboard',
  jobs: 'Khám phá & Tìm kiếm việc làm',
  recommendations: 'Đề xuất việc làm phù hợp',
  profile: 'Hồ sơ Ứng viên & Nguồn tham chiếu gốc',
  resume: 'Không gian Hồ sơ tạo thiết kế & Xác thực',
  applications: 'Quản lý & Theo dõi đơn nộp',
  system: 'Hệ thống & Cơ sở dữ liệu',
};

/**
 * Checks if running in a local development environment.
 * Used to conditionally enable local-only features like Quick Admin Login.
 */
export function isLocalDevEnvironment() {
  if (typeof window === 'undefined' || !window.location) return false;
  const { hostname, protocol } = window.location;
  if (protocol === 'file:') return true;
  if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '0.0.0.0') return true;
  if (window.ENV && window.ENV.ENVIRONMENT === 'development') return true;
  return false;
}

/**
 * Resolves the active Backend API base URL using a multi-tiered hierarchy:
 * 1. User manual override stored in localStorage (`jh_api_base`)
 * 2. Window Runtime Config (`window.ENV?.API_URL` or `window.__RUNTIME_CONFIG__?.API_URL` or `window.API_URL`)
 * 3. HTML Meta Tag (`<meta name="api-base" content="...">`)
 * 4. Local dev auto-detection (if on localhost / 127.0.0.1 on a non-8000 port -> http://localhost:8000/api/v1)
 * 5. File protocol auto-detection (if on file:// -> http://localhost:8000/api/v1)
 * 6. Default relative path (`/api/v1`)
 */
export function resolveApiBaseUrl() {
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

export function getApiResolutionSource() {
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
