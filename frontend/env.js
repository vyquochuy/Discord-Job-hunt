/**
 * Job Hunter Platform — Runtime Environment Configuration
 * 
 * Default configuration: empty API_URL enables automatic resolution
 * (uses localStorage override, meta tag, dev port fallback, or relative /api/v1).
 */

window.ENV = window.ENV || {
  API_URL: '',
  ENVIRONMENT: 'production',
};
