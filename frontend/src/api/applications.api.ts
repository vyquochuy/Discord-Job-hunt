import { client } from './client';
import { Application, ApplicationStatus } from '../types/application';

export function getApplications(page = 1, pageSize = 50): Promise<Application[]> {
  return client.get(`/applications?page=${page}&page_size=${pageSize}`);
}

export function submitApplication(
  jobId: string,
  payload: Record<string, unknown> = {}
): Promise<Application> {
  return client.post(`/applications/apply/${jobId}`, payload);
}

export function createApplication(data: { job_id: string; [key: string]: unknown }): Promise<Application> {
  return submitApplication(data.job_id, data);
}

export function updateApplicationStatus(
  appId: string,
  status: ApplicationStatus,
  errorMessage: string | null = null
): Promise<Application> {
  return client.patch(`/applications/${appId}/status`, {
    status,
    error_message: errorMessage,
  });
}
