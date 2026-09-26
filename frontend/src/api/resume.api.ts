import { client } from './client';
import { TailoredResume, TailoredResumeSummary } from '../types/resume';

export function getTailoredResumes(): Promise<TailoredResumeSummary[]> {
  return client.get('/resumes');
}

export function getTailoredResumeById(resumeId: string): Promise<TailoredResume> {
  return client.get(`/resumes/${resumeId}`);
}

export function getTailoredResume(jobId: string): Promise<TailoredResume> {
  return client.get(`/resumes/job/${jobId}`);
}

export function tailorResume(
  jobId: string,
  forceRegenerate = false,
  customTone = 'professional_and_humble'
): Promise<TailoredResume> {
  return client.post(`/resumes/tailor/${jobId}`, {
    force_regenerate: forceRegenerate,
    custom_tone: customTone,
  });
}

export const createTailoredResume = tailorResume;

export function deleteTailoredResume(jobId: string): Promise<{ message: string }> {
  return client.delete(`/resumes/job/${jobId}`);
}

export function deleteTailoredResumeById(resumeId: string): Promise<{ message: string }> {
  return client.delete(`/resumes/${resumeId}`);
}

export function updateResumeLatex(resumeId: string, latexSource: string): Promise<TailoredResume> {
  return client.put(`/resumes/${resumeId}/tex`, {
    latex_source: latexSource,
  });
}

export function getResumePdfUrl(resumeId: string, download = false): string {
  let url = `${client.getBaseUrl()}/resumes/${resumeId}/pdf?download=${download ? 'true' : 'false'}`;
  const token = client.getToken();
  if (token) {
    url += `&token=${encodeURIComponent(token)}`;
  }
  return url;
}
