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
  return client.post(`/jobs/daily-batch?limit_per_source=${limitPerSource}`);
}

export function triggerCollection(source = 'mock', limit = 5) {
  return client.post(`/jobs/collect?source=${source}&limit=${limit}`);
}

export function ingestManualJob(payload) {
  return client.post('/jobs/ingest-manual', payload);
}
