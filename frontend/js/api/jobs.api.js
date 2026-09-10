/**
 * Job Hunter Platform — Jobs API Endpoints
 */

import { client } from './client.js';

export function getJobs(params = {}) {
  const query = new URLSearchParams();
  if (params.keyword) query.append('keyword', params.keyword);
  if (params.work_mode) query.append('work_mode', params.work_mode);
  if (params.level) query.append('level', params.level);
  if (params.location) query.append('location', params.location);
  if (params.source) query.append('source', params.source);
  if (params.page) query.append('page', params.page);
  if (params.page_size) query.append('page_size', params.page_size);

  return client.get(`/jobs?${query.toString()}`);
}

export function getJobDetail(jobId) {
  return client.get(`/jobs/${jobId}`);
}

export function getSavedJobs() {
  return client.get('/jobs/saved');
}

export function saveJob(jobId, notes = '') {
  return client.post(`/jobs/${jobId}/save`, { notes });
}

export function unsaveJob(jobId) {
  return client.delete(`/jobs/${jobId}/save`);
}

export function triggerDailyBatch(limitPerSource = 50) {
  // Quét đa nguồn cào 10 website có thể mất từ 1-3 phút.
  // Đặt timeout 5 phút (300,000ms) để không bị trình duyệt tự ngắt abort sau 25s
  return client.post(`/jobs/daily-batch?limit_per_source=${limitPerSource}`, null, { timeout: 300000 });
}

export function triggerCollection(source = 'mock', limit = 5) {
  return client.post(`/jobs/collect?source=${source}&limit=${limit}`, null, { timeout: 120000 });
}

export function ingestManualJob(payload) {
  return client.post('/jobs/ingest-manual', payload);
}
