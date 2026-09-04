/**
 * Job Hunter Platform — Tailored Resume & LaTeX API Endpoints
 */

import { client } from './client.js';

export function getTailoredResume(jobId) {
  return client.get(`/resumes/job/${jobId}`);
}

export function tailorResume(jobId, forceRegenerate = false, customTone = 'professional_and_humble') {
  return client.post(`/resumes/tailor/${jobId}`, {
    force_regenerate: forceRegenerate,
    custom_tone: customTone,
  });
}

export function deleteTailoredResume(jobId) {
  return client.delete(`/resumes/job/${jobId}`);
}

export function deleteTailoredResumeById(resumeId) {
  return client.delete(`/resumes/${resumeId}`);
}

export function updateResumeLatex(resumeId, latexSource) {
  return client.put(`/resumes/${resumeId}/tex`, {
    latex_source: latexSource,
  });
}

export function getResumePdfUrl(resumeId, download = false) {
  return `${client.getBaseUrl()}/resumes/${resumeId}/pdf?download=${download ? 'true' : 'false'}`;
}
