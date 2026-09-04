/**
 * Job Hunter Platform — Application Tracker API Endpoints
 */

import { client } from './client.js';

export function getApplications(page = 1, pageSize = 20) {
  return client.get(`/applications?page=${page}&page_size=${pageSize}`);
}

export function submitApplication(jobId, payload = {}) {
  return client.post(`/applications/apply/${jobId}`, payload);
}

export function updateApplicationStatus(appId, status, errorMessage = null) {
  return client.patch(`/applications/${appId}/status`, {
    status,
    error_message: errorMessage,
  });
}
