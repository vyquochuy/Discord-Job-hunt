/**
 * Job Hunter Platform — Candidate Profile API Endpoints
 */

import { client } from './client.js';

export function getProfile() {
  return client.get('/profile');
}

export function updateProfile(profileData) {
  return client.put('/profile', profileData);
}

export function syncProfileFromContext() {
  return client.post('/profile/sync');
}

export async function uploadResumeFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const url = `${client.getBaseUrl()}/profile/upload-resume`;
  const headers = {};
  if (client.hasToken()) {
    headers['Authorization'] = `Bearer ${client.token}`;
  }

  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    let errorMsg = `HTTP Error ${response.status}`;
    try {
      const errData = await response.json();
      errorMsg = errData.detail || errorMsg;
    } catch (_) {}
    throw new Error(errorMsg);
  }
  return await response.json();
}
