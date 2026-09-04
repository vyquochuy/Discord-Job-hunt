/**
 * Job Hunter Platform — Unified API Export
 * Maintains full backward compatibility with legacy `api` methods while providing modular imports.
 */

import { client } from './client.js';
import * as authApi from './auth.api.js';
import * as jobsApi from './jobs.api.js';
import * as matchesApi from './matches.api.js';
import * as profileApi from './profile.api.js';
import * as resumeApi from './resume.api.js';
import * as applicationsApi from './applications.api.js';
import * as systemApi from './system.api.js';

export const api = {
  // Client base & Token management
  getBaseUrl: () => client.getBaseUrl(),
  setBaseUrl: (url) => client.setBaseUrl(url),
  resetBaseUrl: () => client.resetBaseUrl(),
  getResolutionSource: () => client.getResolutionSource(),
  setToken: (token) => client.setToken(token),
  hasToken: () => client.hasToken(),
  logout: () => client.logout(),
  request: (endpoint, options) => client.request(endpoint, options),

  // Auth
  register: authApi.register,
  login: authApi.login,
  getMe: authApi.getMe,

  // Jobs
  getJobs: jobsApi.getJobs,
  getJobDetail: jobsApi.getJobDetail,
  getSavedJobs: jobsApi.getSavedJobs,
  saveJob: jobsApi.saveJob,
  unsaveJob: jobsApi.unsaveJob,
  triggerDailyBatch: jobsApi.triggerDailyBatch,
  triggerCollection: jobsApi.triggerCollection,
  ingestManualJob: jobsApi.ingestManualJob,

  // Matches
  getTopRecommendations: matchesApi.getTopRecommendations,
  getMatchDetail: matchesApi.getMatchDetail,
  calculateMatch: matchesApi.calculateMatch,

  // Profile
  getProfile: profileApi.getProfile,
  updateProfile: profileApi.updateProfile,
  syncProfileFromContext: profileApi.syncProfileFromContext,
  uploadResumeFile: profileApi.uploadResumeFile,

  // Tailored Resumes
  getTailoredResume: resumeApi.getTailoredResume,
  tailorResume: resumeApi.tailorResume,
  deleteTailoredResume: resumeApi.deleteTailoredResume,
  deleteTailoredResumeById: resumeApi.deleteTailoredResumeById,
  updateResumeLatex: resumeApi.updateResumeLatex,
  getResumePdfUrl: resumeApi.getResumePdfUrl,

  // Applications
  getApplications: applicationsApi.getApplications,
  submitApplication: applicationsApi.submitApplication,
  updateApplicationStatus: applicationsApi.updateApplicationStatus,

  // System
  checkHealth: systemApi.checkHealth,
  purgeDatabase: systemApi.purgeDatabase,
  resetDemo: systemApi.resetDemo,
};

// Global backward compatibility bridge
if (typeof window !== 'undefined') {
  window.api = api;
}

export {
  client,
  authApi,
  jobsApi,
  matchesApi,
  profileApi,
  resumeApi,
  applicationsApi,
  systemApi,
};
