import { client } from './client';
import { CandidateProfile, SyncProfileResponse } from '../types/candidate';

export function getProfile(): Promise<CandidateProfile> {
  return client.get('/profile');
}

export function updateProfile(profileData: Partial<CandidateProfile>): Promise<CandidateProfile> {
  return client.put('/profile', profileData);
}

export function syncProfileFromContext(): Promise<SyncProfileResponse> {
  return client.post('/profile/sync');
}

export async function uploadResumeFile(file: File): Promise<CandidateProfile & { message?: string }> {
  const formData = new FormData();
  formData.append('file', file);

  const url = `${client.getBaseUrl()}/profile/upload-resume`;
  const headers: Record<string, string> = {};
  const token = client.getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
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
