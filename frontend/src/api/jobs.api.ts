import { client } from './client';
import { Job, JobDetail, JobListResponse, JobFilterParams } from '../types/job';

export function getJobs(params: JobFilterParams = {}): Promise<JobListResponse> {
  const query = new URLSearchParams();
  if (params.keyword) query.append('keyword', params.keyword);
  if (params.work_mode) query.append('work_mode', params.work_mode);
  if (params.level) query.append('level', params.level);
  if (params.location) query.append('location', params.location);
  if (params.source) query.append('source', params.source);
  if (params.page) query.append('page', String(params.page));
  if (params.page_size) query.append('page_size', String(params.page_size));

  const qs = query.toString();
  return client.get(`/jobs${qs ? `?${qs}` : ''}`);
}

export function getJobDetail(jobId: string): Promise<JobDetail> {
  return client.get(`/jobs/${jobId}`);
}

export function getSavedJobs(): Promise<Array<{ id: string; job_id: string; job: Job; notes?: string }>> {
  return client.get('/jobs/saved');
}

export function saveJob(jobId: string, notes = ''): Promise<{ message: string; saved: boolean }> {
  return client.post(`/jobs/${jobId}/save`, { notes });
}

export function unsaveJob(jobId: string): Promise<{ message: string }> {
  return client.delete(`/jobs/${jobId}/save`);
}

export function triggerDailyBatch(limitPerSource = 50): Promise<{
  total_sources: number;
  total_collected: number;
  total_standardized: number;
  total_matches_created: number;
  sources_summary?: Record<string, number>;
}> {
  return client.post(`/jobs/daily-batch?limit_per_source=${limitPerSource}`, null, { timeout: 300000 });
}

export function triggerCollection(source = 'mock', limit = 5): Promise<unknown> {
  return client.post(`/jobs/collect?source=${source}&limit=${limit}`, null, { timeout: 120000 });
}

export interface ManualIngestPayload {
  raw_text?: string;
  source_url?: string;
  auto_match?: boolean;
}

export function ingestManualJob(payload: ManualIngestPayload): Promise<{
  job: Job;
  match?: unknown;
  message?: string;
}> {
  return client.post('/jobs/ingest-manual', payload);
}
