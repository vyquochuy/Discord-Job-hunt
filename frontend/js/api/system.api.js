/**
 * Job Hunter Platform — System Administration & Health API Endpoints
 */

import { client } from './client.js';

export async function checkHealth() {
  const startTime = performance.now();
  let healthUrl;
  const baseUrl = client.getBaseUrl();

  if (baseUrl.startsWith('http://') || baseUrl.startsWith('https://')) {
    const rootBase = baseUrl.replace(/\/api\/v1\/?$/, '');
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

export function purgeDatabase(scope = 'jobs_and_tailoring', cleanStorage = true) {
  return client.post('/system/purge-database', {
    scope,
    clean_storage: cleanStorage,
    confirm: true,
  });
}

export function resetDemo() {
  return client.post('/system/reset-demo');
}
