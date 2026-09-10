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

/**
 * Resolves the active Backend API base URL using a multi-tiered hierarchy:
 * 1. User manual override stored in localStorage (`jh_api_base`)
 * 2. Local dev auto-detection (Localhost / 127.0.0.1 -> local FastAPI at http://localhost:8000/api/v1)
 * 3. Window Runtime Config (`window.ENV?.API_URL` or `window.__RUNTIME_CONFIG__?.API_URL` or `window.API_URL`)
 * 4. HTML Meta Tag (`<meta name="api-base" content="...">`)
 * 5. Default relative path (`/api/v1`)
 */
function normalizeBaseUrl(url) {
  if (!url || typeof url !== 'string') return '';
  let cleaned = url.trim().replace(/\/+$/, '');
  if (!cleaned.endsWith('/api/v1') && !cleaned.includes('/api/')) {
    cleaned += '/api/v1';
  }
  return cleaned;
}

export function resolveApiBaseUrl() {
  // 1. localStorage override (cho phép người dùng ghi đè thủ công trong phần cài đặt)
  try {
    const saved = localStorage.getItem('jh_api_base');
    if (saved && saved.trim()) {
      return normalizeBaseUrl(saved);
    }
  } catch (_) {}

  // 2. Local dev auto-detection: Khi chạy local (localhost, 127.0.0.1, file://, hoặc LAN IP),
  // luôn ưu tiên tự động kết nối tới Backend FastAPI & Database PostgreSQL local.
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
      // Nếu cùng port 8000 (FastAPI đang phục vụ frontend tĩnh)
      if (port === '8000') {
        return '/api/v1';
      }
      // Nếu chạy qua Live Server, file://, hoặc port khác
      const host = (hostname && hostname !== '0.0.0.0') ? hostname : 'localhost';
      return `http://${host}:8000/api/v1`;
    }
  }

  // 3. Window Runtime Config (Dành cho môi trường Cloud / Production như Cloudflare Pages, Render)
  const envUrl = window.ENV?.API_URL || window.__RUNTIME_CONFIG__?.API_URL || window.API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim()) {
    return normalizeBaseUrl(envUrl);
  }

  // 4. Meta tag
  if (typeof document !== 'undefined') {
    const metaTag = document.querySelector('meta[name="api-base"]');
    if (metaTag && metaTag.content && metaTag.content.trim()) {
      return normalizeBaseUrl(metaTag.content);
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
    const metaTag = document.querySelector('meta[name="api-base"]');
    if (metaTag && metaTag.content && metaTag.content.trim()) return 'HTML <meta name="api-base">';
  }

  return 'Relative Path (/api/v1)';
}
